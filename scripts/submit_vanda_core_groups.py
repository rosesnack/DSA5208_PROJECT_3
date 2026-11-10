"""Submit missing full-core groups within project credits; default is a dry run."""
import argparse
import csv
from datetime import datetime
from zoneinfo import ZoneInfo
import fcntl
import json
import os
from pathlib import Path
import subprocess


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()


def cpu_hours(job):
    h, m, s = map(int, job["Resource_List"]["walltime"].split(":"))
    return int(job["Resource_List"]["ncpus"]) * (h + m / 60 + s / 3600)


def allocation_request(group):
    per_node = group['cores_per_node']
    memory = max(per_node, 64) if group['graph'].startswith('strong_') else max(per_node, 4)
    chunk = f'ncpus={per_node}:mpiprocs={per_node}:ompthreads=1:mem={memory}gb'
    hosts = group.get('requested_hosts')
    if hosts:
        assert len(hosts) == len(set(hosts)) == group['nodes']
        return '+'.join(f'1:{chunk}:host={host}' for host in hosts)
    return f'{group["nodes"]}:{chunk}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("project")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--max-new", type=int, default=24)
    parser.add_argument("--margin", type=float, default=128)
    parser.add_argument("--cores-per-node", nargs="+", type=int, choices=(1, 2, 4, 8, 16, 32, 64), default=[32],
                        help="Only submit the explicitly enabled and validated allocation sizes")
    parser.add_argument("--confirmed-balance", type=float,
                        help="Balance just supplied by the user; conservatively reserve running jobs too")
    parser.add_argument("--dependency", required=True, help="Free smoke-test job which must pass")
    parser.add_argument("--defer-held-job", action="append", default=[],
                        help="Do not reserve a named postponed job only while PBS confirms its user hold")
    args = parser.parse_args()
    root = Path("results/updated_vanda_scaling") / args.run_id
    with (root / "core_group_submit.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        groups = json.loads(args.plan.read_text())
        ids = subprocess.run(["qselect", "-u", os.environ["USER"]], text=True,
                             capture_output=True, check=True).stdout.split()
        jobs = json.loads(run("qstat", "-f", "-F", "json", *ids))["Jobs"] if ids else {}
        if args.confirmed_balance is None:
            balance_text = run("hpc", "project")
            balance = float(next(line for line in balance_text.splitlines()
                                 if line.strip().startswith(args.project + " ")).split("|")[2])
        else:
            balance = args.confirmed_balance
        reserved_states = ("Q", "H", "R", "E") if args.confirmed_balance is not None else ("Q", "H")
        deferred = {i for i in args.defer_held_job if i in jobs and jobs[i]['job_state'] == 'H'
                    and 'u' in jobs[i].get('Hold_Types', '')}
        pending = sum(cpu_hours(j) for i, j in jobs.items() if j.get("project") == args.project
                      and j["queue"] in ("auto", "batch_cpu") and j["job_state"] in reserved_states
                      and i not in deferred)
        available = balance - pending - args.margin
        registry = root / "core_group_jobs.tsv"
        fields = ["graph", "nodes", "cores_per_node", "cores", "performance_job", "validation_job", "walltime", "cells", "plan", "dependency"]
        existing = list(csv.DictReader(registry.open(), delimiter="\t")) if registry.exists() else []
        known = {(r["graph"], int(r["nodes"]), int(r["cores_per_node"]),
                  json.loads(Path(r["plan"]).read_text()).get("extension", "")) for r in existing}
        accepted = []
        env = os.environ.copy()
        env.update(RUN_ID=args.run_id, DATA_ROOT=f'/scratch/{os.environ["USER"]}/dsa5208_scaling/{args.run_id}',
                   OMPI_MCA_btl="self,vader,tcp", OMPI_MCA_pml="ob1", UCX_NET_DEVICES="",
                   PAGERANK_HYBRID_MAX_TOTAL_THREADS="512")
        for group in groups:
            key = (group["graph"], group["nodes"], group["cores_per_node"], group.get("extension", ""))
            if key in known or group["cores_per_node"] not in args.cores_per_node or len(accepted) >= args.max_new:
                continue
            if group["prerequisite"] and not (root / group["prerequisite"]).is_file():
                continue
            cells = [c for c in group["cells"]
                     if not (root / Path(c["canonical_summary"]).parent / "complete.txt").is_file()]
            if not cells:
                continue
            group = {**group, "cells": cells}
            hours, minutes, seconds = map(int, group["walltime"].split(":"))
            reservation = group["cores"] * (hours + minutes / 60 + seconds / 3600)
            if reservation > available:
                continue
            suffix = "_" + group["extension"] if group.get("extension") else ""
            plan = root / "core_group_plans" / f'{group["graph"]}_n{group["nodes"]}_c{group["cores_per_node"]}{suffix}.json'
            if args.submit:
                plan.parent.mkdir(exist_ok=True)
                plan.write_text(json.dumps(group, indent=2) + "\n")
                env["CORE_GROUP_PLAN"] = str(plan.resolve())
                dependency = group.get("dependency", args.dependency)
                resources = 'select=' + allocation_request(group)
                perf = subprocess.check_output(["qsub", "-h", "-P", args.project, "-q", "auto", "-l", resources,
                    "-l", "walltime=" + group["walltime"], "-W", "depend=afterok:" + dependency,
                    "scripts/vanda_core_group_job.pbs"], env=env, text=True).strip()
                row = dict(zip(fields, (group["graph"], group["nodes"], group["cores_per_node"], group["cores"],
                           perf, "", group["walltime"], len(group["cells"]), str(plan), dependency)))
                existing.append(row)
                # Persist the held performance request before creating its free dependent job.
                with registry.open("w", newline="") as output:
                    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t")
                    writer.writeheader(); writer.writerows(existing)
                val = subprocess.check_output(["qsub", "-q", "auto_free", "-W", "depend=afterok:" + perf,
                    "scripts/vanda_finalize_core_group_job.pbs"], env=env, text=True).strip()
                row["validation_job"] = val
                with registry.open("w", newline="") as output:
                    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t")
                    writer.writeheader(); writer.writerows(existing)
                allocated = json.loads(run("qstat", "-f", "-F", "json", perf))["Jobs"][perf]["Resource_List"]
                hosts_match = all(h.lower() in allocated['select'].lower() for h in group.get('requested_hosts', []))
                if int(allocated["ncpus"]) != group["cores"] or int(allocated["nodect"]) != group["nodes"] or not hosts_match:
                    run("qdel", val)
                    run("qdel", perf)
                    raise RuntimeError(f"Cancelled held allocation {perf}: PBS resources differ from the full-core plan")
                run("qrls", "-h", "u", perf)
            else:
                perf = val = "dry-run"
            available -= reservation
            known.add(key)
            accepted.append({"graph": group["graph"], "nodes": group["nodes"], "cores": group["cores"],
                             "cells": len(group["cells"]), "walltime": group["walltime"],
                             "reservation": reservation, "performance_job": perf, "validation_job": val,
                             "dependency": group.get("dependency", args.dependency)})
            print(json.dumps(accepted[-1]), flush=True)
        now = datetime.now(ZoneInfo("Asia/Singapore"))
        date_tag = now.strftime("%Y%m%d")
        summary = {"observed_at": now.isoformat(), "submitted": args.submit,
                   "balance": balance, "balance_source": "user_confirmed" if args.confirmed_balance is not None else "hpc_project",
                   "prior_pending_reservations": pending, "margin": args.margin,
                   "deferred_user_held_jobs": sorted(deferred),
                   "new_reservations": sum(g["reservation"] for g in accepted),
                   "uncommitted_after_margin": available, "groups": accepted}
        record = json.dumps(summary, indent=2) + "\n"
        (root / f"core_group_last_check_{date_tag}.json").write_text(record)
        with (root / f"core_group_submission_events_{date_tag}.jsonl").open("a") as log:
            log.write(json.dumps(summary) + "\n")
        if not args.submit or accepted:
            name = f"core_group_submission_{date_tag}.json" if args.submit else f"core_group_dry_run_{date_tag}.json"
            (root / name).write_text(record)
            if args.submit:
                (root / f'core_group_submission_{now.strftime("%Y%m%d_%H%M%S_%f")}.json').write_text(record)
        print(f'Groups: {len(accepted)}, cells: {sum(g["cells"] for g in accepted)}, uncommitted after margin: {available:.3f}')


if __name__ == "__main__":
    main()

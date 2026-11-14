"""Measure one core budget or validate/publish it using the original solvers and checks."""
import argparse
from collections import defaultdict
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def command(parts, env=None, log=None):
    print(" ".join(map(str, parts)), flush=True)
    if log:
        with log.open("w") as output:
            subprocess.run(parts, env=env, stdout=output, stderr=subprocess.STDOUT, check=True)
    else:
        subprocess.run(parts, env=env, check=True)


def folder_for(cell, graph):
    method = cell["implementation"] + ("_halo" if cell["communication"] == "halo" else "")
    path = Path(method)
    if cell["implementation"] == "mpi_kokkos":
        path /= "OpenMP"
    config = f'p{cell["processes"]}'
    if cell["implementation"] == "hybrid" or cell["threads"] > 1:
        config += f'_t{cell["threads"]}'
    return path / graph / config


def layout_command(group, processes, threads, executable):
    parts = ["mpiexec", "-x", "LD_LIBRARY_PATH", "-x", "OMP_NUM_THREADS",
             "-x", "PAGERANK_KOKKOS_THREADS", "-x", "PAGERANK_HYBRID_THREADS",
             "--map-by", f'ppr:{processes // group["nodes"]}:node',
             "--bind-to", "none", "-n", str(processes),
             "python3", "scripts/mpi_affinity_exec.py", str(threads)]
    return parts + executable


def check_affinity(records, group, processes, threads):
    assert sorted(r["rank"] for r in records) == list(range(processes))
    hosts = defaultdict(list)
    for record in records:
        assert len(record["cpus"]) == threads, record
        hosts[record["host"]].extend(record["cpus"])
    assert len(hosts) == group["nodes"], hosts.keys()
    for cpus in hosts.values():
        assert len(cpus) == len(set(cpus)) == group["cores_per_node"], cpus


def compute(group, raw, env):
    metadata = {"performance_job": env["PBS_JOBID"], "group": group,
                "executable_overrides": group.get("executables", {}),
                "mpi": subprocess.check_output(["mpicxx", "--showme:version"], text=True).strip(),
                "compiler": subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
                "cmake": [line for line in Path("build-vanda-matrix-cpu/CMakeCache.txt").read_text().splitlines()
                          if line.startswith(("CMAKE_BUILD_TYPE:", "CMAKE_CXX_COMPILER:"))]}
    (raw / "environment.json").write_text(json.dumps(metadata, indent=2) + "\n")
    reference = Path(env["DATA_ROOT"]) / "results/serial_grid" / group["graph"] / "serial" / group["graph"]
    destination = raw / "serial" / group["graph"]
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "history.csv", "timings.csv", "ranks.csv"):
        if not (destination / name).exists():
            os.link(reference / name, destination / name)
    command(["bash", "scripts/record_vanda_allocation.sh", str(raw / "cpu_hosts.jsonl")], env)
    if not group.get("validation_only"):
        hosts = [json.loads(line) for line in (raw / "cpu_hosts.jsonl").read_text().splitlines()]
        assert all("Platinum 8452Y" in host["cpu_model"] for host in hosts), hosts
    command(["python3", "scripts/select_graph_manifest.py",
             str(Path(env["DATA_ROOT"]) / "manifests/strong_scaling.tsv"), group["graph"],
             str(raw / "dataset.tsv")], env)
    env["PAGERANK_DATASET_MANIFEST"] = str(raw / "dataset.tsv")
    mapping = raw / "mapping"
    mapping.mkdir(exist_ok=True)
    measured_layouts = set()
    previous_dense_halo = False
    pauses = []
    for cell in group["cells"]:
        p, t = cell["processes"], cell["threads"]
        assert p * t == group["cores"] and p % group["nodes"] == 0
        env.update(OMP_NUM_THREADS=str(t), PAGERANK_KOKKOS_THREADS=str(t), PAGERANK_HYBRID_THREADS=str(t))
        if (p, t) not in measured_layouts:
            probe = layout_command(group, p, t, ["python3", "scripts/report_core_group_affinity.py"])
            output = subprocess.check_output(probe, env=env, text=True, timeout=120)
            records = [json.loads(line) for line in output.splitlines()]
            check_affinity(records, group, p, t)
            (mapping / f"p{p}_t{t}.jsonl").write_text(output)
            with (mapping / f"p{p}_t{t}.csv").open("w", newline="") as target:
                csv.writer(target).writerows((r["rank"], r["host"]) for r in sorted(records, key=lambda r: r["rank"]))
            measured_layouts.add((p, t))
        folder = raw / folder_for(cell, group["graph"])
        if (folder / "performance_job.txt").exists():
            saved = json.loads((folder / "summary.json").read_text())
            assert saved["repeat_runs"] == 5 and saved["warmup_runs"] == 1
            print(f"Reusing saved cell: {folder}", flush=True)
            continue
        program = group.get("executables", {}).get(
            cell["implementation"], "./build-vanda-matrix-cpu/pagerank_" + cell["implementation"])
        if previous_dense_halo and group.get("dense_launch_pause_s", 0):
            seconds = group["dense_launch_pause_s"]
            print(f"Outside solver timing: waiting {seconds}s after dense TCP Halo launch", flush=True)
            time.sleep(seconds)
            pauses.append({"before": str(folder_for(cell, group["graph"])), "seconds": seconds})
            (raw / "launcher_pauses.json").write_text(json.dumps(pauses, indent=2) + "\n")
        command(layout_command(group, p, t, [program,
                f'--communication={cell["communication"]}']), env)
        (folder / "performance_job.txt").write_text(env["PBS_JOBID"] + "\n")
        previous_dense_halo = p >= 256 and cell["communication"] == "halo"
    (raw / "measurement_complete.txt").write_text(env["PBS_JOBID"] + "\n")


def finalize(group, raw, env):
    env["PAGERANK_DATASET_MANIFEST"] = str(raw / "dataset.tsv")
    env["PAGERANK_HYBRID_MAX_TOTAL_THREADS"] = "512"
    records = [json.loads(line) for line in (raw / "cpu_hosts.jsonl").read_text().splitlines()]
    assert len({r["host"] for r in records}) == group["nodes"]
    if not group.get("validation_only"):
        assert all("Platinum 8452Y" in r["cpu_model"] for r in records), records
    for path in (raw / "mapping").glob("*.jsonl"):
        p, t = (int(v[1:]) for v in path.stem.split("_"))
        check_affinity([json.loads(line) for line in path.read_text().splitlines()], group, p, t)
    validations = defaultdict(list)
    for cell in group["cells"]:
        summary = json.loads((raw / folder_for(cell, group["graph"]) / "summary.json").read_text())
        assert summary["processes"] == cell["processes"]
        if cell["implementation"] == "hybrid":
            assert summary["threads_per_process"] == [cell["threads"]] * cell["processes"]
            assert summary["total_threads"] == group["cores"]
        elif cell["implementation"] == "mpi_kokkos":
            assert summary["actual_threads"] == cell["threads"]
        validations[cell["implementation"], cell["communication"]].append(cell)
    tasks = []
    logs = raw / "validation_logs"
    logs.mkdir(exist_ok=True)
    for (method, mode), cells in validations.items():
        settings = env.copy()
        if method == "hybrid":
            settings["PAGERANK_HYBRID_CONFIGS"] = " ".join(f'{c["processes"]}:{c["threads"]}' for c in cells)
            parts = ["python3", "scripts/validate_hybrid.py", mode, "--processes"]
            parts += [str(p) for p in sorted({c["processes"] for c in cells})]
            tasks.append((parts, settings, logs / f"{method}_{mode}.log"))
        elif method == "mpi":
            tasks.append((["python3", "scripts/validate_mpi.py", mode, "--processes"] +
                          [str(c["processes"]) for c in cells], settings, logs / f"{method}_{mode}.log"))
        else:
            for cell in cells:
                tasks.append((["python3", "scripts/validate_mpi_device.py", "mpi_kokkos", "OpenMP", mode,
                               "--threads", str(cell["threads"]), "--processes", str(cell["processes"])],
                              settings, logs / f'{method}_{mode}_t{cell["threads"]}.log'))
    for task in tasks:
        command(*task)
    root = Path.cwd() / "results/updated_vanda_scaling" / env["RUN_ID"]
    group_relative = raw.relative_to(Path(env["DATA_ROOT"]) / "results")
    archived = root / group_relative
    shutil.copytree(raw, archived, dirs_exist_ok=True, ignore=shutil.ignore_patterns("ranks.csv"))
    for cell in ([] if group.get("validation_only") else group["cells"]):
        source = raw / folder_for(cell, group["graph"])
        target = root / Path(cell["canonical_summary"]).parent
        if (target / "complete.txt").exists():
            continue
        target.mkdir(parents=True, exist_ok=True)
        for name in ("summary.json", "history.csv", "timings.csv", "performance_job.txt"):
            shutil.copy2(source / name, target / name)
        job = (source / "performance_job.txt").read_text().strip()
        proof = {"performance_job": job, "validation_job": env["PBS_JOBID"],
                 "group": str(group_relative), "cores": group["cores"], "nodes": group["nodes"],
                 "processes": cell["processes"], "threads": cell["threads"]}
        (target / "provenance.json").write_text(json.dumps(proof, indent=2) + "\n")
        (target / "complete.txt").write_text(job + "\n")
    (archived / "complete.txt").write_text((raw / "measurement_complete.txt").read_text())
    (archived / "validation_job.txt").write_text(env["PBS_JOBID"] + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("compute", "finalize"))
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    group = json.loads(args.plan.read_text())
    env = os.environ.copy()
    stage = "validation_core_groups" if group.get("validation_only") else group.get("raw_stage", "cpu_core_groups")
    raw = Path(env["DATA_ROOT"]) / "results" / stage / group["graph"] / f'nodes{group["nodes"]}_cores{group["cores_per_node"]}'
    raw.mkdir(parents=True, exist_ok=True)
    env.update(PAGERANK_RESULTS_ROOT=str(raw), PAGERANK_ENVIRONMENT="vanda-gcc13-release",
               PAGERANK_RUN_ID=env["RUN_ID"], PAGERANK_REPEATS="5", PAGERANK_WARMUPS="1",
               PAGERANK_HYBRID_MAX_TOTAL_THREADS="512",
               OMP_DYNAMIC="FALSE", OMP_PROC_BIND="spread", OMP_PLACES="cores")
    if args.mode == "compute":
        (raw / "group_plan.json").write_text(json.dumps(group, indent=2) + "\n")
        compute(group, raw, env)
    else:
        finalize(group, raw, env)


if __name__ == "__main__":
    main()

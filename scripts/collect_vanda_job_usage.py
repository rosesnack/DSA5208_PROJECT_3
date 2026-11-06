"""Save PBS requested resources and actual walltimes for a Vanda experiment run.

Run on a Vanda login node after updating submitted_jobs.tsv. The CPU-hour
columns are resource-time estimates; project accounting is authoritative.
"""
import argparse
import csv
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


def hours(clock):
    h, m, s = map(int, clock.split(":"))
    return h + m / 60 + s / 3600


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run_id")
args = parser.parse_args()
root = Path("results/updated_vanda_scaling") / args.run_id
with (root / "submitted_jobs.tsv").open(newline="", encoding="utf-8") as source:
    rows = [{**row, "job_role": "submitted"}
            for row in csv.DictReader(source, delimiter="\t")]
with (root / "retry_jobs.tsv").open(newline="", encoding="utf-8") as source:
    rows += [{"stage": row["stage"], "graph": row["graph"], "nodes": row["nodes"],
              "job_id": row["replacement_job"], "job_role": row["reason"]}
             for row in csv.DictReader(source, delimiter="\t")]
recovery_table = root / "free_cpu_recovery.tsv"
if recovery_table.is_file():
    with recovery_table.open(newline="", encoding="utf-8") as source:
        rows += [{"stage": row["stage"], "graph": row["graph"], "nodes": row["nodes"],
                  "job_id": row["replacement_job"], "job_role": "free_queue_recovery"}
                 for row in csv.DictReader(source, delimiter="\t")]
partial_core_table = root / "free_core_weak_jobs.tsv"
if partial_core_table.is_file():
    with partial_core_table.open(newline="", encoding="utf-8") as source:
        rows += [{"stage": "cpu_core_weak_partial", "graph": row["family"],
                  "nodes": "1/2/4", "job_id": row["job_id"],
                  "job_role": row["scope"]}
                 for row in csv.DictReader(source, delimiter="\t")]
for table, role in (("failed_jobs.tsv", "earlier_failed_attempt"),
                    ("replaced_jobs.tsv", "superseded_attempt")):
    with (root / table).open(newline="", encoding="utf-8") as source:
        rows += [{"stage": row["stage"], "graph": row["graph"],
                  "nodes": row["nodes"], "job_id": row["job_id"], "job_role": role}
                 for row in csv.DictReader(source, delimiter="\t")]
for stage, directory, marker_name, nodes in (
        ("serial", "serial_grid", "resume_serial_complete.txt", "1"),
        ("gpu", "gpu", "resume_gpu_complete.txt", "2")):
    rows += [{"stage": stage, "graph": marker.parent.name, "nodes": nodes,
              "job_id": marker.read_text(encoding="utf-8").strip(),
              "job_role": "resume_after_walltime"}
             for marker in (root / directory).glob(f"*/{marker_name}")]
known_ids = {row["job_id"] for row in rows}
for marker in (*root.rglob("*.complete"), *root.rglob("*complete*.txt")):
    job_id = marker.read_text(encoding="utf-8").strip()
    if re.fullmatch(r"\d+\.stdct-mgmt-02", job_id) and job_id not in known_ids:
        parts = marker.relative_to(root).parts
        stage = "serial" if parts[0] == "free_cpu_archive" else parts[0]
        rows.append({"stage": stage, "graph": parts[-2] if len(parts) > 1 else "-",
                     "nodes": "2" if stage == "gpu" else "1" if stage == "serial" else "-",
                     "job_id": job_id, "job_role": f"completion_marker:{marker.relative_to(root)}"})
        known_ids.add(job_id)

jobs = {}
ids = list(dict.fromkeys(row["job_id"] for row in rows))
for start in range(0, len(ids), 25):
    response = subprocess.check_output(
        ["qstat", "-x", "-f", "-F", "json", *ids[start:start + 25]],
        text=True)
    jobs.update(json.loads(response)["Jobs"])

timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
records = []
for row in rows:
    job = jobs[row["job_id"]]
    requested = job["Resource_List"]
    used = job.get("resources_used", {})
    cpu = int(requested["ncpus"])
    gpu = int(requested.get("ngpus", 0))
    requested_hours = hours(requested["walltime"])
    elapsed = hours(used["walltime"]) if "walltime" in used else None
    paid_cpu = job["queue"] == "batch_cpu"
    records.append({
        "queried_at": timestamp,
        "stage": row["stage"], "graph": row["graph"], "nodes": row["nodes"],
        "job_role": row["job_role"], "job_id": row["job_id"],
        "job_state": job["job_state"], "queue": job["queue"],
        "exit_status": job.get("Exit_status", ""),
        "allocated_ncpus": cpu, "allocated_ngpus": gpu,
        "requested_walltime": requested["walltime"],
        "actual_walltime": used.get("walltime", ""),
        "requested_core_hours": round(cpu * requested_hours, 3),
        "actual_core_hours": round(cpu * elapsed, 3) if elapsed is not None else "",
        "paid_cpu_reservation_hours": round(cpu * requested_hours, 3) if paid_cpu else 0,
        "paid_cpu_actual_hours": round(cpu * elapsed, 3) if paid_cpu and elapsed is not None else "",
        "actual_gpu_hours": round(gpu * elapsed, 3) if elapsed is not None else "",
    })

destination = root / "pbs_job_usage.csv"
with destination.open("w", newline="", encoding="utf-8") as output:
    writer = csv.DictWriter(output, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
print(f"Wrote {len(records)} PBS job records to {destination}")

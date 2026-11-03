"""Count validated Vanda matrix batches from completion markers and job IDs."""
import argparse
import csv
import os
import subprocess
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run_id")
parser.add_argument("--missing", action="store_true", help="List batches without a completion marker")
parser.add_argument("--qstat", action="store_true", help="Also show the current PBS queue")
args = parser.parse_args()

root = Path(__file__).resolve().parents[1] / "results" / "updated_vanda_scaling" / args.run_id
replacements = {}
recovery_table = root / "free_cpu_recovery.tsv"
for recovery_table in (recovery_table, root / "retry_jobs.tsv"):
    if recovery_table.is_file():
        with recovery_table.open(newline="", encoding="utf-8") as source:
            for replacement in csv.DictReader(source, delimiter="\t"):
                key = (replacement["stage"], replacement["graph"], replacement["nodes"])
                replacements[key] = replacement["replacement_job"]
markers = {
    "data": lambda row: root / "data.complete",
    "data_512": lambda row: root / "data_512.complete",
    "cpu_build": lambda row: root / "cpu_build.complete",
    "gpu_build": lambda row: root / "gpu_build.complete",
    "cpu_smoke": lambda row: root / "cpu_smoke_uniform" / "complete.txt",
    "gpu_smoke": lambda row: root / "gpu_smoke_uniform" / "complete.txt",
    "layout_probe": lambda row: root / "layout_probe.complete",
    "affinity_probe": lambda row: root / "affinity_probe.complete",
    "serial": lambda row: root / "serial_grid" / row["graph"] / "complete.txt",
    "mpi_strong": lambda row: root / "strong" / row["graph"] / f"nodes{row['nodes']}" / "complete.txt",
    "mpi_strong_512": lambda row: root / "strong" / row["graph"] / "nodes8_p512" / "complete.txt",
    "gpu": lambda row: root / "gpu" / row["graph"] / "complete.txt",
    "gpu_ext_4": lambda row: root / "gpu" / row["graph"] / "extension_gpu_p4.complete",
    "gpu_ext_8": lambda row: root / "gpu" / row["graph"] / "extension_gpu_p8.complete",
    "gpu_ext_validate": lambda row: root / "gpu" / row["graph"] / "complete_p4_p8.txt",
    "mpi_weak": lambda row: root / "weak" / "complete.txt",
    "mpi_weak_512": lambda row: root / "weak_512" / row["graph"] / "complete.txt",
    "gpu_weak": lambda row: root / "gpu_weak" / "complete.txt",
    "gpu_weak_ext_4": lambda row: root / "gpu_weak" / "extension_weak_gpu_p4.complete",
    "gpu_weak_ext_8": lambda row: root / "gpu_weak" / "extension_weak_gpu_p8.complete",
    "gpu_weak_ext_validate": lambda row: root / "gpu_weak" / "complete_p4_p8.txt",
    "kokkos_cpu_grid": lambda row: root / "kokkos_cpu_grid" / row["graph"] / f"nodes{row['nodes']}" / "complete.txt",
    "kokkos_cpu_512": lambda row: root / "kokkos_cpu_512" / row["graph"] / "complete.txt",
    "cpu_core_weak": lambda row: root / "weak_core" / row["graph"] / "complete_p256.txt",
    "cpu_core_weak_512": lambda row: root / "weak_core" / row["graph"] / "complete_p512.txt",
}
total, done = Counter(), Counter()
resumed_gpu = 0
missing = []
with (root / "submitted_jobs.tsv").open(newline="", encoding="utf-8") as source:
    for row in csv.DictReader(source, delimiter="\t"):
        stage = row["stage"]
        total[stage] += 1
        marker = markers[stage](row)
        if marker.exists():
            completed_job = marker.read_text(encoding="utf-8").strip()
            if completed_job == row["job_id"]:
                done[stage] += 1
                continue
            key = (stage, row["graph"], row["nodes"])
            if completed_job == replacements.get(key):
                done[stage] += 1
                continue
            if stage == "gpu" and (marker.parent / "resume_gpu_complete.txt").is_file():
                done[stage] += 1
                resumed_gpu += 1
                continue
            if stage == "serial" and (marker.parent / "resume_serial_complete.txt").is_file():
                done[stage] += 1
                continue
        missing.append(row)

for stage in markers:
    print(f"{stage:12s} {done[stage]:3d}/{total[stage]:3d} complete")
print(f"Total: {sum(done.values())}/{sum(total.values())} validated batches")
if resumed_gpu:
    print(f"GPU batches validated after resume: {resumed_gpu}")
if args.missing:
    for row in missing:
        print(f"pending {row['stage']:12s} {row['graph']:30s} "
              f"nodes={row['nodes']} job={row['job_id']}")
if args.qstat:
    subprocess.run(["qstat", "-u", os.environ["USER"]], check=False)

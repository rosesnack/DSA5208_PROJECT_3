"""Separate Xeon Gold free-queue pilot data from the Platinum project matrix."""
import csv
import os
import shutil
import sys
from pathlib import Path


run_id = sys.argv[1]
root = Path("results/updated_vanda_scaling") / run_id
data_root = Path(os.environ.get("DATA_ROOT", f"/scratch/{os.environ['USER']}/dsa5208_scaling/{run_id}"))
recovery_table = root / "free_cpu_recovery.tsv"
with recovery_table.open(newline="", encoding="utf-8") as source:
    recovered = list(csv.DictReader(source, delimiter="\t"))


def archive(stage, graph, nodes):
    suffix = Path(graph) if stage == "serial_grid" else Path(graph) / f"nodes{nodes}"
    for base, archive_base in (
        (root / stage, root / "free_cpu_archive" / stage),
        (data_root / "results" / stage, data_root / "results" / "free_cpu_archive" / stage),
    ):
        source = base / suffix
        if source.exists():
            destination = archive_base / suffix
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(source, destination)
            print(f"Archived {source} -> {destination}")


for row in recovered:
    if row["stage"] == "serial":
        archive("serial_grid", row["graph"], row["nodes"])
    elif row["stage"] == "mpi_strong":
        archive("strong", row["graph"], row["nodes"])

job_table = root / "submitted_jobs.tsv"
with job_table.open(newline="", encoding="utf-8") as source:
    rows = list(csv.DictReader(source, delimiter="\t"))
free_kokkos = [row for row in rows if row["stage"] == "kokkos_cpu_grid" and
               1513015 <= int(row["job_id"].split(".")[0]) <= 1513039]
for row in free_kokkos:
    archive("kokkos_cpu_grid", row["graph"], row["nodes"])
with (root / "free_cpu_archived_submissions.tsv").open("w", newline="", encoding="utf-8") as output:
    writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter="\t",
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(free_kokkos)
with job_table.open("w", newline="", encoding="utf-8") as output:
    writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter="\t",
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(row for row in rows if row not in free_kokkos)
recovery_table.rename(root / "free_cpu_archived.tsv")
print(f"Archived {len(recovered)} recovery submissions and {len(free_kokkos)} Kokkos submissions")

"""Release a bounded batch of held Vanda CPU matrix jobs after credits return."""
import argparse
import csv
import os
import subprocess
from pathlib import Path


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run_id")
parser.add_argument("--stages", nargs="+", required=True)
parser.add_argument("--max-jobs", type=int, default=8)
args = parser.parse_args()

table = Path("results/updated_vanda_scaling") / args.run_id / "submitted_jobs.tsv"
with table.open(newline="", encoding="utf-8") as source:
    rows = list(csv.DictReader(source, delimiter="\t"))
held = set(subprocess.check_output(
    ["qselect", "-u", os.environ["USER"], "-s", "H", "-q", "batch_cpu"],
    text=True).splitlines())
selected = [row["job_id"] for stage in args.stages for row in rows
            if row["stage"] == stage and row["job_id"] in held]
selected = selected[:args.max_jobs]
if selected:
    subprocess.run(["qrls", *selected], check=True)
for job in selected:
    print(job)
print(f"Released {len(selected)} held CPU matrix jobs")

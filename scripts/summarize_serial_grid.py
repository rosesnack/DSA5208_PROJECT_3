"""Create a CSV of serial runtime against vertex and edge counts."""
import csv
import json
import os
from pathlib import Path

from validate_serial import DATASETS, RESULTS_ROOT

output_path = RESULTS_ROOT / "serial_scaling.csv"
output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", newline="", encoding="utf-8") as output:
    fields = ("dataset", "family", "vertices", "edges", "average_degree", "median_s", "min_s", "max_s")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for name, _ in DATASETS.items():
        if not name.startswith("grid_"):
            continue
        family = name.split("_n", 1)[0].removeprefix("grid_")
        summary_path = RESULTS_ROOT / "serial" / name / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        nodes, edges = summary["nodes"], summary["edges"]
        writer.writerow({"dataset": name, "family": family, "vertices": nodes, "edges": edges,
                         "average_degree": edges / nodes, "median_s": summary["solve_median_s"],
                         "min_s": summary["solve_min_s"], "max_s": summary["solve_max_s"]})
print(output_path)

"""Validate weak-scaling results and calculate efficiency from p=1 references."""
import csv
import json
import os
from pathlib import Path

from validate_serial import DATASETS, RESULTS_ROOT, validate

PROCESS_COUNTS = tuple(int(value) for value in os.environ["PAGERANK_PROCESS_COUNTS"].split())
VERTICES_PER_RANK = int(os.environ.get("PAGERANK_WEAK_VERTICES_PER_RANK", "50000"))
EDGES_PER_RANK = int(os.environ.get("PAGERANK_WEAK_EDGES_PER_RANK", "800000"))
checks = []
rows = []

for communication, folder_name in (("allgather", "mpi"), ("halo", "mpi_halo")):
    for family in ("controlled", "uniform", "hub"):
        measurements = []
        for processes in PROCESS_COUNTS:
            name = f"weak_{family}_p{processes:03d}"
            edge_path, node_path = DATASETS[name]
            folder = RESULTS_ROOT / folder_name / name / f"p{processes}"
            print(f"Checking {communication} {name}/p{processes}...", flush=True)
            try:
                check = validate(name, edge_path, node_path, folder)
                summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
                assert summary["implementation"] == "mpi"
                assert summary["processes"] == processes
                expected = "allgather" if communication == "allgather" else "halo"
                assert summary["communication"] == expected
                assert summary["nodes"] == VERTICES_PER_RANK * processes
                assert summary["edges"] == EDGES_PER_RANK * processes
                assert summary["nodes"] // processes == VERTICES_PER_RANK
                assert summary["edges"] // processes == EDGES_PER_RANK
                check.update(communication=communication, processes=processes, family=family)
                measurements.append((processes, summary, check))
                print(f"PASS: {summary['nodes']} vertices, {summary['edges']} edges, "
                      f"median={summary['solve_median_s']:.6g}s", flush=True)
            except (AssertionError, OSError, ValueError, KeyError) as error:
                check = {"dataset": name, "communication": communication, "processes": processes,
                         "family": family, "passed": False, "error": str(error)}
                checks.append(check)
                print(f"FAIL: {name}/p{processes}: {error}", flush=True)
                continue
            checks.append(check)

        reference_summary = next(summary for processes, summary, _ in measurements if processes == 1)
        reference_step = reference_summary["solve_median_s"] / reference_summary["iterations"]
        for processes, summary, check in measurements:
            median = summary["solve_median_s"]
            seconds_per_iteration = median / summary["iterations"]
            check["seconds_per_iteration"] = seconds_per_iteration
            check["iteration_efficiency"] = reference_step / seconds_per_iteration
            check["iteration_scaled_speedup"] = processes * reference_step / seconds_per_iteration
            check["solve_time_efficiency"] = reference_summary["solve_median_s"] / median
            rows.append({"family": family, "communication": communication, "processes": processes,
                         "vertices": summary["nodes"], "edges": summary["edges"],
                         "vertices_per_rank": summary["nodes"] / processes,
                         "edges_per_rank": summary["edges"] / processes,
                         "iterations": summary["iterations"], "median_s": median,
                         "seconds_per_iteration": seconds_per_iteration,
                         "iteration_scaled_speedup": check["iteration_scaled_speedup"],
                         "iteration_efficiency": check["iteration_efficiency"],
                         "solve_time_efficiency": check["solve_time_efficiency"],
                         "communication_s": summary.get("communication_max_s"),
                         "communication_bytes_per_iteration": summary.get("communication_bytes_per_iteration"),
                         "communication_setup_bytes": summary.get("communication_setup_bytes")})

report = {"passed": sum(check["passed"] for check in checks),
          "failed": sum(not check["passed"] for check in checks),
          "process_counts": PROCESS_COUNTS,
          "graph_families": ("controlled", "uniform", "hub"),
          "method": "Independent residual, rank mass, history, and repeated-timing checks; each family uses its own p=1 reference",
          "checks": checks}
report_path = RESULTS_ROOT / "weak_scaling_validation.json"
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
with (RESULTS_ROOT / "weak_scaling.csv").open("w", newline="", encoding="utf-8") as output:
    writer = csv.DictWriter(output, fieldnames=("family", "communication", "processes", "vertices", "edges",
                                                "vertices_per_rank", "edges_per_rank", "median_s",
                                                "iterations", "seconds_per_iteration", "iteration_scaled_speedup",
                                                "iteration_efficiency", "solve_time_efficiency", "communication_s",
                                                "communication_bytes_per_iteration", "communication_setup_bytes"))
    writer.writeheader()
    writer.writerows(rows)
print(f"Weak-scaling validation: {report_path}")
raise SystemExit(0 if report["failed"] == 0 else 1)

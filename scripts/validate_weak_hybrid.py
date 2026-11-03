"""Validate MPI+OpenMP weak scaling for both communication strategies."""
import csv
import json
import os

from validate_serial import DATASETS, RESULTS_ROOT, validate

PROCESS_COUNTS = tuple(int(value) for value in os.environ.get(
    "PAGERANK_WEAK_HYBRID_PROCESSES", "1 2 4 8 16 32 64").split())
THREADS = int(os.environ.get("PAGERANK_WEAK_HYBRID_THREADS", "4"))
VERTICES_PER_RANK = int(os.environ.get("PAGERANK_WEAK_VERTICES_PER_RANK", "50000"))
EDGES_PER_RANK = int(os.environ.get("PAGERANK_WEAK_EDGES_PER_RANK", "800000"))
checks, rows = [], []

for communication, implementation_root in (("allgather", "hybrid"), ("halo", "hybrid_halo")):
    for family in ("uniform", "hub", "controlled"):
        measurements = []
        for processes in PROCESS_COUNTS:
            name = f"weak_{family}_p{processes:03d}"
            edge_path, node_path = DATASETS[name]
            folder = RESULTS_ROOT / implementation_root / name / f"p{processes}_t{THREADS}"
            print(f"Checking {implementation_root}/{name}/p{processes}_t{THREADS}...", flush=True)
            try:
                check = validate(name, edge_path, node_path, folder)
                summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
                assert summary["implementation"] == "hybrid"
                assert summary["processes"] == processes
                assert summary["requested_threads"] == THREADS
                assert summary["communication"] in (("allgather", "allgatherv") if communication == "allgather" else ("halo",))
                assert summary["nodes"] == VERTICES_PER_RANK * processes
                assert summary["edges"] == EDGES_PER_RANK * processes
                assert summary["total_threads"] == THREADS * processes
                check.update(family=family, communication=communication, processes=processes,
                             requested_threads=THREADS)
                measurements.append((processes, summary, check))
                checks.append(check)
                print(f"PASS: median={summary['solve_median_s']:.6g}s", flush=True)
            except (AssertionError, OSError, ValueError, KeyError) as error:
                checks.append({"dataset": name, "family": family, "communication": communication,
                               "processes": processes, "requested_threads": THREADS,
                               "passed": False, "error": str(error)})
                print(f"FAIL: {name}/p{processes}_t{THREADS}: {error}", flush=True)
        reference = next(summary for processes, summary, _ in measurements if processes == 1)
        reference_step = reference["solve_median_s"] / reference["iterations"]
        for processes, summary, check in measurements:
            seconds_per_iteration = summary["solve_median_s"] / summary["iterations"]
            check["iteration_efficiency"] = reference_step / seconds_per_iteration
            rows.append({"family": family, "communication": communication,
                         "processes": processes, "threads_per_rank": THREADS,
                         "total_threads": summary["total_threads"],
                         "vertices": summary["nodes"], "edges": summary["edges"],
                         "iterations": summary["iterations"], "median_s": summary["solve_median_s"],
                         "seconds_per_iteration": seconds_per_iteration,
                         "iteration_efficiency": check["iteration_efficiency"],
                         "solve_time_efficiency": reference["solve_median_s"] / summary["solve_median_s"],
                         "communication_s": summary["communication_max_s"],
                         "communication_bytes_per_iteration": summary["communication_bytes_per_iteration"],
                         "communication_setup_s": summary["communication_setup_s"],
                         "communication_setup_bytes": summary["communication_setup_bytes"]})

report = {"passed": sum(check["passed"] for check in checks),
          "failed": sum(not check["passed"] for check in checks),
          "process_counts": PROCESS_COUNTS, "threads_per_rank": THREADS,
          "method": "Independent rank residual and repeated-timing checks; per-iteration p=1 weak reference",
          "checks": checks}
(RESULTS_ROOT / "weak_hybrid_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
with (RESULTS_ROOT / "weak_hybrid_scaling.csv").open("w", newline="", encoding="utf-8") as output:
    fields = ("family", "communication", "processes", "threads_per_rank", "total_threads",
              "vertices", "edges", "iterations", "median_s", "seconds_per_iteration",
              "iteration_efficiency", "solve_time_efficiency", "communication_s",
              "communication_bytes_per_iteration", "communication_setup_s", "communication_setup_bytes")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
raise SystemExit(0 if report["failed"] == 0 else 1)

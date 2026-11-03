"""Validate MPI+CUDA or MPI+Kokkos results against the same-environment Serial run."""
import argparse
import csv
import json
import math
import os

from validate_serial import DATASETS, RESULTS_ROOT, read_csv, validate

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("implementation", choices=("mpi_cuda", "mpi_kokkos"))
parser.add_argument("backend", help="Cuda or OpenMP execution backend")
parser.add_argument("communication", choices=("allgather", "halo"))
parser.add_argument("--processes", nargs="+", type=int, required=True)
parser.add_argument("--threads", type=int, default=1)
args = parser.parse_args()

results = RESULTS_ROOT / (args.implementation + ("_halo" if args.communication == "halo" else "")) / args.backend
serial_results = RESULTS_ROOT / "serial"
checks, scaling = [], []

for name, (edge_path, node_path) in DATASETS.items():
    baseline_folder = serial_results / name
    print(f"Checking Serial baseline for {name}...", flush=True)
    try:
        validate(name, edge_path, node_path, baseline_folder)
        baseline = json.loads((baseline_folder / "summary.json").read_text(encoding="utf-8"))
        assert baseline["implementation"] == "serial"
        serial_ranks = {int(row["node_id"]): float(row["rank"])
                        for row in read_csv(baseline_folder / "ranks.csv")}
    except (AssertionError, OSError, ValueError, KeyError) as error:
        checks.extend({"dataset": name, "processes": p, "passed": False,
                       "error": f"Serial baseline: {error}"} for p in args.processes)
        continue
    for processes in args.processes:
        configuration = f"p{processes}_t{args.threads}" if args.threads > 1 else f"p{processes}"
        folder = results / name / configuration
        print(f"Checking {args.implementation}/{args.backend}/{args.communication}/{name}/p{processes}...", flush=True)
        try:
            check = validate(name, edge_path, node_path, folder)
            summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
            assert summary["implementation"] == args.implementation
            assert summary["backend"] == args.backend
            assert summary["communication"] == args.communication
            assert summary["processes"] == processes
            assert summary.get("requested_threads", 1) == args.threads
            assert summary.get("actual_threads", 1) == args.threads
            for key in ("dataset", "environment", "build_type", "nodes", "edges", "alpha",
                        "tolerance_l1", "max_iterations", "fixed_iterations", "warmup_runs", "repeat_runs"):
                assert summary[key] == baseline[key], f"Serial/MPI+device settings differ: {key}"
            parallel_ranks = {int(row["node_id"]): float(row["rank"])
                              for row in read_csv(folder / "ranks.csv")}
            assert serial_ranks.keys() == parallel_ranks.keys(), "Node IDs differ"
            rank_l1 = math.fsum(abs(value - parallel_ranks[node]) for node, value in serial_ranks.items())
            assert rank_l1 <= 1e-8, f"Rank L1 difference is {rank_l1:.3e}"
            row = {"dataset": name, "implementation": args.implementation,
                   "backend": args.backend, "communication": args.communication,
                   "processes": processes, "serial_s": baseline["solve_median_s"],
                   "requested_threads": args.threads,
                   "parallel_s": summary["solve_median_s"],
                   "speedup": baseline["solve_median_s"] / summary["solve_median_s"],
                   "communication_s": summary["communication_median_s"],
                   "communication_bytes_per_iteration": summary["communication_bytes_per_iteration"],
                   "communication_setup_s": summary["communication_setup_s"],
                   "communication_setup_bytes": summary["communication_setup_bytes"],
                   "backend_compute_s": summary["backend_compute_median_s"],
                   "transfer_s": summary["transfer_median_s"], "rank_l1_error": rank_l1}
            scaling.append(row)
            checks.append({**check, **row})
            print(f"PASS: rank L1={rank_l1:.3e}, speedup={row['speedup']:.3g}", flush=True)
        except (AssertionError, OSError, ValueError, KeyError) as error:
            checks.append({"dataset": name, "processes": processes, "passed": False, "error": str(error)})
            print(f"FAIL: {name}/p{processes}: {error}", flush=True)

report = {"implementation": args.implementation, "backend": args.backend,
          "communication": args.communication, "process_counts": args.processes,
          "requested_threads": args.threads,
          "passed": sum(check["passed"] for check in checks),
          "failed": sum(not check["passed"] for check in checks),
          "method": "Independent residual and full-rank comparison to the same-environment Serial run",
          "checks": checks}
report_root = results / f"threads_{args.threads}" if args.threads > 1 else results
report_root.mkdir(parents=True, exist_ok=True)
suffix = os.environ.get("PAGERANK_REPORT_SUFFIX", "")
(report_root / f"validation{suffix}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
with (report_root / f"scaling{suffix}.csv").open("w", newline="", encoding="utf-8") as output:
    fields = ("dataset", "implementation", "backend", "communication", "processes", "serial_s",
              "requested_threads",
              "parallel_s", "speedup", "communication_s", "communication_bytes_per_iteration",
              "communication_setup_s", "communication_setup_bytes", "backend_compute_s",
              "transfer_s", "rank_l1_error")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(scaling)
raise SystemExit(0 if report["failed"] == 0 else 1)

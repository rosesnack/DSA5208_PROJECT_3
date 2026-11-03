"""Validate a weak-scaling MPI method for both communication modes."""
import argparse
import csv
import itertools
import json
import math
import os

from validate_serial import DATASETS, RESULTS_ROOT, read_csv, validate

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("implementation", choices=("mpi", "hybrid", "mpi_cuda", "mpi_kokkos"))
parser.add_argument("--backend", default="")
parser.add_argument("--threads", type=int, default=1)
parser.add_argument("--graph-scale", type=int, default=1,
                    help="Graph-size multiplier per MPI rank; use 4 for core-normalized T=4 weak scaling")
parser.add_argument("--processes", nargs="+", type=int, required=True)
parser.add_argument("--suffix", default="")
parser.add_argument("--families", nargs="+", choices=("uniform", "hub", "controlled"),
                    default=("uniform", "hub", "controlled"))
args = parser.parse_args()
VERTICES_PER_RANK = int(os.environ.get("PAGERANK_WEAK_VERTICES_PER_RANK", "50000"))
EDGES_PER_RANK = int(os.environ.get("PAGERANK_WEAK_EDGES_PER_RANK", "800000"))


def result_folder(communication, family, processes):
    method = args.implementation + ("_halo" if communication == "halo" else "")
    root = RESULTS_ROOT / method
    if args.backend:
        root /= args.backend
    name = f"weak_{family}_p{processes * args.graph_scale:03d}"
    threaded = args.implementation == "hybrid" or (args.implementation == "mpi_kokkos" and args.threads > 1)
    configuration = f"p{processes}_t{args.threads}" if threaded else f"p{processes}"
    return root / name / configuration


def paired_rank_error(family, processes):
    first = read_csv(result_folder("allgather", family, processes) / "ranks.csv")
    second = read_csv(result_folder("halo", family, processes) / "ranks.csv")
    def errors():
        for left, right in itertools.zip_longest(first, second):
            assert left is not None and right is not None, "Allgatherv/Halo rank counts differ"
            assert left["node_id"] == right["node_id"], "Allgatherv/Halo node IDs differ"
            yield abs(float(left["rank"]) - float(right["rank"]))
    return math.fsum(errors())


checks, rows = [], []
for family in args.families:
    for communication in ("allgather", "halo"):
        measurements = []
        for processes in args.processes:
            name = f"weak_{family}_p{processes * args.graph_scale:03d}"
            edge_path, node_path = DATASETS[name]
            folder = result_folder(communication, family, processes)
            print(f"Checking {args.implementation}/{args.backend}/{communication}/{name}...", flush=True)
            try:
                check = validate(name, edge_path, node_path, folder)
                summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
                assert summary["implementation"] == args.implementation
                assert summary["processes"] == processes
                assert summary["communication"] in (("allgather", "allgatherv") if communication == "allgather" else ("halo",))
                assert summary["nodes"] == VERTICES_PER_RANK * processes * args.graph_scale
                assert summary["edges"] == EDGES_PER_RANK * processes * args.graph_scale
                if args.backend:
                    assert summary["backend"] == args.backend
                if args.implementation == "hybrid":
                    assert summary["requested_threads"] == args.threads
                if args.implementation == "mpi_kokkos":
                    assert summary.get("requested_threads", 1) == args.threads
                    assert summary.get("actual_threads", 1) == args.threads
                check.update(communication=communication, family=family, processes=processes)
                checks.append(check)
                measurements.append((processes, summary))
            except (AssertionError, OSError, ValueError, KeyError) as error:
                checks.append({"dataset": name, "family": family, "communication": communication,
                               "processes": processes, "passed": False, "error": str(error)})
        reference = (next(summary for processes, summary in measurements if processes == 1)
                     if 1 in args.processes else
                     json.loads((result_folder(communication, family, 1) / "summary.json").read_text(encoding="utf-8")))
        reference_step = reference["solve_median_s"] / reference["iterations"]
        for processes, summary in measurements:
            for key in ("environment", "build_type", "alpha", "tolerance_l1", "max_iterations",
                        "fixed_iterations", "warmup_runs", "repeat_runs"):
                assert summary[key] == reference[key], f"Weak p=1 settings differ: {key}"
            median = summary["solve_median_s"]
            step = median / summary["iterations"]
            rows.append({"family": family, "implementation": args.implementation,
                         "backend": args.backend, "communication": communication,
                         "processes": processes, "threads_per_rank": args.threads,
                         "cpu_cores": processes * args.threads,
                         "graph_scale": args.graph_scale,
                         "vertices": summary["nodes"], "edges": summary["edges"],
                         "iterations": summary["iterations"], "median_s": median,
                         "seconds_per_iteration": step,
                         "iteration_efficiency": reference_step / step,
                         "solve_time_efficiency": reference["solve_median_s"] / median,
                         "communication_s": summary["communication_max_s"],
                         "communication_bytes_per_iteration": summary["communication_bytes_per_iteration"],
                         "communication_setup_s": summary["communication_setup_s"]})

for family in args.families:
    for processes in args.processes:
        error = paired_rank_error(family, processes)
        passed = error <= 1e-8
        checks.append({"dataset": f"weak_{family}_p{processes * args.graph_scale:03d}", "processes": processes,
                       "family": family, "comparison": "Allgatherv versus Halo",
                       "rank_l1_error": error, "passed": passed})
        print(f"Paired modes: {family} p{processes}, rank L1={error:.3e}", flush=True)

root = RESULTS_ROOT / f"weak_{args.implementation}_{args.backend or 'cpu'}_t{args.threads}{args.suffix}"
root.mkdir(parents=True, exist_ok=True)
report = {"implementation": args.implementation, "backend": args.backend,
          "threads_per_rank": args.threads, "graph_scale": args.graph_scale,
          "process_counts": args.processes,
          "passed": sum(check["passed"] for check in checks),
          "failed": sum(not check["passed"] for check in checks), "checks": checks}
(root / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
with (root / "scaling.csv").open("w", newline="", encoding="utf-8") as output:
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
raise SystemExit(0 if report["failed"] == 0 else 1)

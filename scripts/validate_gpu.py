"""Validate native CUDA or one selected Kokkos backend against the serial reference."""
import argparse
import csv
import json
import math

from validate_serial import DATASETS, RESULTS_ROOT, ROOT, read_csv, validate

RANK_L1_TOLERANCE = 1e-8


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("implementation", choices=("cuda", "kokkos"))
    parser.add_argument("backend", nargs="?", help="Kokkos execution-space name, e.g. Cuda or OpenMP")
    args = parser.parse_args()
    if args.implementation == "kokkos" and not args.backend:
        parser.error("the Kokkos execution-space name is required")

    implementation_root = RESULTS_ROOT / args.implementation
    if args.implementation == "kokkos":
        implementation_root /= args.backend
    serial_root = RESULTS_ROOT / "serial"
    checks, scaling = [], []

    for name, (edge_path, node_path) in DATASETS.items():
        baseline_folder = serial_root / name
        folder = implementation_root / name
        print(f"Checking {args.implementation}/{name}...", flush=True)
        try:
            validate(name, edge_path, node_path, baseline_folder)
            validate(name, edge_path, node_path, folder)
            baseline = json.loads((baseline_folder / "summary.json").read_text(encoding="utf-8"))
            summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
            assert summary["implementation"] == args.implementation
            if args.implementation == "kokkos":
                assert summary["backend"] == args.backend
            for key in ("dataset", "environment", "build_type", "nodes", "edges", "alpha",
                        "tolerance_l1", "max_iterations", "fixed_iterations", "warmup_runs", "repeat_runs"):
                assert summary.get(key) == baseline.get(key), f"Serial/GPU settings differ: {key}"

            serial_ranks = {int(row["node_id"]): float(row["rank"])
                            for row in read_csv(baseline_folder / "ranks.csv")}
            parallel_ranks = {int(row["node_id"]): float(row["rank"])
                              for row in read_csv(folder / "ranks.csv")}
            assert serial_ranks.keys() == parallel_ranks.keys(), "Serial/GPU node IDs differ"
            errors = [abs(value - parallel_ranks[node]) for node, value in serial_ranks.items()]
            l1_error, max_error = math.fsum(errors), max(errors)
            assert l1_error <= RANK_L1_TOLERANCE, f"Rank L1 error too large: {l1_error:.3e}"
            speedup = baseline["solve_median_s"] / summary["solve_median_s"]
            row = {"dataset": name, "implementation": args.implementation,
                   "backend": summary.get("backend", "CUDA"),
                   "serial_s": baseline["solve_median_s"],
                   "parallel_s": summary["solve_median_s"], "speedup": speedup,
                   "rank_l1_error": l1_error, "rank_max_error": max_error}
            scaling.append(row)
            checks.append({"dataset": name, "passed": True, **row,
                           "iterations": summary["iterations"],
                           "residual_l1": summary["max_residual_l1"],
                           "rank_sum_error": summary["max_rank_sum_error"]})
            print(f"PASS: rank L1 error={l1_error:.3e}, speedup={speedup:.2f}", flush=True)
        except (AssertionError, OSError, ValueError, KeyError) as error:
            checks.append({"dataset": name, "passed": False, "error": str(error)})
            print(f"FAIL: {name}: {error}", flush=True)

    passed = sum(check["passed"] for check in checks)
    report = {"implementation": args.implementation, "backend": args.backend,
              "passed": passed, "failed": len(checks) - passed,
              "method": "Independent residual checks and full rank comparison with validated serial output",
              "rank_l1_tolerance": RANK_L1_TOLERANCE, "checks": checks}
    implementation_root.mkdir(parents=True, exist_ok=True)
    (implementation_root / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if scaling:
        with (implementation_root / "scaling.csv").open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=list(scaling[0]))
            writer.writeheader()
            writer.writerows(scaling)
    print(f"Validation report: {implementation_root / 'validation.json'}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

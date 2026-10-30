"""Validate saved OpenMP runs and compare their ranks and timings with serial runs."""
import csv
import json
import math

from validate_serial import DATASETS, RESULTS_ROOT, ROOT, read_csv, validate

RESULTS = RESULTS_ROOT / "openmp"
SERIAL_RESULTS = RESULTS_ROOT / "serial"
THREAD_COUNTS = (1, 2, 4, 8)
RANK_L1_TOLERANCE = 1e-8


def compare(name, folder, threads, baseline, serial_ranks):
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    assert summary["implementation"] == "openmp", "Wrong implementation label"
    assert summary["requested_threads"] == threads, "Wrong requested thread count"
    assert 1 <= summary["threads"] <= threads, "Invalid actual thread count"
    assert all(int(row["threads"]) == summary["threads"] for row in read_csv(folder / "timings.csv")), "Team size changed between repeats"
    for key in ("dataset", "environment", "nodes", "edges", "alpha", "tolerance_l1",
                "max_iterations", "fixed_iterations", "warmup_runs", "repeat_runs", "build_type"):
        assert summary.get(key) == baseline.get(key), f"Serial/OpenMP settings differ: {key}"

    # Match original IDs, so comparison does not depend on row order.
    parallel_ranks = {int(row["node_id"]): float(row["rank"]) for row in read_csv(folder / "ranks.csv")}
    assert parallel_ranks.keys() == serial_ranks.keys(), "Serial/OpenMP node IDs differ"
    errors = [abs(rank - parallel_ranks[node]) for node, rank in serial_ranks.items()]
    l1_error, max_error = math.fsum(errors), max(errors)
    assert l1_error <= RANK_L1_TOLERANCE, f"Serial/OpenMP rank error too large: {l1_error:.3e}"
    speedup = baseline["solve_median_s"] / summary["solve_median_s"]
    return {"dataset": name, "requested_threads": threads, "threads": summary["threads"],
            "serial_s": baseline["solve_median_s"], "openmp_s": summary["solve_median_s"],
            "speedup": speedup, "efficiency": speedup / summary["threads"],
            "rank_l1_error": l1_error, "rank_max_error": max_error}


def main():
    checks, scaling = [], []
    for name, (edge_path, node_path) in DATASETS.items():
        # Validate the serial reference before using it to assess the parallel output.
        print(f"Checking {name} serial reference...", flush=True)
        try:
            validate(name, edge_path, node_path, SERIAL_RESULTS / name)
            baseline = json.loads((SERIAL_RESULTS / name / "summary.json").read_text(encoding="utf-8"))
            assert baseline["implementation"] == "serial", "Wrong reference implementation"
            serial_ranks = {int(row["node_id"]): float(row["rank"])
                            for row in read_csv(SERIAL_RESULTS / name / "ranks.csv")}
        except (AssertionError, OSError, ValueError, KeyError) as error:
            checks.extend({"dataset": name, "requested_threads": t, "passed": False,
                        "error": f"Serial reference: {error}"} for t in THREAD_COUNTS)
            print(f"FAIL: {name} serial reference: {error}", flush=True)
            continue
        for threads in THREAD_COUNTS:
            folder = RESULTS / name / f"t{threads}"
            print(f"Checking {name}/t{threads}...", flush=True)
            try:
                check = validate(name, edge_path, node_path, folder)
                comparison = compare(name, folder, threads, baseline, serial_ranks)
                check.update(comparison)
                scaling.append(comparison)
                print(f"PASS: L1 error={comparison['rank_l1_error']:.3e}, speedup={comparison['speedup']:.2f}", flush=True)
            except (AssertionError, OSError, ValueError, KeyError) as error:
                check = {"dataset": name, "requested_threads": threads, "passed": False, "error": str(error)}
                print(f"FAIL: {name}/t{threads}: {error}", flush=True)
            checks.append(check)
    passed = sum(check["passed"] for check in checks)
    report = {"passed": passed, "failed": len(checks) - passed,
            "method": "Independent residual checks and full rank comparison with validated serial output",
            "rank_l1_tolerance": RANK_L1_TOLERANCE, "checks": checks}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with (RESULTS / "scaling.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["dataset", "requested_threads", "threads", "serial_s", "openmp_s",
                                                "speedup", "efficiency", "rank_l1_error", "rank_max_error"])
        writer.writeheader()
        writer.writerows(scaling)
    print(f"Validation and scaling results: {RESULTS}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

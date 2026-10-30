"""Validate saved MPI + OpenMP runs and compare their ranks and timings with serial runs."""
import argparse
import csv
import json
import math

from validate_serial import DATASETS, RESULTS_ROOT, ROOT, read_csv, validate

RESULTS = RESULTS_ROOT / "hybrid"
SERIAL_RESULTS = RESULTS_ROOT / "serial"
THREAD_COUNTS = (1, 2, 4, 8)
MAX_TOTAL_THREADS = 8
RANK_L1_TOLERANCE = 1e-8


def compare(name, folder, processes, threads, baseline, serial_ranks):
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    assert summary["implementation"] == "hybrid", "Wrong implementation label"
    assert summary["processes"] == processes, "Wrong process count"
    assert all(int(row["processes"]) == summary["processes"] for row in read_csv(folder / "timings.csv")), "Process count changed between repeats"
    assert summary["requested_threads"] == threads, "Wrong requested thread count"
    actual = summary["threads_per_process"]
    assert len(actual) == processes and all(1 <= count <= threads for count in actual), "Invalid actual team sizes"
    total_threads = sum(actual)
    assert summary["total_threads"] == total_threads, "Wrong total thread count"
    assert summary["mpi_thread_mode"] == "funneled", "Wrong MPI thread mode"
    for row in read_csv(folder / "timings.csv"):
        assert int(row["threads_min"]) == min(actual) and int(row["threads_max"]) == max(actual), "Team sizes changed between repeats"
        assert int(row["total_threads"]) == total_threads, "Total thread count changed between repeats"
    for key in ("dataset", "environment", "nodes", "edges", "alpha", "tolerance_l1",
                "max_iterations", "fixed_iterations", "warmup_runs", "repeat_runs", "build_type"):
        assert summary.get(key) == baseline.get(key), f"Serial/hybrid settings differ: {key}"

    # Match original IDs, so comparison does not depend on row order.
    parallel_ranks = {int(row["node_id"]): float(row["rank"]) for row in read_csv(folder / "ranks.csv")}
    assert parallel_ranks.keys() == serial_ranks.keys(), "Serial/hybrid node IDs differ"
    errors = [abs(rank - parallel_ranks[node]) for node, rank in serial_ranks.items()]
    l1_error, max_error = math.fsum(errors), max(errors)
    assert l1_error <= RANK_L1_TOLERANCE, f"Serial/hybrid rank error too large: {l1_error:.3e}"
    speedup = baseline["solve_median_s"] / summary["solve_median_s"]
    return {"dataset": name, "processes": processes, "requested_threads": threads,
            "threads_min": min(actual), "threads_max": max(actual), "total_threads": total_threads,
            "serial_s": baseline["solve_median_s"], "hybrid_s": summary["solve_median_s"],
            "speedup": speedup, "efficiency": speedup / total_threads,
            "rank_l1_error": l1_error, "rank_max_error": max_error}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processes", nargs="+", type=int, choices=(1, 2, 4, 8),
                        default=(1, 2, 4, 8), help="MPI process counts to validate")
    processes_to_validate = tuple(dict.fromkeys(parser.parse_args().processes))
    configurations = [(p, t) for p in processes_to_validate for t in THREAD_COUNTS
                      if p * t <= MAX_TOTAL_THREADS]
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
            checks.extend({"dataset": name, "processes": p, "requested_threads": t, "passed": False,
                        "error": f"Serial reference: {error}"} for p, t in configurations)
            print(f"FAIL: {name} serial reference: {error}", flush=True)
            continue
        for processes, threads in configurations:
            folder = RESULTS / name / f"p{processes}_t{threads}"
            print(f"Checking {name}/p{processes}_t{threads}...", flush=True)
            try:
                check = validate(name, edge_path, node_path, folder)
                comparison = compare(name, folder, processes, threads, baseline, serial_ranks)
                check.update(comparison)
                scaling.append(comparison)
                print(f"PASS: L1 error={comparison['rank_l1_error']:.3e}, speedup={comparison['speedup']:.2f}", flush=True)
            except (AssertionError, OSError, ValueError, KeyError) as error:
                check = {"dataset": name, "processes": processes, "requested_threads": threads, "passed": False, "error": str(error)}
                print(f"FAIL: {name}/p{processes}_t{threads}: {error}", flush=True)
            checks.append(check)
    passed = sum(check["passed"] for check in checks)
    report = {"passed": passed, "failed": len(checks) - passed,
            "process_counts": processes_to_validate,
            "method": "Independent residual checks and full rank comparison with validated serial output",
            "rank_l1_tolerance": RANK_L1_TOLERANCE, "checks": checks}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with (RESULTS / "scaling.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["dataset", "processes", "requested_threads", "threads_min", "threads_max", "total_threads", "serial_s", "hybrid_s",
                                                "speedup", "efficiency", "rank_l1_error", "rank_max_error"])
        writer.writeheader()
        writer.writerows(scaling)
    print(f"Validation and scaling results: {RESULTS}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

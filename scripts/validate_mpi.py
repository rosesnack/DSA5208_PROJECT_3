"""Validate saved MPI runs and compare their ranks and timings with serial runs."""
import csv
import json
import math

from validate_serial import DATASETS, ROOT, read_csv, validate

RESULTS = ROOT / "results/mpi"
SERIAL_RESULTS = ROOT / "results/serial"
PROCESS_COUNTS = (1, 2, 4, 8)
RANK_L1_TOLERANCE = 1e-8


def compare(name, folder, processes, baseline, serial_ranks):
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    assert summary["implementation"] == "mpi", "Wrong implementation label"
    assert summary["processes"] == processes, "Wrong process count"
    assert all(int(row["processes"]) == summary["processes"] for row in read_csv(folder / "timings.csv")), "Process count changed between repeats"
    for key in ("dataset", "environment", "nodes", "edges", "alpha", "tolerance_l1",
                "max_iterations", "fixed_iterations", "warmup_runs", "repeat_runs"):
        assert summary[key] == baseline[key], f"Serial/MPI settings differ: {key}"

    # Match original IDs, so comparison does not depend on row order.
    parallel_ranks = {int(row["node_id"]): float(row["rank"]) for row in read_csv(folder / "ranks.csv")}
    assert parallel_ranks.keys() == serial_ranks.keys(), "Serial/MPI node IDs differ"
    errors = [abs(rank - parallel_ranks[node]) for node, rank in serial_ranks.items()]
    l1_error, max_error = math.fsum(errors), max(errors)
    assert l1_error <= RANK_L1_TOLERANCE, f"Serial/MPI rank error too large: {l1_error:.3e}"
    speedup = baseline["solve_median_s"] / summary["solve_median_s"]
    return {"dataset": name, "processes": summary["processes"],
            "serial_s": baseline["solve_median_s"], "mpi_s": summary["solve_median_s"],
            "speedup": speedup, "efficiency": speedup / summary["processes"],
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
            checks.extend({"dataset": name, "processes": t, "passed": False,
                        "error": f"Serial reference: {error}"} for t in PROCESS_COUNTS)
            print(f"FAIL: {name} serial reference: {error}", flush=True)
            continue
        for processes in PROCESS_COUNTS:
            folder = RESULTS / name / f"p{processes}"
            print(f"Checking {name}/p{processes}...", flush=True)
            try:
                check = validate(name, edge_path, node_path, folder)
                comparison = compare(name, folder, processes, baseline, serial_ranks)
                check.update(comparison)
                scaling.append(comparison)
                print(f"PASS: L1 error={comparison['rank_l1_error']:.3e}, speedup={comparison['speedup']:.2f}", flush=True)
            except (AssertionError, OSError, ValueError, KeyError) as error:
                check = {"dataset": name, "processes": processes, "passed": False, "error": str(error)}
                print(f"FAIL: {name}/p{processes}: {error}", flush=True)
            checks.append(check)
    passed = sum(check["passed"] for check in checks)
    report = {"passed": passed, "failed": len(checks) - passed,
            "method": "Independent residual checks and full rank comparison with validated serial output",
            "rank_l1_tolerance": RANK_L1_TOLERANCE, "checks": checks}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with (RESULTS / "scaling.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["dataset", "processes", "serial_s", "mpi_s",
                                                "speedup", "efficiency", "rank_l1_error", "rank_max_error"])
        writer.writeheader()
        writer.writerows(scaling)
    print(f"Validation and scaling results: {RESULTS}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

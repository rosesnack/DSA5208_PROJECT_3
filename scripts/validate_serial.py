"""Check saved experiment results against the three original graphs."""
import csv
import json
import math
import os
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = Path(os.environ.get("PAGERANK_RESULTS_ROOT", "results"))
if not RESULTS_ROOT.is_absolute():
    RESULTS_ROOT = ROOT / RESULTS_ROOT
RESULTS = RESULTS_ROOT / "serial"
def load_datasets():
    manifest_name = os.environ.get("PAGERANK_DATASET_MANIFEST")
    if not manifest_name:
        return {
            "google": (ROOT / "data/raw/web-Google.txt", None),
            "uniform": (ROOT / "data/synthetic/uniform.edges", ROOT / "data/synthetic/uniform.nodes"),
            "hub": (ROOT / "data/synthetic/hub.edges", ROOT / "data/synthetic/hub.nodes"),
        }
    manifest_path = Path(manifest_name)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    datasets = {}
    with manifest_path.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            name, edge_name, node_name = line.split()
            edge_path = Path(edge_name)
            node_path = None if node_name == "-" else Path(node_name)
            datasets[name] = (edge_path if edge_path.is_absolute() else ROOT / edge_path,
                              None if node_path is None else
                              node_path if node_path.is_absolute() else ROOT / node_path)
    return datasets


DATASETS = load_datasets()
MASS_TOLERANCE = 1e-10
ROUNDING_TOLERANCE = 1e-12


def data_lines(path):
    # Stream large files instead of loading all edges into memory.
    with path.open(encoding="utf-8-sig") as source:
        for line in source:
            text = line.split("#", 1)[0].strip()
            if text:
                yield text


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as source:
        yield from csv.DictReader(source)


def validate(name, edge_path, node_path, folder):
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    assert summary["dataset"] == name, "Wrong dataset label"
    ids, ranks, in_degree, out_degree = [], [], [], []
    for row in read_csv(folder / "ranks.csv"):
        ids.append(int(row["node_id"]))
        ranks.append(float(row["rank"]))
        in_degree.append(int(row["in_degree"]))
        out_degree.append(int(row["out_degree"]))
    n = len(ids)
    assert n == summary["nodes"] and n > 0, "Wrong node count"
    position = {node: i for i, node in enumerate(ids)}
    assert len(position) == n, "Duplicate node IDs"
    assert all(math.isfinite(r) and r >= 0 for r in ranks), "Invalid rank values"
    rank_sum = math.fsum(ranks)
    assert abs(rank_sum - 1) <= MASS_TOLERANCE, "Ranks do not sum to 1"
    assert all(d >= 0 for d in in_degree + out_degree), "Negative degree"
    if node_path is not None:
        assert set(map(int, data_lines(node_path))) == set(ids), "Node IDs differ from the node file"

    # These three datasets have unique directed edges. Check every saved degree
    # against the raw file, and push rank along each edge independently of C++ CSR.
    contributions = [r / degree if degree else 0.0 for r, degree in zip(ranks, out_degree)]
    incoming = [0.0] * n
    actual_in, actual_out = [0] * n, [0] * n
    edge_count = 0
    for line in data_lines(edge_path):
        source, destination = map(int, line.split())
        u, v = position[source], position[destination]
        actual_out[u] += 1
        actual_in[v] += 1
        incoming[v] += contributions[u]
        edge_count += 1
    assert edge_count == summary["edges"], "Wrong edge count"
    assert actual_in == in_degree and actual_out == out_degree, "Degrees differ from the original graph"
    if node_path is None:
        assert all(a or b for a, b in zip(actual_in, actual_out)), "Extra IDs not present in the edge file"

    alpha, tolerance = summary["alpha"], summary["tolerance_l1"]
    assert 0 <= alpha < 1 and tolerance > 0, "Invalid PageRank settings"
    dangling = math.fsum(r for r, degree in zip(ranks, actual_out) if degree == 0)
    base = ((1 - alpha) + alpha * dangling) / n
    residual = math.fsum(abs(base + alpha * value - rank) for value, rank in zip(incoming, ranks))
    assert residual <= tolerance + ROUNDING_TOLERANCE, f"Independent residual too large: {residual:.3e}"

    # Check the last run's convergence history and the configured iteration limit.
    history = list(read_csv(folder / "history.csv"))
    iterations = summary["iterations"]
    assert len(history) == iterations and iterations > 0, "Wrong history length"
    assert [int(row["iteration"]) for row in history] == list(range(1, iterations + 1)), "Wrong history iteration IDs"
    deltas = [float(row["delta_l1"]) for row in history]
    assert all(math.isfinite(delta) and delta >= 0 for delta in deltas), "Invalid history values"
    assert deltas[-1] <= tolerance and summary["converged"], "Run did not converge"
    if summary["fixed_iterations"]:
        assert iterations == summary["fixed_iterations"], "Wrong fixed iteration count"
    else:
        assert iterations <= summary["max_iterations"], "Iteration limit exceeded"
        assert all(delta > tolerance for delta in deltas[:-1]), "Iterations continued after convergence"

    # Recompute the summary from individual measurements, not from C++ statistics.
    timings = list(read_csv(folder / "timings.csv"))
    assert len(timings) == summary["repeat_runs"] and timings, "Wrong repeat count"
    assert [int(row["run"]) for row in timings] == list(range(1, len(timings) + 1)), "Wrong run IDs"
    assert all(row["converged"] == "true" for row in timings), "A repeat did not converge"
    assert all(int(row["iterations"]) == iterations for row in timings), "Repeat iteration counts differ"
    times = [float(row["solve_s"]) for row in timings]
    residuals = [float(row["residual_l1"]) for row in timings]
    sums = [float(row["rank_sum"]) for row in timings]
    assert all(math.isfinite(t) and t > 0 for t in times), "Invalid solve time"
    assert all(0 <= r <= tolerance + ROUNDING_TOLERANCE for r in residuals), "Invalid reported residual"
    assert all(abs(s - 1) <= MASS_TOLERANCE for s in sums), "Invalid reported rank sum"
    assert all(math.isclose(r, residuals[-1], rel_tol=1e-6, abs_tol=ROUNDING_TOLERANCE) for r in residuals), "Repeat residuals differ"
    assert math.isclose(residual, residuals[-1], rel_tol=1e-6, abs_tol=ROUNDING_TOLERANCE), "Independent residual differs from C++"
    assert abs(rank_sum - sums[-1]) <= MASS_TOLERANCE, "Saved ranks differ from the reported sum"
    expected = {
        "solve_median_s": statistics.median(times),
        "solve_min_s": min(times),
        "solve_max_s": max(times),
        "max_residual_l1": max(residuals),
        "max_rank_sum_error": max(abs(s - 1) for s in sums),
    }
    for key, value in expected.items():
        assert math.isclose(summary[key], value, rel_tol=1e-12, abs_tol=1e-15), f"Wrong summary field: {key}"
    return {"dataset": name, "passed": True, "nodes": n, "edges": edge_count,
            "iterations": iterations, "independent_residual_l1": residual,
            "rank_sum_error": abs(rank_sum - 1)}


def main():
    checks = []
    for name, (edge_path, node_path) in DATASETS.items():
        print(f"Checking {name}...", flush=True)
        try:
            check = validate(name, edge_path, node_path, RESULTS / name)
            print(f"PASS: {name}, residual={check['independent_residual_l1']:.3e}", flush=True)
        except (AssertionError, OSError, ValueError, KeyError) as error:
            check = {"dataset": name, "passed": False, "error": str(error)}
            print(f"FAIL: {name}: {error}", flush=True)
        checks.append(check)
    passed = sum(check["passed"] for check in checks)
    report = {"passed": passed, "failed": len(checks) - passed,
            "method": "Saved-output checks and an independent PageRank update over the original edges",
            "mass_tolerance": MASS_TOLERANCE, "rounding_tolerance": ROUNDING_TOLERANCE,
            "checks": checks}
    RESULTS.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS / "validation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {report_path}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

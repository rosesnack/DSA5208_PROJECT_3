"""Summarize the validated MPI+Kokkos OpenMP grid and plot selected fixed graphs."""
import argparse
import csv
import json
from pathlib import Path

from audit_fixed_matrix import graph_names


def summary(root, graph, nodes, processes, threads, communication):
    suffix = "_halo" if communication == "halo" else ""
    if nodes == 8 and processes == 512 and threads == 1:
        job = root / "strong" / graph / "nodes8_p512"
        result = job / f"mpi_kokkos{suffix}" / "OpenMP" / graph / "p512"
    elif nodes == 8 and processes == 128 and threads == 4:
        job = root / "kokkos_cpu_512" / graph
        result = job / f"mpi_kokkos{suffix}" / "OpenMP" / graph / "p128_t4"
    elif threads == 1:
        job = root / "strong" / graph / f"nodes{nodes}"
        result = job / f"mpi_kokkos{suffix}" / "OpenMP" / graph / f"p{processes}"
    else:
        job = root / "kokkos_cpu_grid" / graph / f"nodes{nodes}"
        result = job / f"mpi_kokkos{suffix}" / "OpenMP" / graph / f"p{processes}_t{threads}"
    if not (job / "complete.txt").is_file():
        return None
    path = result / "summary.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--graphs", nargs="+", default=("google", "uniform", "hub"))
    parser.add_argument("--csv-only", action="store_true")
    args = parser.parse_args()
    rows = []
    for graph in graph_names():
        for communication in ("allgather", "halo"):
            for nodes in (1, 2, 4, 8):
                for ranks_per_node in (1, 2, 4, 8, 16, 32):
                    processes = nodes * ranks_per_node
                    for threads in (1, 2, 4, 8, 16, 32):
                        if ranks_per_node * threads > 32:
                            continue
                        result = summary(args.results_root, graph, nodes, processes, threads,
                                         communication)
                        if result is None:
                            continue
                        rows.append({"graph": graph, "communication": communication,
                                     "nodes": nodes, "ranks_per_node": ranks_per_node,
                                     "processes": processes, "threads": threads,
                                     "cores": processes * threads,
                                     "solve_median_s": result["solve_median_s"],
                                     "communication_median_s": result["communication_median_s"]})
            for processes, threads in ((512, 1), (128, 4)):
                result = summary(args.results_root, graph, 8, processes, threads, communication)
                if result is not None:
                    rows.append({"graph": graph, "communication": communication,
                                 "nodes": 8, "ranks_per_node": processes // 8,
                                 "processes": processes, "threads": threads, "cores": 512,
                                 "solve_median_s": result["solve_median_s"],
                                 "communication_median_s": result["communication_median_s"]})
    baselines = {(row["graph"], row["communication"], row["threads"]): row["solve_median_s"]
                 for row in rows if row["nodes"] == 1 and row["processes"] == 1}
    for row in rows:
        baseline = baselines.get((row["graph"], row["communication"], row["threads"]))
        row["strong_speedup"] = baseline / row["solve_median_s"] if baseline else ""
        row["strong_efficiency"] = (row["strong_speedup"] / row["processes"]
                                    if baseline else "")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "kokkos_cpu_grid.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=("graph", "communication", "nodes",
                             "ranks_per_node", "processes", "threads", "cores", "solve_median_s",
                             "communication_median_s", "strong_speedup", "strong_efficiency"))
        writer.writeheader()
        writer.writerows(rows)

    if args.csv_only:
        print(f"Saved {len(rows)} validated MPI+Kokkos OpenMP cells")
        return

    import matplotlib.pyplot as plt

    for graph in args.graphs:
        for communication in ("allgather", "halo"):
            fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
            for nodes in (1, 2, 4, 8):
                for threads in (1, 4):
                    group = sorted((row for row in rows if row["graph"] == graph and
                                    row["communication"] == communication and
                                    row["nodes"] == nodes and row["threads"] == threads),
                                   key=lambda row: row["cores"])
                    if not group:
                        continue
                    label = f"{nodes} nodes, T={threads}"
                    axes[0].plot([row["cores"] for row in group],
                                 [row["solve_median_s"] for row in group], marker="o", label=label)
                    efficient = [row for row in group if row["strong_efficiency"] != ""]
                    axes[1].plot([row["cores"] for row in efficient],
                                 [row["strong_efficiency"] for row in efficient], marker="o", label=label)
            for axis in axes:
                axis.set_xscale("log", base=2)
                axis.set_xlabel("CPU cores = MPI ranks × threads/rank")
                axis.grid(True, alpha=0.25)
            axes[0].set_yscale("log")
            axes[0].set_ylabel("Median solve time (s)")
            axes[1].set_ylabel("Same-method strong-scaling efficiency")
            axes[1].legend(bbox_to_anchor=(1.05, 1), loc="upper left")
            fig.suptitle(f"MPI+Kokkos OpenMP: {graph}, {communication}")
            fig.tight_layout()
            fig.savefig(args.output_dir / f"kokkos_cpu_{graph}_{communication}.png", dpi=180,
                        bbox_inches="tight")
            plt.close(fig)
    print(f"Saved {len(rows)} validated MPI+Kokkos OpenMP cells")


if __name__ == "__main__":
    main()

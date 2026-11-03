"""Summarize one-hardware Cloud GPU strong-scaling results for all 45 graphs."""
import argparse
import csv
from pathlib import Path


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--graphs", nargs="+", default=("google", "uniform", "hub"))
    parser.add_argument("--csv-only", action="store_true")
    args = parser.parse_args()
    root = args.results_root
    if not (root / "complete.txt").is_file():
        raise SystemExit("Cloud matrix has no complete.txt marker")
    rows = []
    methods = (("MPI CPU control", "mpi", "", "mpi_s", (1,)),
               ("MPI+OpenMP CPU control", "hybrid", "", "hybrid_s", (1, 2, 4, 8)),
               ("MPI+CUDA", "mpi_cuda", "Cuda", "parallel_s", (1,)),
               ("MPI+Kokkos CUDA", "mpi_kokkos", "Cuda", "parallel_s", (1,)))
    for label, method, backend, time_key, threads_allowed in methods:
        for communication in ("allgather", "halo"):
            folder = method + ("_halo" if communication == "halo" else "")
            path = root / folder / backend / "scaling.csv"
            for result in read_rows(path):
                threads = int(result["requested_threads"]) if method == "hybrid" else 1
                if threads not in threads_allowed:
                    continue
                rows.append({"graph": result["dataset"], "method": label,
                             "communication": communication, "nodes": int(result["processes"]),
                             "processes": int(result["processes"]), "threads": threads,
                             "gpu_count": int(result["processes"]) if method in ("mpi_cuda", "mpi_kokkos") else 0,
                             "solve_median_s": float(result[time_key])})
    baselines = {(row["graph"], row["method"], row["communication"], row["threads"]):
                 row["solve_median_s"] for row in rows if row["processes"] == 1}
    for row in rows:
        key = (row["graph"], row["method"], row["communication"], row["threads"])
        baseline = baselines[key]
        row["strong_speedup"] = baseline / row["solve_median_s"]
        row["strong_efficiency"] = row["strong_speedup"] / row["processes"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "cloud_gpu_scaling.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=("graph", "method", "communication", "nodes",
                                "processes", "threads", "gpu_count", "solve_median_s",
                                "strong_speedup", "strong_efficiency"))
        writer.writeheader()
        writer.writerows(rows)
    if args.csv_only:
        print(f"Saved {len(rows)} validated Cloud scaling cells")
        return

    import matplotlib.pyplot as plt

    for graph in args.graphs:
        fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
        for method in ("MPI CPU control", "MPI+OpenMP CPU control", "MPI+CUDA", "MPI+Kokkos CUDA"):
            for communication in ("allgather", "halo"):
                subset = sorted((row for row in rows if row["graph"] == graph and
                                 row["method"] == method and row["communication"] == communication and
                                 row["threads"] == 1), key=lambda row: row["processes"])
                if not subset:
                    continue
                label = f"{method} {communication}"
                x = [row["processes"] for row in subset]
                for axis, key in zip(axes, ("solve_median_s", "strong_speedup", "strong_efficiency")):
                    axis.plot(x, [row[key] for row in subset], marker="o", label=label)
        for axis in axes:
            axis.set_xscale("log", base=2)
            axis.set_xlabel("GPU nodes = MPI ranks (GPU methods: one GPU/rank)")
            axis.grid(True, alpha=0.25)
        axes[0].set_yscale("log")
        axes[0].set_ylabel("Median solve time (s)")
        axes[1].set_ylabel("Speedup vs same method at p=1")
        axes[2].set_ylabel("Same-method strong efficiency")
        axes[1].legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        fig.suptitle(f"Cloud matched-node PageRank: {graph}")
        fig.tight_layout()
        fig.savefig(args.output_dir / f"cloud_gpu_scaling_{graph}.png", dpi=180,
                    bbox_inches="tight")
        plt.close(fig)
    print(f"Saved {len(rows)} validated Cloud scaling cells")


if __name__ == "__main__":
    main()

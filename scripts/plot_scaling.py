"""Plot fixed-graph serial, strong/weak MPI, hybrid, and GPU result matrices."""
import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def read_gpu_scaling_rows(path):
    rows = read_rows(path)
    extension = path.with_name("scaling_p4_p8.csv")
    if extension.is_file():
        rows.extend(read_rows(extension))
    return rows


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("results_root", type=Path)
parser.add_argument("output_dir", type=Path)
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=True)

serial = []
for path in sorted((args.results_root / "serial_grid").glob("*/serial_scaling.csv")):
    serial.extend(read_rows(path))
for family in sorted({row["family"] for row in serial}):
    fig, ax = plt.subplots()
    for degree in sorted({float(row["average_degree"]) for row in serial}):
        group = sorted((row for row in serial if row["family"] == family and
                        float(row["average_degree"]) == degree), key=lambda row: int(row["vertices"]))
        ax.plot([int(row["edges"]) for row in group], [float(row["median_s"]) for row in group],
                marker="o", label=f"average out-degree {degree:g}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Directed edges")
    ax.set_ylabel("Serial solve time (s)")
    ax.set_title(f"Serial PageRank size grid: {family}")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output_dir / f"serial_size_scaling_{family}.png", dpi=180)
    plt.close(fig)

for communication, relative, label in (("allgather", "mpi/scaling.csv", "Allgatherv"),
                                         ("halo", "mpi_halo/scaling.csv", "Halo")):
    rows = []
    for path in sorted((args.results_root / "strong").glob(f"*/nodes*/{relative}")):
        node_count = int(path.parents[1].name.removeprefix("nodes").split("_")[0])
        rows.extend({**row, "node_count": node_count} for row in read_rows(path))
    for dataset in sorted({row["dataset"] for row in rows}):
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
        for node_count in sorted({row["node_count"] for row in rows}):
            group = sorted((row for row in rows if row["dataset"] == dataset and
                            row["node_count"] == node_count), key=lambda row: int(row["processes"]))
            processes = [int(row["processes"]) for row in group]
            for axis, key in zip(axes, ("mpi_s", "speedup", "efficiency")):
                axis.plot(processes, [float(row[key]) for row in group], marker="o", label=f"{node_count} nodes")
        for axis, ylabel, title, log_y in zip(axes,
                                              ("Solve time (s)", "Speedup vs serial", "Parallel efficiency"),
                                              ("runtime", "speedup", "efficiency"),
                                              (True, True, False)):
            axis.set_xscale("log", base=2)
            if log_y:
                axis.set_yscale("log")
            axis.set_xlabel("MPI ranks")
            axis.set_ylabel(ylabel)
            axis.set_title(f"{label} {title}")
            axis.grid(True, which="both", alpha=0.25)
            axis.legend()
        fig.suptitle(f"Strong scaling: {dataset}")
        fig.tight_layout()
        fig.savefig(args.output_dir / f"strong_{communication}_{dataset}.png", dpi=180)
        plt.close(fig)

weak = read_rows(args.results_root / "weak" / "weak_scaling.csv")
for family in ("uniform", "hub", "controlled"):
    extension = (args.results_root / "weak_512" / family /
                 f"weak_mpi_cpu_t1_extension_p512_{family}" / "scaling.csv")
    if extension.exists():
        weak.extend(read_rows(extension))
for family in sorted({row["family"] for row in weak}):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for communication in ("allgather", "halo"):
        group = sorted((row for row in weak if row["family"] == family and
                        row["communication"] == communication), key=lambda row: int(row["processes"]))
        label = "Allgatherv" if communication == "allgather" else "Halo"
        processes = [int(row["processes"]) for row in group]
        axes[0].plot(processes, [float(row["median_s"]) for row in group], marker="o", label=label)
        axes[1].plot(processes, [float(row["iteration_efficiency"]) for row in group], marker="o", label=label)
    axes[0].set_xscale("log", base=2)
    axes[0].set_yscale("log")
    axes[0].set_xlabel("MPI ranks")
    axes[0].set_ylabel("Solve time (s)")
    axes[0].set_title(f"Weak scaling runtime: {family}")
    axes[1].set_xscale("log", base=2)
    axes[1].set_xlabel("MPI ranks")
    axes[1].set_ylabel("Per-iteration weak efficiency")
    axes[1].set_title(f"Weak scaling efficiency: {family}")
    for axis in axes:
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
    fig.tight_layout()
    fig.savefig(args.output_dir / f"weak_{family}.png", dpi=180)
    plt.close(fig)

for hardware, sources in (
    ("cpu", (("MPI", args.results_root / "weak" / "weak_scaling.csv"),
             ("MPI+OpenMP T=4", args.results_root / "weak" / "weak_hybrid_scaling.csv"),
             ("MPI+Kokkos OpenMP", args.results_root / "weak" /
              "weak_mpi_kokkos_OpenMP_t1" / "scaling.csv"))),
    ("gpu", (("MPI", args.results_root / "gpu_weak" / "weak_mpi_cpu_t1" / "scaling.csv"),
             *((f"MPI+OpenMP T={threads}", args.results_root / "gpu_weak" /
                f"weak_hybrid_cpu_t{threads}" / "scaling.csv") for threads in (1, 2, 4, 8)),
             ("MPI+CUDA", args.results_root / "gpu_weak" /
              "weak_mpi_cuda_Cuda_t1" / "scaling.csv"),
             ("MPI+Kokkos CUDA", args.results_root / "gpu_weak" /
              "weak_mpi_kokkos_Cuda_t1" / "scaling.csv")))):
    for family in ("uniform", "hub", "controlled"):
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
        for method, path in sources:
            rows = read_gpu_scaling_rows(path) if hardware == "gpu" else read_rows(path)
            if hardware == "cpu":
                family_root = args.results_root / "weak_512" / family
                extra = {
                    "MPI": family_root / f"weak_mpi_cpu_t1_extension_p512_{family}" / "scaling.csv",
                    "MPI+OpenMP T=4": family_root /
                    f"weak_hybrid_cpu_t4_extension_p128_{family}" / "scaling.csv",
                    "MPI+Kokkos OpenMP": family_root /
                    f"weak_mpi_kokkos_OpenMP_t1_extension_p512_{family}" / "scaling.csv",
                }[method]
                if extra.exists():
                    rows.extend(read_rows(extra))
            for communication in ("allgather", "halo"):
                group = sorted((row for row in rows if row["family"] == family and
                                row["communication"] == communication),
                               key=lambda row: int(row["processes"]))
                x = [int(row["processes"]) for row in group]
                axes[0].plot(x, [float(row["seconds_per_iteration"]) for row in group],
                             marker="o", label=f"{method} {communication}")
                axes[1].plot(x, [float(row["iteration_efficiency"]) for row in group],
                             marker="o", label=f"{method} {communication}")
        for axis in axes:
            axis.set_xscale("log", base=2)
            axis.set_xlabel("MPI ranks")
            axis.grid(True, which="both", alpha=0.25)
        axes[0].set_yscale("log")
        axes[0].set_ylabel("Time per iteration (s)")
        axes[1].set_ylabel("Per-iteration weak efficiency")
        axes[1].legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        fig.suptitle(f"Weak scaling: {family} on {hardware} nodes")
        fig.tight_layout()
        fig.savefig(args.output_dir / f"weak_all_methods_{hardware}_{family}.png", dpi=180,
                    bbox_inches="tight")
        plt.close(fig)

for communication, folder in (("allgather", "hybrid"), ("halo", "hybrid_halo")):
    hybrid = []
    for path in sorted((args.results_root / "strong").glob(f"*/nodes*/{folder}/scaling.csv")):
        node_count = int(path.parents[1].name.removeprefix("nodes").split("_")[0])
        hybrid.extend({**row, "node_count": node_count} for row in read_rows(path))
    for dataset in sorted({row["dataset"] for row in hybrid}):
        dataset_rows = [row for row in hybrid if row["dataset"] == dataset]
        for node_count in sorted({int(row["node_count"]) for row in dataset_rows}):
            group = sorted((row for row in dataset_rows if int(row["node_count"]) == node_count),
                           key=lambda row: (int(row["processes"]), int(row["requested_threads"])))
            fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
            for threads in sorted({int(row["requested_threads"]) for row in group}):
                subset = [row for row in group if int(row["requested_threads"]) == threads]
                total = [int(row["processes"]) * threads for row in subset]
                legend = f"{threads} threads/rank"
                axes[0].plot(total, [float(row["hybrid_s"]) for row in subset], marker="o", label=legend)
                axes[1].plot(total, [float(row["speedup"]) for row in subset], marker="o", label=legend)
            axes[0].set_yscale("log")
            axes[1].set_yscale("log")
            for axis in axes:
                axis.set_xscale("log", base=2)
                axis.set_xlabel("MPI ranks × OpenMP threads")
                axis.grid(True, which="both", alpha=0.25)
                axis.legend()
            axes[0].set_ylabel("Solve time (s)")
            axes[0].set_title("MPI + OpenMP runtime")
            axes[1].set_ylabel("Speedup vs serial")
            axes[1].set_title("MPI + OpenMP speedup")
            fig.suptitle(f"Hybrid {communication}: {dataset}, {node_count} nodes")
            fig.tight_layout()
            fig.savefig(args.output_dir / f"hybrid_{communication}_{dataset}_nodes{node_count}.png", dpi=180)
            plt.close(fig)

kokkos_openmp = []
for threads in (1, 2, 4, 8, 16, 32):
    for path in sorted((args.results_root / "serial_grid").glob(
            f"*/kokkos_threads_{threads}/kokkos/OpenMP/scaling.csv")):
        kokkos_openmp.extend({**row, "requested_threads": threads} for row in read_rows(path))
for dataset in sorted({row["dataset"] for row in kokkos_openmp}):
    group = sorted((row for row in kokkos_openmp if row["dataset"] == dataset),
                   key=lambda row: int(row["requested_threads"]))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    threads = [int(row["requested_threads"]) for row in group]
    axes[0].plot(threads, [float(row["parallel_s"]) for row in group], marker="o")
    axes[1].plot(threads, [float(row["speedup"]) for row in group], marker="o")
    axes[0].set_yscale("log")
    for axis in axes:
        axis.set_xscale("log", base=2)
        axis.set_xlabel("Kokkos OpenMP threads")
        axis.grid(True, which="both", alpha=0.25)
    axes[0].set_ylabel("Solve time (s)")
    axes[0].set_title("Kokkos OpenMP runtime")
    axes[1].set_ylabel("Speedup vs serial")
    axes[1].set_title("Kokkos OpenMP speedup")
    fig.suptitle(f"Kokkos OpenMP scaling: {dataset}")
    fig.tight_layout()
    fig.savefig(args.output_dir / f"kokkos_openmp_{dataset}.png", dpi=180)
    plt.close(fig)

gpu = []
for pattern in ("*/cuda/scaling.csv", "*/kokkos/Cuda/scaling.csv"):
    for path in sorted((args.results_root / "gpu").glob(pattern)):
        gpu.extend(read_rows(path))
datasets = sorted({row["dataset"] for row in gpu})
fig, ax = plt.subplots(figsize=(max(10, len(datasets) * 0.7), 5))
width = 0.25
positions = list(range(len(datasets)))
for offset, implementation in enumerate(sorted({row["implementation"] for row in gpu})):
    values = {row["dataset"]: float(row["parallel_s"]) for row in gpu if row["implementation"] == implementation}
    ax.bar([position + (offset - 0.5) * width for position in positions],
           [values[dataset] for dataset in datasets], width=width, label=implementation)
ax.set_xticks(positions, datasets, rotation=70, ha="right")
ax.set_yscale("log")
ax.set_ylabel("GPU solve time (s)")
ax.set_title("Native CUDA and Kokkos-CUDA across the fixed graph set")
ax.grid(True, axis="y", which="both", alpha=0.25)
ax.legend()
fig.tight_layout()
fig.savefig(args.output_dir / "gpu_all_fixed_graphs.png", dpi=180)
plt.close(fig)

for graph_root in sorted((args.results_root / "gpu").iterdir()):
    if not graph_root.is_dir():
        continue
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for method, backend, label in (("mpi", "", "MPI"),
                                   ("hybrid", "", "MPI+OpenMP T=1"),
                                   ("mpi_cuda", "Cuda", "MPI+CUDA"),
                                   ("mpi_kokkos", "Cuda", "MPI+Kokkos CUDA")):
        for communication in ("allgather", "halo"):
            folder = method + ("_halo" if communication == "halo" else "")
            path = graph_root / folder / backend / "scaling.csv"
            rows = sorted(read_gpu_scaling_rows(path), key=lambda row: int(row["processes"]))
            if method == "hybrid":
                rows = [row for row in rows if int(row["requested_threads"]) == 1]
            x = [int(row["processes"]) for row in rows]
            y = [float(row["parallel_s"] if "parallel_s" in row else
                       row["hybrid_s"] if "hybrid_s" in row else row["mpi_s"]) for row in rows]
            axes[0].plot(x, y, marker="o", label=f"{label} {communication}")
            axes[1].plot(x, [y[0] / value for value in y], marker="o",
                         label=f"{label} {communication}")
            axes[2].plot(x, [y[0] / (processes * value) for processes, value in zip(x, y)],
                         marker="o", label=f"{label} {communication}")
    for axis in axes:
        axis.set_xscale("log", base=2)
        axis.grid(True, which="both", alpha=0.25)
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Nodes = MPI ranks = GPUs")
    axes[0].set_ylabel("Solve time (s)")
    axes[1].set_xlabel("Nodes = MPI ranks = GPUs")
    axes[1].set_ylabel("Speedup vs same method at p=1")
    axes[2].set_xlabel("Nodes = MPI ranks = GPUs")
    axes[2].set_ylabel("Strong scaling efficiency")
    axes[1].legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    fig.suptitle(f"Matched MPI and GPU layout: {graph_root.name}")
    fig.tight_layout()
    fig.savefig(args.output_dir / f"mpi_gpu_matched_{graph_root.name}.png", dpi=180,
                bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for communication in ("allgather", "halo"):
        folder = "hybrid_halo" if communication == "halo" else "hybrid"
        rows = read_gpu_scaling_rows(graph_root / folder / "scaling.csv")
        for threads in (1, 2, 4, 8):
            group = sorted((row for row in rows if int(row["requested_threads"]) == threads),
                           key=lambda row: int(row["processes"]))
            x = [int(row["processes"]) for row in group]
            y = [float(row["hybrid_s"]) for row in group]
            label = f"T={threads} {communication}"
            axes[0].plot(x, y, marker="o", label=label)
            axes[1].plot(x, [y[0] / (processes * value) for processes, value in zip(x, y)],
                         marker="o", label=label)
    for axis in axes:
        axis.set_xscale("log", base=2)
        axis.set_xlabel("Nodes = MPI ranks")
        axis.grid(True, which="both", alpha=0.25)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Solve time (s)")
    axes[1].set_ylabel("Strong scaling efficiency at fixed T")
    axes[1].legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    fig.suptitle(f"MPI+OpenMP on GPU nodes: {graph_root.name}")
    fig.tight_layout()
    fig.savefig(args.output_dir / f"hybrid_gpu_nodes_{graph_root.name}.png", dpi=180,
                bbox_inches="tight")
    plt.close(fig)

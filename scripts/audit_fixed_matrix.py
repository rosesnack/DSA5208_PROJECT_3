"""Check every planned fixed-graph result cell against saved summaries and job markers."""
import argparse
import csv
from collections import Counter
from pathlib import Path

from generate_scaling_graphs import FAMILIES, SERIAL_AVERAGE_DEGREES, SERIAL_VERTICES


def graph_names():
    names = ["google", "uniform", "hub"]
    for family in FAMILIES:
        names.append(f"synthetic_{family}")
        for vertices in SERIAL_VERTICES:
            for degree in SERIAL_AVERAGE_DEGREES:
                names.append(f"grid_{family}_n{vertices}_d{degree}")
    names.extend(f"strong_{family}" for family in FAMILIES)
    return names


def cell(stage, graph, layout, summary, marker):
    return {"stage": stage, "graph": graph, "layout": layout,
            "summary": summary, "marker": marker}


def vanda_cells(root, include_gpu_extension=False):
    for graph in graph_names():
        serial = root / "serial_grid" / graph
        serial_marker = serial / "complete.txt"
        yield cell("serial", graph, "1 CPU core", serial / "serial" / graph / "summary.json", serial_marker)
        for threads in (1, 2, 4, 8, 16, 32):
            yield cell("openmp", graph, f"T={threads}",
                       serial / "openmp" / graph / f"t{threads}" / "summary.json", serial_marker)
            yield cell("kokkos_openmp", graph, f"T={threads}",
                       serial / f"kokkos_threads_{threads}" / "kokkos" / "OpenMP" / graph / "summary.json",
                       serial_marker)
        for nodes in (1, 2, 4, 8):
            strong = root / "strong" / graph / f"nodes{nodes}"
            grid = root / "kokkos_cpu_grid" / graph / f"nodes{nodes}"
            for ranks_per_node in (1, 2, 4, 8, 16, 32):
                processes = nodes * ranks_per_node
                for communication in ("allgather", "halo"):
                    suffix = "_halo" if communication == "halo" else ""
                    layout = f"n={nodes},r={ranks_per_node},p={processes},{communication}"
                    yield cell("mpi_cpu", graph, layout,
                               strong / f"mpi{suffix}" / graph / f"p{processes}" / "summary.json",
                               strong / "complete.txt")
                    yield cell("mpi_kokkos_cpu_t1", graph, layout,
                               strong / f"mpi_kokkos{suffix}" / "OpenMP" / graph /
                               f"p{processes}" / "summary.json", strong / "complete.txt")
                    for threads in (1, 2, 4, 8, 16, 32):
                        if ranks_per_node * threads > 32:
                            continue
                        threaded_layout = f"{layout},T={threads}"
                        yield cell("mpi_openmp", graph, threaded_layout,
                                   strong / f"hybrid{suffix}" / graph /
                                   f"p{processes}_t{threads}" / "summary.json", strong / "complete.txt")
                        if threads > 1:
                            yield cell("mpi_kokkos_cpu_threads", graph, threaded_layout,
                                       grid / f"mpi_kokkos{suffix}" / "OpenMP" / graph /
                                       f"p{processes}_t{threads}" / "summary.json", grid / "complete.txt")
        strong_512 = root / "strong" / graph / "nodes8_p512"
        kokkos_512 = root / "kokkos_cpu_512" / graph
        for communication in ("allgather", "halo"):
            suffix = "_halo" if communication == "halo" else ""
            marker = strong_512 / "complete.txt"
            yield cell("mpi_cpu_512", graph, communication,
                       strong_512 / f"mpi{suffix}" / graph / "p512" / "summary.json", marker)
            yield cell("mpi_kokkos_cpu_512_t1", graph, communication,
                       strong_512 / f"mpi_kokkos{suffix}" / "OpenMP" / graph / "p512" /
                       "summary.json", marker)
            for processes, threads in ((512, 1), (128, 4)):
                yield cell("mpi_openmp_512", graph, f"p={processes},T={threads},{communication}",
                           strong_512 / f"hybrid{suffix}" / graph /
                           f"p{processes}_t{threads}" / "summary.json", marker)
            yield cell("mpi_kokkos_cpu_512_t4", graph, communication,
                       kokkos_512 / f"mpi_kokkos{suffix}" / "OpenMP" / graph /
                       "p128_t4" / "summary.json", kokkos_512 / "complete.txt")
        gpu = root / "gpu" / graph
        gpu_marker = gpu / "complete.txt"
        yield from gpu_cells(gpu, graph, gpu_marker, (1, 2), (1, 2, 4, 8, 16, 32))
        if include_gpu_extension:
            extension_marker = gpu / "complete_p4_p8.txt"
            for item in gpu_cells(gpu, graph, extension_marker, (4, 8), ()):
                if item["stage"] in ("gpu_node_mpi_cpu", "gpu_node_mpi_openmp",
                                     "mpi_cuda", "mpi_kokkos_cuda"):
                    yield item


def gpu_cells(root, graph, marker, processes, openmp_threads):
    yield cell("gpu_node_serial", graph, "p=1", root / "serial" / graph / "summary.json", marker)
    for threads in openmp_threads:
        yield cell("gpu_node_openmp", graph, f"T={threads}",
                   root / "openmp" / graph / f"t{threads}" / "summary.json", marker)
    yield cell("cuda", graph, "1 GPU", root / "cuda" / graph / "summary.json", marker)
    yield cell("kokkos_cuda", graph, "1 GPU", root / "kokkos" / "Cuda" / graph / "summary.json", marker)
    for p in processes:
        for communication in ("allgather", "halo"):
            suffix = "_halo" if communication == "halo" else ""
            layout = f"p={p},{communication}"
            yield cell("gpu_node_mpi_cpu", graph, layout,
                       root / f"mpi{suffix}" / graph / f"p{p}" / "summary.json", marker)
            for threads in (1, 2, 4, 8):
                yield cell("gpu_node_mpi_openmp", graph, f"{layout},T={threads}",
                           root / f"hybrid{suffix}" / graph / f"p{p}_t{threads}" / "summary.json", marker)
            yield cell("mpi_cuda", graph, layout,
                       root / f"mpi_cuda{suffix}" / "Cuda" / graph / f"p{p}" / "summary.json", marker)
            yield cell("mpi_kokkos_cuda", graph, layout,
                       root / f"mpi_kokkos{suffix}" / "Cuda" / graph / f"p{p}" / "summary.json", marker)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", choices=("vanda", "cloud"))
    parser.add_argument("results_root", type=Path)
    parser.add_argument("--include-vanda-gpu-extension", action="store_true")
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    root = args.results_root
    if args.environment == "vanda":
        cells = vanda_cells(root, args.include_vanda_gpu_extension)
    else:
        cells = (cell_item for graph in graph_names()
                 for cell_item in gpu_cells(root, graph, root / "complete.txt", (1, 2, 4, 8),
                                            (1, 2, 4, 8)))
    counts = Counter()
    rows = []
    for item in cells:
        produced = item["summary"].is_file()
        validated = produced and item["marker"].is_file()
        counts[(item["stage"], "expected")] += 1
        counts[(item["stage"], "produced")] += produced
        counts[(item["stage"], "validated")] += validated
        if args.csv:
            rows.append({**item, "summary": str(item["summary"]), "marker": str(item["marker"]),
                         "produced": produced, "validated": validated})
    for stage in sorted({key[0] for key in counts}):
        print(f"{stage:28s} {counts[(stage, 'validated')]:5d}/{counts[(stage, 'expected')]:5d} validated"
              f" ({counts[(stage, 'produced')]} summaries)")
    print(f"Total {sum(value for (stage, kind), value in counts.items() if kind == 'validated')}/"
          f"{sum(value for (stage, kind), value in counts.items() if kind == 'expected')} validated cells")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()

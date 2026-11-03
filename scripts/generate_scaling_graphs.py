"""Build the complete fixed-graph matrix and reproducible weak-scaling families."""
import argparse
import csv
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERIAL_VERTICES = (50_000, 100_000, 200_000, 400_000)
SERIAL_AVERAGE_DEGREES = (4, 8, 16)
PROCESS_COUNTS = (1, 2, 4, 8, 16, 32, 64, 128, 256)
WEAK_VERTICES_PER_RANK = 50_000
WEAK_EDGES_PER_RANK = 800_000
SEED = 5208
FAMILIES = ("uniform", "hub", "controlled")


def mixed(value):
    value = (value + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return value ^ (value >> 31)


def write_graph(folder, name, nodes, edges, seed, family="controlled"):
    folder.mkdir(parents=True, exist_ok=True)
    edge_path, node_path = folder / f"{name}.edges", folder / f"{name}.nodes"
    low_nodes = nodes * 4 // 5
    high_nodes = nodes - low_nodes
    average_degree = edges // nodes
    low_degree = max(1, average_degree // 2)
    high_degree, high_remainder = divmod(edges - low_nodes * low_degree, high_nodes)
    hub_nodes = min(nodes - 1, max(1, nodes // 100, high_degree, average_degree))
    non_hub_nodes = nodes - hub_nodes
    uniform_stride = 2654435761 % nodes
    while math.gcd(uniform_stride, nodes) != 1:
        uniform_stride += 1
    hub_stride = 11400714819323198485 % hub_nodes
    while math.gcd(hub_stride, hub_nodes) != 1:
        hub_stride += 1
    regular_stride = 6364136223846793005 % non_hub_nodes
    while math.gcd(regular_stride, non_hub_nodes) != 1:
        regular_stride += 1

    with node_path.open("w", encoding="ascii", newline="\n") as output:
        for node in range(nodes):
            output.write(f"{node}\n")

    with edge_path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"# Directed synthetic {family} graph; source destination; seed={seed}\n")
        for source in range(nodes):
            permuted = (seed - source) % nodes
            degree = (average_degree if family in ("hub", "uniform") else
                      low_degree if permuted < low_nodes else
                      high_degree + (permuted - low_nodes < high_remainder))
            if family == "uniform":
                start = mixed(source ^ seed) % nodes
                for offset in range(degree):
                    output.write(f"{source} {(start + offset * uniform_stride) % nodes}\n")
                continue
            hub_degree = degree * 4 // 5
            hub_start = mixed(source ^ seed) % hub_nodes
            for offset in range(hub_degree):
                destination = (hub_start + offset * hub_stride) % hub_nodes
                output.write(f"{source} {destination}\n")
            regular_degree = degree - hub_degree
            regular_start = mixed(source ^ (seed << 1)) % non_hub_nodes
            for offset in range(regular_degree):
                logical_destination = hub_nodes + (regular_start + offset * regular_stride) % non_hub_nodes
                output.write(f"{source} {logical_destination}\n")
    return edge_path, node_path


def manifest_line(name, edge_path, node_path):
    return f"{name} {edge_path} {node_path}\n"


def add_row(rows, name, experiment, processes, nodes, edges, degree, family, seed):
    rows.append({"name": name, "experiment": experiment, "family": family,
                 "processes": processes, "vertices": nodes, "edges": edges,
                 "average_out_degree": degree, "seed": seed})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--serial-vertices", nargs="+", type=int, default=SERIAL_VERTICES)
    parser.add_argument("--serial-average-degrees", nargs="+", type=int, default=SERIAL_AVERAGE_DEGREES)
    parser.add_argument("--process-counts", nargs="+", type=int, default=PROCESS_COUNTS)
    parser.add_argument("--weak-vertices-per-rank", type=int, default=WEAK_VERTICES_PER_RANK)
    parser.add_argument("--weak-edges-per-rank", type=int, default=WEAK_EDGES_PER_RANK)
    parser.add_argument("--original-data", type=Path, default=ROOT / "data")
    parser.add_argument("--fixed-only", action="store_true",
                        help="Generate the 42 original/canonical/grid graphs without weak or large inputs")
    args = parser.parse_args()
    root = args.output_root.resolve()
    fixed_dir, weak_dir = root / "fixed_graphs", root / "weak_scaling"
    fixed_dir.mkdir(parents=True, exist_ok=True)
    manifests = root / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    fixed_rows, weak_rows, design_rows = [], [], []

    originals = (("google", args.original_data / "raw/web-Google.txt", None),
                 ("uniform", args.original_data / "synthetic/uniform.edges", args.original_data / "synthetic/uniform.nodes"),
                 ("hub", args.original_data / "synthetic/hub.edges", args.original_data / "synthetic/hub.nodes"))
    for name, edge_source, node_source in originals:
        edge_target = fixed_dir / f"{name}.edges"
        node_target = None if node_source is None else fixed_dir / f"{name}.nodes"
        shutil.copyfile(edge_source, edge_target)
        if node_source is not None:
            shutil.copyfile(node_source, node_target)
        fixed_rows.append(manifest_line(name, edge_target, node_target or "-"))
        design_rows.append({"name": name, "experiment": "all_fixed_graph_methods", "family": "original",
                            "processes": "all", "vertices": "from_source", "edges": "from_source",
                            "average_out_degree": "from_source", "seed": "source data"})

    for family in FAMILIES:
        canonical_name = f"synthetic_{family}"
        edge_path, node_path = write_graph(fixed_dir, canonical_name, 100_000, 1_000_000, SEED, family)
        fixed_rows.append(manifest_line(canonical_name, edge_path, node_path))
        add_row(design_rows, canonical_name, "all_fixed_graph_methods", "all", 100_000,
                1_000_000, 10, family, SEED)
        for nodes in args.serial_vertices:
            for degree in args.serial_average_degrees:
                edges = nodes * degree
                name = f"grid_{family}_n{nodes}_d{degree}"
                edge_path, node_path = write_graph(fixed_dir, name, nodes, edges, SEED, family)
                fixed_rows.append(manifest_line(name, edge_path, node_path))
                add_row(design_rows, name, "all_fixed_graph_methods", "all", nodes, edges, degree, family, SEED)

    for processes in (() if args.fixed_only else args.process_counts):
        per_p_rows = []
        for family in FAMILIES:
            nodes, edges = args.weak_vertices_per_rank * processes, args.weak_edges_per_rank * processes
            name = f"weak_{family}_p{processes:03d}"
            edge_path, node_path = write_graph(weak_dir, name, nodes, edges, SEED, family)
            line = manifest_line(name, edge_path, node_path)
            per_p_rows.append(line)
            weak_rows.append(line)
            degree = edges // nodes
            add_row(design_rows, name, "weak_scaling", processes, nodes, edges, degree, family, SEED)
        (manifests / f"weak_p{processes:03d}.tsv").write_text("".join(per_p_rows), encoding="utf-8")

    if not args.fixed_only:
        strong_processes = 256 if 256 in args.process_counts else max(args.process_counts)
        strong_nodes = args.weak_vertices_per_rank * strong_processes
        strong_edges = args.weak_edges_per_rank * strong_processes
        for family in FAMILIES:
            name = f"strong_{family}"
            weak_name = f"weak_{family}_p{strong_processes:03d}"
            edge_path = weak_dir / f"{weak_name}.edges"
            node_path = weak_dir / f"{weak_name}.nodes"
            fixed_rows.append(manifest_line(name, edge_path, node_path))
            add_row(design_rows, name, "all_fixed_graph_methods", "all", strong_nodes, strong_edges,
                    args.weak_edges_per_rank // args.weak_vertices_per_rank, family, SEED)

    (manifests / "fixed_graphs.tsv").write_text("".join(fixed_rows), encoding="utf-8")
    (manifests / "serial_grid.tsv").write_text("".join(fixed_rows), encoding="utf-8")
    (manifests / "strong_scaling.tsv").write_text("".join(fixed_rows), encoding="utf-8")
    (manifests / "weak_scaling.tsv").write_text("".join(weak_rows), encoding="utf-8")
    with (root / "experiment_design.csv").open("w", newline="", encoding="utf-8") as output:
        fields = ("name", "experiment", "family", "processes", "vertices", "edges", "average_out_degree", "seed")
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(design_rows)
    print(f"Fixed matrix: {len(fixed_rows)} datasets (3 original + 3 canonical synthetic + "
          f"{3 * len(args.serial_vertices) * len(args.serial_average_degrees)} size-grid + "
          f"{0 if args.fixed_only else 3} strong graphs)", flush=True)
    print(f"Weak matrix: {0 if args.fixed_only else len(args.process_counts)} process counts × 3 synthetic graph families", flush=True)
    print(f"Inputs and manifests: {root}", flush=True)


if __name__ == "__main__":
    main()

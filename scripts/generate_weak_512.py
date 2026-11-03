"""Append the optional 512-rank weak graphs without changing the fixed strong graphs."""
import argparse
import csv
from pathlib import Path

from generate_scaling_graphs import (FAMILIES, SEED, WEAK_EDGES_PER_RANK,
                                     WEAK_VERTICES_PER_RANK, manifest_line, write_graph)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-root", required=True, type=Path)
args = parser.parse_args()
root = args.output_root.resolve()
processes = 512
nodes = WEAK_VERTICES_PER_RANK * processes
edges = WEAK_EDGES_PER_RANK * processes
rows = []
for family in FAMILIES:
    name = f"weak_{family}_p{processes:03d}"
    edge_path, node_path = write_graph(root / "weak_scaling", name, nodes, edges, SEED, family)
    rows.append(manifest_line(name, edge_path, node_path))
manifest = root / "manifests" / "weak_p512.tsv"
manifest.write_text("".join(rows), encoding="utf-8")
with (root / "manifests" / "weak_scaling.tsv").open("a", encoding="utf-8") as output:
    output.writelines(rows)
with (root / "experiment_design.csv").open("a", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    for family in FAMILIES:
        writer.writerow((f"weak_{family}_p512", "weak_scaling", family, processes,
                         nodes, edges, edges // nodes, SEED))
print(f"Added p=512 weak graphs: 3 families × {nodes} vertices × {edges} edges", flush=True)

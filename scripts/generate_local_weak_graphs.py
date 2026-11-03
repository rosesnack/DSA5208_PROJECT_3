"""Generate the workstation-sized weak-scaling subset at p=1,2,4,8."""
import argparse
import csv
from pathlib import Path

from generate_scaling_graphs import (FAMILIES, SEED, WEAK_EDGES_PER_RANK,
                                     WEAK_VERTICES_PER_RANK, manifest_line, write_graph)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-root", required=True, type=Path)
args = parser.parse_args()
root = args.output_root.resolve()
manifests = root / "manifests"
manifests.mkdir(parents=True, exist_ok=True)
all_rows = []
with (root / "experiment_design.csv").open("w", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow(("name", "experiment", "family", "processes", "vertices",
                     "edges", "average_out_degree", "seed"))
    for processes in (1, 2, 4, 8):
        per_process = []
        for family in FAMILIES:
            name = f"weak_{family}_p{processes:03d}"
            nodes = WEAK_VERTICES_PER_RANK * processes
            edges = WEAK_EDGES_PER_RANK * processes
            edge_path, node_path = write_graph(root / "weak_scaling", name, nodes,
                                               edges, SEED, family)
            per_process.append(manifest_line(name, edge_path, node_path))
            writer.writerow((name, "weak_scaling", family, processes, nodes, edges,
                             edges // nodes, SEED))
        (manifests / f"weak_p{processes:03d}.tsv").write_text("".join(per_process), encoding="utf-8")
        all_rows.extend(per_process)
(manifests / "weak_scaling.tsv").write_text("".join(all_rows), encoding="utf-8")
print("Generated 12 local weak-scaling graphs (three families × four process counts)", flush=True)

"""List missing fixed-graph GPU cells left by interrupted Vanda jobs."""
import argparse
import csv
from pathlib import Path

from audit_fixed_matrix import gpu_cells


def repeat_count(folder):
    with (folder / "timings.csv").open(newline="", encoding="utf-8") as source:
        return sum(1 for _ in csv.DictReader(source))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gpu_root", type=Path)
    parser.add_argument("--graphs", nargs="+",
                        default=("strong_uniform", "strong_hub", "strong_controlled"))
    args = parser.parse_args()
    for graph in args.graphs:
        graph_root = args.gpu_root / graph
        cells = list(gpu_cells(graph_root, graph, graph_root / "complete.txt", (1, 2),
                               (1, 2, 4, 8, 16, 32)))
        complete = []
        missing = []
        for cell in cells:
            summary = cell["summary"]
            if summary.is_file() and (summary.parent / "timings.csv").is_file() and \
                    (summary.parent / "ranks.csv").is_file() and repeat_count(summary.parent) == 5:
                complete.append(cell)
            else:
                missing.append(cell)
        print(f"{graph}: {len(complete)}/{len(cells)} cells have five timings and saved ranks")
        for cell in missing:
            print(f"  MISSING {cell['stage']} {cell['layout']}")


if __name__ == "__main__":
    main()

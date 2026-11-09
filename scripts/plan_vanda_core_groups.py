"""Group only missing fixed CPU cells by nodes and actual cores per node."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from audit_fixed_matrix import resolve_cell, vanda_cells


def build_groups(root, reuse_roots):
    groups = defaultdict(list)
    for item in vanda_cells(root):
        stage = item["stage"]
        if stage not in ("mpi_cpu", "mpi_kokkos_cpu_t1", "mpi_openmp",
                         "mpi_kokkos_cpu_threads", "mpi_cpu_512", "mpi_kokkos_cpu_512_t1",
                         "mpi_openmp_512", "mpi_kokkos_cpu_512_t4"):
            continue
        resolved, _ = resolve_cell(item, root, reuse_roots)
        if resolved["summary"].is_file() and resolved["marker"].is_file():
            continue
        layout = dict(field.split("=") for field in item["layout"].split(",") if "=" in field)
        endpoint = "512" in stage
        nodes = 8 if endpoint else int(layout["n"])
        threads = int(layout.get("T", "4" if stage == "mpi_kokkos_cpu_512_t4" else "1"))
        processes = int(layout.get("p", str(512 // threads)))
        cores_per_node = processes * threads // nodes
        method = "hybrid" if stage in ("mpi_openmp", "mpi_openmp_512") else "mpi" if stage in ("mpi_cpu", "mpi_cpu_512") else "mpi_kokkos"
        mode = "halo" if item["layout"].endswith("halo") or ",halo," in item["layout"] else "allgather"
        groups[item["graph"], nodes, cores_per_node].append({
            "implementation": method, "processes": processes, "threads": threads,
            "communication": mode, "canonical_summary": str(item["summary"].relative_to(root))})
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--reuse-root", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = []
    for (graph, nodes, per_node), cells in build_groups(args.root, args.reuse_root).items():
        large = graph.startswith("strong_")
        minutes = 480 if large else 90 if nodes == 8 else 45
        priority = (0 if large and nodes == 1 and per_node == 32 else
                    1 if per_node == 32 and not large else 2 if per_node < 32 and not large else 3)
        # Complete the n=1 large-graph group before extending that family to more nodes.
        prerequisite = f"cpu_core_groups/{graph}/nodes1_cores32/complete.txt" if large and nodes > 1 else ""
        plan.append({"graph": graph, "nodes": nodes, "cores_per_node": per_node,
                     "cores": nodes * per_node, "priority": priority,
                     "walltime": f"{minutes // 60:02d}:{minutes % 60:02d}:00",
                     "prerequisite": prerequisite, "cells": cells})
    plan.sort(key=lambda g: (g["priority"], g["graph"] != "grid_controlled_n200000_d4",
                            g["graph"], g["nodes"], g["cores_per_node"]))
    args.output.write_text(json.dumps(plan, indent=2) + "\n")
    print(f'{len(plan)} resource groups, {sum(len(g["cells"]) for g in plan)} missing cells; no valid cells remeasured')


if __name__ == "__main__":
    main()

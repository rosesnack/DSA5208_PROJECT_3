"""Freeze audited missing CPU cells and the separately counted 512-core splits."""
import argparse
import json
from pathlib import Path

from audit_fixed_matrix import graph_names
from plan_vanda_core_groups import build_groups


def make_plan(root, reuse_roots, endpoint_proof):
    result = []
    for (graph, nodes, per_node), cells in build_groups(root, reuse_roots).items():
        large = graph.startswith("strong_")
        minutes = ({1: 210, 2: 210, 4: 240, 8: 360}[nodes] if per_node == 32 else 480) if large else {1: 20, 2: 30, 4: 45, 8: 60}[nodes]
        if per_node == 64:
            minutes = 480 if large else 60
        result.append({"graph": graph, "nodes": nodes, "cores_per_node": per_node,
                       "cores": nodes * per_node, "priority": 0 if per_node == 32 else 2 if per_node == 64 else 1,
                       "walltime": f"{minutes // 60:02d}:{minutes % 60:02d}:00",
                       "prerequisite": f"cpu_core_groups/{graph}/nodes1_cores32/complete.txt" if large and nodes > 1 else "",
                       "required_job": endpoint_proof if per_node == 64 else "",
                       "dense_launch_pause_s": 65 if per_node == 64 else 0,
                       "walltime_basis": "Ordinary batches: observed 37s-5m11s, reserve 20/30/45/60m by nodes. Large 32-core batches: 16m-79m observed; reserve 3.5/4/6h. Lower-parallelism large graphs reserve 8h. 512-core ordinary batches reserve 1h and require successful endpoint validation.",
                       "cells": cells})
    for graph in graph_names():
        cells = []
        for method in ("hybrid", "mpi_kokkos"):
            for threads in (2, 8, 16, 32):
                processes = 512 // threads
                for mode in ("allgather", "halo"):
                    suffix = "_halo" if mode == "halo" else ""
                    base = Path("strong") / graph / "nodes8_p512" if method == "hybrid" else Path("kokkos_cpu_512") / graph
                    folder = base / (method + suffix)
                    if method == "mpi_kokkos":
                        folder /= "OpenMP"
                    folder = folder / graph / f"p{processes}_t{threads}"
                    cells.append({"implementation": method, "processes": processes, "threads": threads,
                                  "communication": mode, "canonical_summary": str(folder / "summary.json")})
        result.append({"graph": graph, "nodes": 8, "cores_per_node": 64, "cores": 512,
                       "extension": "additional_512_splits", "raw_stage": "cpu_core_groups_extra512",
                       "priority": 3, "walltime": "08:00:00" if graph.startswith("strong_") else "01:00:00",
                       "prerequisite": "", "required_job": endpoint_proof, "dense_launch_pause_s": 65,
                       "cells": cells})
    return sorted(result, key=lambda g: (g["priority"], g["graph"].startswith("strong_"),
                                         g["graph"], g["nodes"], g["cores_per_node"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--reuse-root", type=Path, action="append", default=[])
    parser.add_argument("--endpoint-proof", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = make_plan(args.root, args.reuse_root, args.endpoint_proof)
    args.output.write_text(json.dumps(plan, indent=2) + "\n")
    print(f'{len(plan)} groups; {sum(len(g["cells"]) for g in plan if not g.get("extension"))} original missing cells; 720 added endpoint cells separately counted')

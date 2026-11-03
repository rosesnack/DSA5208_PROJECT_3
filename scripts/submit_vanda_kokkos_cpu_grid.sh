#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the run ID}"
PROJECT="${2:?Pass the Vanda project name}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
JOB_TABLE="results/updated_vanda_scaling/$RUN_ID/submitted_jobs.tsv"
MAX_NEW_GRAPHS="${MAX_NEW_GRAPHS:-1}"
test -f "results/updated_vanda_scaling/$RUN_ID/cpu_build.complete"

if [[ -n "${PAGERANK_GRAPH_NAMES:-}" ]]; then
    read -r -a GRAPH_NAMES <<< "$PAGERANK_GRAPH_NAMES"
else
    mapfile -t GRAPH_NAMES < <(python3 scripts/list_fixed_graphs.py)
fi

submitted=0
for graph in "${GRAPH_NAMES[@]}"; do
    (( submitted < MAX_NEW_GRAPHS )) || break
    test -f "results/updated_vanda_scaling/$RUN_ID/serial_grid/$graph/complete.txt" || continue
    for nodes in 1 2 4 8; do
        awk -F '\t' -v graph="$graph" -v nodes="$nodes" \
            '$1 == "kokkos_cpu_grid" && $2 == graph && $3 == nodes {found=1} END {exit !found}' \
            "$JOB_TABLE" && continue
        job=$(qsub -P "$PROJECT" -q auto -l walltime=02:00:00 \
            -l "select=${nodes}:ncpus=32:mpiprocs=32:ompthreads=1:mem=32gb" \
            -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,GRAPH_NAME=$graph,PAGERANK_NODE_COUNTS=$nodes" \
            scripts/vanda_kokkos_cpu_grid_job.pbs)
        printf 'kokkos_cpu_grid\t%s\t%s\t%s\n' "$graph" "$nodes" "$job" >> "$JOB_TABLE"
    done
    if ! awk -F '\t' -v graph="$graph" \
        '$1 == "kokkos_cpu_512" && $2 == graph {found=1} END {exit !found}' \
        "$JOB_TABLE"; then
        job=$(qsub -P "$PROJECT" -q auto -l walltime=02:00:00 \
            -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,GRAPH_NAME=$graph" \
            scripts/vanda_kokkos_cpu_512_job.pbs)
        printf 'kokkos_cpu_512\t%s\t8\t%s\n' "$graph" "$job" >> "$JOB_TABLE"
    fi
    ((submitted += 1))
done
printf 'Submitted Kokkos CPU thread grids for %s graph(s).\n' "$submitted"

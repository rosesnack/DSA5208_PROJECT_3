#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the existing run ID}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
RUN_ROOT="results/updated_vanda_scaling/$RUN_ID"
JOB_TABLE="$RUN_ROOT/submitted_jobs.tsv"
RECOVERY_TABLE="$RUN_ROOT/free_cpu_recovery.tsv"
MAX_NEW_JOBS="${MAX_NEW_JOBS:-8}"

test -f "$RUN_ROOT/kokkos_cpu_rebuild.complete"
submitted=0
while IFS= read -r graph; do
    for nodes in 1 2 4; do
        (( submitted < MAX_NEW_JOBS )) || break 2
        [[ -f "$RUN_ROOT/kokkos_cpu_grid/$graph/nodes$nodes/complete.txt" ]] && continue
        existing=$(awk -F '\t' -v graph="$graph" -v nodes="$nodes" \
            '$1 == "kokkos_cpu_grid" && $2 == graph && $3 == nodes {print $4}' \
            "$JOB_TABLE")
        [[ -n "$existing" ]] && continue
        dependency=()
        if [[ ! -f "$RUN_ROOT/serial_grid/$graph/complete.txt" ]]; then
            serial_job=$(awk -F '\t' -v graph="$graph" \
                '$1 == "serial" && $2 == graph {print $5}' "$RECOVERY_TABLE")
            dependency=(-W "depend=afterok:$serial_job")
        fi
        job=$(qsub -q auto_free -l walltime=02:00:00 \
            -l "select=${nodes}:ncpus=32:mpiprocs=32:ompthreads=1:mem=32gb" \
            "${dependency[@]}" \
            -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,GRAPH_NAME=$graph,PAGERANK_NODE_COUNTS=$nodes" \
            scripts/vanda_kokkos_cpu_grid_job.pbs)
        printf 'kokkos_cpu_grid\t%s\t%s\t%s\n' \
            "$graph" "$nodes" "$job" >> "$JOB_TABLE"
        printf '%s\tnodes%s\t%s\n' "$graph" "$nodes" "$job"
        ((submitted += 1))
    done
done < <(python3 scripts/list_fixed_graphs.py)

printf 'Submitted %s free-queue Kokkos CPU thread-grid batches.\n' "$submitted"

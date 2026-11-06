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
FREE_MPI_WALLTIME="${FREE_MPI_WALLTIME:-08:00:00}"

if [[ ! -f "$RECOVERY_TABLE" ]]; then
    printf 'stage\tgraph\tnodes\toriginal_job\treplacement_job\n' > "$RECOVERY_TABLE"
fi

submitted=0
while IFS= read -r graph; do
    for nodes in 1 2 4; do
        (( submitted < MAX_NEW_JOBS )) || break 2
        [[ -f "$RUN_ROOT/strong/$graph/nodes$nodes/complete.txt" ]] && continue
        replacement=$(awk -F '\t' -v graph="$graph" -v nodes="$nodes" \
            '$1 == "mpi_strong" && $2 == graph && $3 == nodes {print $5}' \
            "$RECOVERY_TABLE")
        [[ -n "$replacement" ]] && continue
        original=$(awk -F '\t' -v graph="$graph" -v nodes="$nodes" \
            '$1 == "mpi_strong" && $2 == graph && $3 == nodes {print $4}' \
            "$JOB_TABLE")
        dependency=()
        if [[ ! -f "$RUN_ROOT/serial_grid/$graph/complete.txt" ]]; then
            serial_job=$(awk -F '\t' -v graph="$graph" \
                '$1 == "serial" && $2 == graph {print $5}' "$RECOVERY_TABLE")
            dependency=(-W "depend=afterok:$serial_job")
        fi
        replacement=$(qsub -q auto_free -l "walltime=$FREE_MPI_WALLTIME" \
            -l "select=${nodes}:ncpus=32:mpiprocs=32:ompthreads=1:mem=32gb" \
            "${dependency[@]}" \
            -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,GRAPH_NAME=$graph,PAGERANK_NODE_COUNTS=$nodes,PAGERANK_RUN_STRONG=1,PAGERANK_RUN_WEAK=0" \
            scripts/vanda_mpi_scaling_job.pbs)
        if [[ -n "$original" ]]; then
            printf 'mpi_strong\t%s\t%s\t%s\t%s\n' \
                "$graph" "$nodes" "$original" "$replacement" >> "$RECOVERY_TABLE"
        else
            printf 'mpi_strong\t%s\t%s\t%s\n' \
                "$graph" "$nodes" "$replacement" >> "$JOB_TABLE"
        fi
        printf '%s\tnodes%s\t%s\n' "$graph" "$nodes" "$replacement"
        ((submitted += 1))
    done
done < <(python3 scripts/list_fixed_graphs.py)

printf 'Submitted %s free-queue MPI strong-scaling batches.\n' "$submitted"

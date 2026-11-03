#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the run ID}"
PROJECT="${2:?Pass the Vanda project name}"
GRAPH_NAME="${3:?Pass the failed graph name}"
NODE_COUNT="${4:?Pass the failed node count}"
ORIGINAL_JOB="${5:?Pass the failed PBS job ID}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
RUN_ROOT="results/updated_vanda_scaling/$RUN_ID"
RETRY_TABLE="$RUN_ROOT/retry_jobs.tsv"

if [[ -f "$RETRY_TABLE" ]] && awk -F '\t' -v graph="$GRAPH_NAME" -v nodes="$NODE_COUNT" \
    '$1 == "mpi_strong" && $2 == graph && $3 == nodes {found=1} END {exit !found}' \
    "$RETRY_TABLE"; then
    echo "A retry is already recorded for $GRAPH_NAME nodes=$NODE_COUNT"
    exit 0
fi

variables="RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,GRAPH_NAME=$GRAPH_NAME,PAGERANK_NODE_COUNTS=$NODE_COUNT"
job=$(qsub -P "$PROJECT" -q auto -l walltime=04:00:00 \
    -l "select=$NODE_COUNT:ncpus=32:mpiprocs=32:ompthreads=1:mem=32gb" \
    -v "$variables" scripts/vanda_retry_mpi_strong_job.pbs)
if [[ ! -f "$RETRY_TABLE" ]]; then
    printf 'stage\tgraph\tnodes\toriginal_job\treplacement_job\treason\n' > "$RETRY_TABLE"
fi
printf 'mpi_strong\t%s\t%s\t%s\t%s\twalltime\n' \
    "$GRAPH_NAME" "$NODE_COUNT" "$ORIGINAL_JOB" "$job" >> "$RETRY_TABLE"
printf 'Retry submitted: %s nodes=%s job=%s\n' "$GRAPH_NAME" "$NODE_COUNT" "$job"

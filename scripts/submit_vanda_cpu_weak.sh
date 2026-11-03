#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the existing run ID}"
PROJECT="${2:?Pass the Vanda PBS project name}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
JOB_TABLE="results/updated_vanda_scaling/$RUN_ID/submitted_jobs.tsv"
test -f "results/updated_vanda_scaling/$RUN_ID/data.complete"
test -f "results/updated_vanda_scaling/$RUN_ID/data_512.complete"
test -f "results/updated_vanda_scaling/$RUN_ID/cpu_smoke_uniform/complete.txt"

weak_job=$(awk -F '\t' '$1 == "mpi_weak" {print $4}' "$JOB_TABLE")
if [[ -z "$weak_job" ]]; then
    weak_job=$(qsub -P "$PROJECT" -q auto -l walltime=04:00:00 \
        -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,PAGERANK_NODE_COUNTS=8,PAGERANK_RUN_STRONG=0,PAGERANK_RUN_WEAK=1" \
        scripts/vanda_mpi_scaling_job.pbs)
    printf 'mpi_weak\t-\t8\t%s\n' "$weak_job" >> "$JOB_TABLE"
fi
printf 'mpi_weak\t%s\n' "$weak_job"

for family in uniform hub controlled; do
    if awk -F '\t' -v family="$family" \
        '$1 == "mpi_weak_512" && $2 == family {found = 1} END {exit !found}' "$JOB_TABLE"; then
        continue
    fi
    job=$(qsub -P "$PROJECT" -q auto -l walltime=01:00:00 \
        -W "depend=afterok:$weak_job" \
        -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,WEAK_FAMILY=$family" \
        scripts/vanda_mpi_512_job.pbs)
    printf 'mpi_weak_512\t%s\t8\t%s\n' "$family" "$job" >> "$JOB_TABLE"
    printf 'mpi_weak_512_%s\t%s\n' "$family" "$job"
done

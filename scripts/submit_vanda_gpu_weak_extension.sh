#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the existing run ID}"
PROJECT="${2:?Pass the Vanda project name}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
RUN_ROOT="results/updated_vanda_scaling/$RUN_ID"
JOB_TABLE="$RUN_ROOT/submitted_jobs.tsv"

existing_job() {
    awk -F '\t' -v stage="$1" '$1 == stage {print $4}' "$JOB_TABLE"
}

test -f "$RUN_ROOT/gpu_weak/complete.txt"
variables="RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT"
for count in 4 8; do
    stage="gpu_weak_ext_$count"
    job=$(existing_job "$stage")
    if [[ -z "$job" ]]; then
        job=$(qsub -P "$PROJECT" -q auto -l \
            "select=$count:ncpus=36:mpiprocs=1:ompthreads=8:ngpus=1:mem=120gb" \
            -v "$variables,GPU_COUNT=$count" scripts/vanda_gpu_weak_extension_compute.pbs)
        printf '%s\t-\t%s\t%s\n' "$stage" "$count" "$job" >> "$JOB_TABLE"
    fi
    printf '%s\t%s\n' "$stage" "$job"
    if (( count == 4 )); then p4="$job"; else p8="$job"; fi
done

check=$(existing_job gpu_weak_ext_validate)
if [[ -z "$check" ]]; then
    check=$(qsub -q auto_free -W "depend=afterok:$p4:$p8" \
        -v "$variables" scripts/vanda_gpu_weak_extension_validate.pbs)
    printf 'gpu_weak_ext_validate\t-\t8\t%s\n' "$check" >> "$JOB_TABLE"
fi
printf 'gpu_weak_ext_validate\t%s\n' "$check"

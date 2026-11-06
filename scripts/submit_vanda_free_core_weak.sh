#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the existing run ID}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
RUN_ROOT="results/updated_vanda_scaling/$RUN_ID"
JOB_TABLE="$RUN_ROOT/free_core_weak_jobs.tsv"

test -f "$RUN_ROOT/data_512.complete"
test -f "$RUN_ROOT/cpu_build.complete"
test -x build-vanda-matrix-cpu/pagerank_hybrid
test -x build-vanda-matrix-cpu/pagerank_mpi_kokkos

if [[ ! -f "$JOB_TABLE" ]]; then
    printf 'family\tjob_id\tscope\n' > "$JOB_TABLE"
fi

for family in hub controlled; do
    [[ -f "$RUN_ROOT/weak_core/$family/complete_p128.txt" ]] && continue
    existing=$(awk -F '\t' -v family="$family" '$1 == family {print $2}' "$JOB_TABLE")
    [[ -z "$existing" ]] || continue
    job=$(qsub -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,WEAK_FAMILY=$family" \
        scripts/vanda_cpu_core_weak_free_job.pbs)
    printf '%s\t%s\tC=4,8,16,32,64,128\n' "$family" "$job" >> "$JOB_TABLE"
    printf '%s\t%s\n' "$family" "$job"
done

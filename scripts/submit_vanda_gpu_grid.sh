#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the existing run ID}"
PROJECT="${2:?Pass the Vanda PBS project name}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
JOB_TABLE="results/updated_vanda_scaling/$RUN_ID/submitted_jobs.tsv"
test -f "results/updated_vanda_scaling/$RUN_ID/data.complete"
test -f "results/updated_vanda_scaling/$RUN_ID/gpu_build.complete"
test -f "results/updated_vanda_scaling/$RUN_ID/gpu_smoke_uniform/complete.txt"

while IFS= read -r graph; do
    if awk -F '\t' -v graph="$graph" \
        '$1 == "gpu" && $2 == graph {found = 1} END {exit !found}' "$JOB_TABLE"; then
        continue
    fi
    job=$(qsub -P "$PROJECT" -q auto \
        -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,GRAPH_NAME=$graph" \
        scripts/vanda_gpu_scaling_job.pbs)
    printf 'gpu\t%s\t2\t%s\n' "$graph" "$job" >> "$JOB_TABLE"
    printf '%s\t%s\n' "$graph" "$job"
done < <(python3 scripts/list_fixed_graphs.py)

if ! awk -F '\t' '$1 == "gpu_weak" {found = 1} END {exit !found}' "$JOB_TABLE"; then
    job=$(qsub -P "$PROJECT" -q auto \
        -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT" scripts/vanda_gpu_weak_job.pbs)
    printf 'gpu_weak\t-\t2\t%s\n' "$job" >> "$JOB_TABLE"
    printf 'gpu_weak\t%s\n' "$job"
fi

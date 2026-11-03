#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the existing run ID}"
PROJECT="${2:?Pass the Vanda PBS project name}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
JOB_TABLE="results/updated_vanda_scaling/$RUN_ID/submitted_jobs.tsv"
test -f "results/updated_vanda_scaling/$RUN_ID/data.complete"
test -f "results/updated_vanda_scaling/$RUN_ID/cpu_build.complete"

while IFS= read -r graph; do
    if awk -F '\t' -v graph="$graph" \
        '$1 == "serial" && $2 == graph {found = 1} END {exit !found}' "$JOB_TABLE"; then
        continue
    fi
    job=$(qsub -P "$PROJECT" -q auto -l walltime=01:00:00 \
        -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,GRAPH_NAME=$graph" \
        scripts/vanda_serial_grid_job.pbs)
    printf 'serial\t%s\t1\t%s\n' "$graph" "$job" >> "$JOB_TABLE"
    printf '%s\t%s\n' "$graph" "$job"
done < <(python3 scripts/list_fixed_graphs.py)

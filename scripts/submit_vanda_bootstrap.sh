#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
VARIABLES="RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT"
mkdir -p "results/updated_vanda_scaling/$RUN_ID"
JOB_TABLE="results/updated_vanda_scaling/$RUN_ID/submitted_jobs.tsv"
printf 'stage\tgraph\tnodes\tjob_id\n' > "$JOB_TABLE"

data_job=$(qsub -v "$VARIABLES" scripts/vanda_prepare_scaling_data.pbs)
cpu_build_job=$(qsub -v "$VARIABLES" scripts/vanda_cpu_build_job.pbs)
gpu_build_job=$(qsub -v "$VARIABLES" scripts/vanda_gpu_build_job.pbs)
data512_job=$(qsub -W "depend=afterok:$data_job" -v "$VARIABLES" \
    scripts/vanda_prepare_512_data.pbs)
cpu_smoke_job=$(qsub -W "depend=afterok:$cpu_build_job" -v "RUN_ID=$RUN_ID" \
    scripts/vanda_cpu_smoke_job.pbs)
gpu_smoke_job=$(qsub -W "depend=afterok:$gpu_build_job" -v "RUN_ID=$RUN_ID" \
    scripts/vanda_gpu_smoke_job.pbs)

printf 'data\t-\t1\t%s\ncpu_build\t-\t1\t%s\ngpu_build\t-\t1\t%s\ndata_512\t-\t1\t%s\ncpu_smoke\tuniform\t1\t%s\ngpu_smoke\tuniform\t2\t%s\n' \
    "$data_job" "$cpu_build_job" "$gpu_build_job" "$data512_job" \
    "$cpu_smoke_job" "$gpu_smoke_job" >> "$JOB_TABLE"
printf 'Run ID: %s\nJob table: %s\n' "$RUN_ID" "$JOB_TABLE"

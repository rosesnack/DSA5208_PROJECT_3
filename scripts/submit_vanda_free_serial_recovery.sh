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

if [[ ! -f "$RECOVERY_TABLE" ]]; then
    printf 'stage\tgraph\tnodes\toriginal_job\treplacement_job\n' > "$RECOVERY_TABLE"
fi

submitted=0
while IFS= read -r graph; do
    (( submitted < MAX_NEW_JOBS )) || break
    [[ -f "$RUN_ROOT/serial_grid/$graph/complete.txt" ]] && continue
    replacement=$(awk -F '\t' -v graph="$graph" \
        '$1 == "serial" && $2 == graph {print $5}' "$RECOVERY_TABLE")
    [[ -n "$replacement" ]] && continue
    original=$(awk -F '\t' -v graph="$graph" \
        '$1 == "serial" && $2 == graph {print $4}' "$JOB_TABLE")
    replacement=$(qsub -q auto_free -l walltime=02:00:00 \
        -v "RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,GRAPH_NAME=$graph" \
        scripts/vanda_serial_grid_job.pbs)
    printf 'serial\t%s\t1\t%s\t%s\n' "$graph" "$original" "$replacement" \
        >> "$RECOVERY_TABLE"
    printf '%s\t%s\n' "$graph" "$replacement"
    ((submitted += 1))
done < <(python3 scripts/list_fixed_graphs.py)

printf 'Submitted %s free-queue serial replacements.\n' "$submitted"

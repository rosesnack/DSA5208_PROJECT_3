#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the existing run ID}"
PROJECT="${2:?Pass the Vanda project name}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
JOB_TABLE="results/updated_vanda_scaling/$RUN_ID/submitted_jobs.tsv"
MAX_NEW_FAMILIES="${MAX_NEW_FAMILIES:-1}"
test -f "results/updated_vanda_scaling/$RUN_ID/data_512.complete"
test -f "results/updated_vanda_scaling/$RUN_ID/cpu_build.complete"

submitted=0
for family in uniform hub controlled; do
    (( submitted < MAX_NEW_FAMILIES )) || break
    variables="RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,WEAK_FAMILY=$family"
    primary=$(awk -F '\t' -v family="$family" \
        '$1 == "cpu_core_weak" && $2 == family {print $4}' "$JOB_TABLE")
    extension=$(awk -F '\t' -v family="$family" \
        '$1 == "cpu_core_weak_512" && $2 == family {print $4}' "$JOB_TABLE")
    [[ -z "$primary" || -z "$extension" ]] || continue
    if [[ -z "$primary" ]]; then
        primary=$(qsub -P "$PROJECT" -q auto -v "$variables" \
            scripts/vanda_cpu_core_weak_job.pbs)
        printf 'cpu_core_weak\t%s\t8\t%s\n' "$family" "$primary" >> "$JOB_TABLE"
    fi
    if [[ -z "$extension" ]]; then
        dependency=()
        if [[ ! -f "results/updated_vanda_scaling/$RUN_ID/weak_core/$family/complete_p256.txt" ]]; then
            dependency=(-W "depend=afterok:$primary")
        fi
        extension=$(qsub -P "$PROJECT" -q auto "${dependency[@]}" -v "$variables" \
            scripts/vanda_cpu_core_weak_512_job.pbs)
        printf 'cpu_core_weak_512\t%s\t8\t%s\n' "$family" "$extension" >> "$JOB_TABLE"
    fi
    ((submitted += 1))
done
printf 'Submitted core-normalized weak scaling for %s family(s).\n' "$submitted"

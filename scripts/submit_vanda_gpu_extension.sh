#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the existing run ID}"
PROJECT="${2:?Pass the Vanda project name}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
RUN_ROOT="results/updated_vanda_scaling/$RUN_ID"
JOB_TABLE="$RUN_ROOT/submitted_jobs.tsv"
MAX_NEW_GRAPHS="${MAX_NEW_GRAPHS:-1}"

existing_job() {
    awk -F '\t' -v stage="$1" -v graph="$2" \
        '$1 == stage && $2 == graph {print $4}' "$JOB_TABLE"
}

submitted=0
while IFS= read -r graph; do
    (( submitted < MAX_NEW_GRAPHS )) || break
    [[ -f "$RUN_ROOT/gpu/$graph/complete_p4_p8.txt" ]] && continue
    test -f "$RUN_ROOT/gpu/$graph/complete.txt"
    variables="RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT,GRAPH_NAME=$graph"
    p4=$(existing_job gpu_ext_4 "$graph")
    if [[ -z "$p4" ]]; then
        p4=$(qsub -P "$PROJECT" -q auto -l \
            select=4:ncpus=36:mpiprocs=1:ompthreads=8:ngpus=1:mem=120gb \
            -v "$variables,GPU_COUNT=4" scripts/vanda_gpu_extension_compute.pbs)
        printf 'gpu_ext_4\t%s\t4\t%s\n' "$graph" "$p4" >> "$JOB_TABLE"
    fi
    p8=$(existing_job gpu_ext_8 "$graph")
    if [[ -z "$p8" ]]; then
        p8=$(qsub -P "$PROJECT" -q auto -l \
            select=8:ncpus=36:mpiprocs=1:ompthreads=8:ngpus=1:mem=120gb \
            -v "$variables,GPU_COUNT=8" scripts/vanda_gpu_extension_compute.pbs)
        printf 'gpu_ext_8\t%s\t8\t%s\n' "$graph" "$p8" >> "$JOB_TABLE"
    fi
    check=$(existing_job gpu_ext_validate "$graph")
    if [[ -z "$check" ]]; then
        check=$(qsub -q auto_free -W "depend=afterok:$p4:$p8" \
            -v "$variables" scripts/vanda_gpu_extension_validate.pbs)
        printf 'gpu_ext_validate\t%s\t8\t%s\n' "$graph" "$check" >> "$JOB_TABLE"
    fi
    printf '%s\tp4=%s\tp8=%s\tcheck=%s\n' "$graph" "$p4" "$p8" "$check"
    ((submitted += 1))
done < <(python3 scripts/list_fixed_graphs.py)

printf 'Submitted Vanda 4/8-GPU extension for %s graph(s).\n' "$submitted"

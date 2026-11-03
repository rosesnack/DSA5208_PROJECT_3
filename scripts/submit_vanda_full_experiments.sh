#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:?Pass the existing run ID}"
PROJECT="${2:?Pass the Vanda project name shown by hpc project}"
DATA_ROOT="${DATA_ROOT:-/scratch/$USER/dsa5208_scaling/$RUN_ID}"
VARIABLES="RUN_ID=$RUN_ID,DATA_ROOT=$DATA_ROOT"
JOB_TABLE="results/updated_vanda_scaling/$RUN_ID/submitted_jobs.tsv"
MAX_NEW_GRAPHS="${MAX_NEW_GRAPHS:-1}"
INCLUDE_WEAK="${INCLUDE_WEAK:-0}"
for marker in data data_512 cpu_build gpu_build; do
    test -f "results/updated_vanda_scaling/$RUN_ID/$marker.complete"
done
test -f "results/updated_vanda_scaling/$RUN_ID/cpu_smoke_uniform/complete.txt"
test -f "results/updated_vanda_scaling/$RUN_ID/gpu_smoke_uniform/complete.txt"

existing_job() {
    awk -F '\t' -v stage="$1" -v graph="$2" -v nodes="$3" \
        '$1 == stage && $2 == graph && $3 == nodes {print $4}' "$JOB_TABLE"
}

if [[ -n "${PAGERANK_GRAPH_NAMES:-}" ]]; then
    read -r -a GRAPH_NAMES <<< "$PAGERANK_GRAPH_NAMES"
else
    mapfile -t GRAPH_NAMES < <(python3 scripts/list_fixed_graphs.py)
fi
new_graphs=0
for graph in "${GRAPH_NAMES[@]}"; do
    needs_batch=0
    for nodes in 1 2 4 8; do
        [[ -n "$(existing_job mpi_strong "$graph" "$nodes")" ]] || needs_batch=1
    done
    [[ -n "$(existing_job mpi_strong_512 "$graph" 8)" ]] || needs_batch=1
    [[ -n "$(existing_job gpu "$graph" 2)" ]] || needs_batch=1
    (( needs_batch == 1 )) || continue
    (( new_graphs < MAX_NEW_GRAPHS )) || continue
    ((new_graphs += 1))
    graph_variables="$VARIABLES,GRAPH_NAME=$graph"
    serial_job=$(existing_job serial "$graph" 1)
    if [[ -z "$serial_job" ]]; then
        serial_job=$(qsub -P "$PROJECT" -q auto -l walltime=01:00:00 \
            -v "$graph_variables" scripts/vanda_serial_grid_job.pbs)
        printf 'serial\t%s\t1\t%s\n' "$graph" "$serial_job" >> "$JOB_TABLE"
    fi
    dependency=()
    if [[ ! -f "results/updated_vanda_scaling/$RUN_ID/serial_grid/$graph/complete.txt" ]]; then
        dependency=(-W "depend=afterok:$serial_job")
    fi
    for nodes in 1 2 4 8; do
        [[ -z "$(existing_job mpi_strong "$graph" "$nodes")" ]] || continue
        mpi_variables="$graph_variables,PAGERANK_NODE_COUNTS=$nodes,PAGERANK_RUN_STRONG=1,PAGERANK_RUN_WEAK=0"
        mpi_job=$(qsub -P "$PROJECT" -q auto "${dependency[@]}" -l walltime=01:00:00 \
            -l "select=${nodes}:ncpus=32:mpiprocs=32:ompthreads=1:mem=32gb" \
            -v "$mpi_variables" scripts/vanda_mpi_scaling_job.pbs)
        printf 'mpi_strong\t%s\t%s\t%s\n' "$graph" "$nodes" "$mpi_job" >> "$JOB_TABLE"
    done
    if [[ -z "$(existing_job gpu "$graph" 2)" ]]; then
        gpu_job=$(qsub -P "$PROJECT" -q auto -v "$graph_variables" \
            scripts/vanda_gpu_scaling_job.pbs)
        printf 'gpu\t%s\t2\t%s\n' "$graph" "$gpu_job" >> "$JOB_TABLE"
    fi
    if [[ -z "$(existing_job mpi_strong_512 "$graph" 8)" ]]; then
        mpi_512_job=$(qsub -P "$PROJECT" -q auto "${dependency[@]}" \
            -l walltime=01:00:00 -v "$graph_variables" scripts/vanda_mpi_512_job.pbs)
        printf 'mpi_strong_512\t%s\t8\t%s\n' "$graph" "$mpi_512_job" >> "$JOB_TABLE"
    fi
done

if [[ "$INCLUDE_WEAK" == 1 ]]; then
    WEAK_JOB=$(existing_job mpi_weak - 8)
    if [[ -z "$WEAK_JOB" ]]; then
        weak_variables="$VARIABLES,PAGERANK_NODE_COUNTS=8,PAGERANK_RUN_STRONG=0,PAGERANK_RUN_WEAK=1"
        WEAK_JOB=$(qsub -P "$PROJECT" -q auto -l walltime=01:00:00 \
            -v "$weak_variables" scripts/vanda_mpi_scaling_job.pbs)
        printf 'mpi_weak\t-\t8\t%s\n' "$WEAK_JOB" >> "$JOB_TABLE"
    fi
    if [[ -z "$(existing_job gpu_weak - 2)" ]]; then
        gpu_weak_job=$(qsub -P "$PROJECT" -q auto -v "$VARIABLES" \
            scripts/vanda_gpu_weak_job.pbs)
        printf 'gpu_weak\t-\t2\t%s\n' "$gpu_weak_job" >> "$JOB_TABLE"
    fi
    for family in uniform hub controlled; do
        [[ -z "$(existing_job mpi_weak_512 "$family" 8)" ]] || continue
        weak_512_job=$(qsub -P "$PROJECT" -q auto -l walltime=01:00:00 \
            -W "depend=afterok:$WEAK_JOB" -v "$VARIABLES,WEAK_FAMILY=$family" \
            scripts/vanda_mpi_512_job.pbs)
        printf 'mpi_weak_512\t%s\t8\t%s\n' "$family" "$weak_512_job" >> "$JOB_TABLE"
    done
fi

cat <<EOF
Experiment run: $RUN_ID
Shared input/output scratch: $DATA_ROOT
Vanda project: $PROJECT
Prerequisite data, builds, and smoke tests: complete
Fixed graph batches resumed this invocation: $new_graphs (cap: $MAX_NEW_GRAPHS)
Weak scaling submitted this invocation: $INCLUDE_WEAK
Job IDs and graph/node assignments: $JOB_TABLE
EOF

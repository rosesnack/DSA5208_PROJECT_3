#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DATA_ROOT="${DATA_ROOT:?Set DATA_ROOT}"
RUN_ID="${RUN_ID:?Set RUN_ID}"
WEAK_FAMILY="${WEAK_FAMILY:?Set WEAK_FAMILY}"
read -r -a core_counts <<< "${CORE_WEAK_SIZES:-4 8 16 32 64 128 256}"
RESULT_ROOT="$DATA_ROOT/results/weak_core/$WEAK_FAMILY"
DESTINATION="$ROOT/results/updated_vanda_scaling/$RUN_ID/weak_core/$WEAK_FAMILY"
export PAGERANK_RESULTS_ROOT="$RESULT_ROOT"
export PAGERANK_ENVIRONMENT=vanda-gcc13-release PAGERANK_RUN_ID="$RUN_ID"
export PAGERANK_REPEATS=5 PAGERANK_WARMUPS=1
export PAGERANK_HYBRID_MAX_TOTAL_THREADS=512
export OMP_DYNAMIC=FALSE OMP_PROC_BIND=spread OMP_PLACES=cores
mkdir -p "$RESULT_ROOT/manifests" "$RESULT_ROOT/mapping"
if [[ "${core_counts[*]}" == '512' ]]; then
    environment_file="$RESULT_ROOT/environment_p512.txt"
else
    environment_file="$RESULT_ROOT/environment_p256.txt"
fi
{
    printf 'PBS job: %s\n' "$PBS_JOBID"
    lscpu | grep 'Model name'
    grep -E '^(CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER):' build-vanda-matrix-cpu/CMakeCache.txt
    sort -u "$PBS_NODEFILE"
} > "$environment_file"

for cores in "${core_counts[@]}"; do
    processes=$((cores / 4))
    nodes=$((processes / 8))
    (( nodes < 1 )) && nodes=1
    (( cores == 512 )) && nodes=8
    ranks_per_node=$((processes / nodes))
    name=$(printf 'weak_%s_p%03d' "$WEAK_FAMILY" "$cores")
    manifest="$RESULT_ROOT/manifests/${name}_${PBS_JOBID}.tsv"
    python3 scripts/select_graph_manifest.py "$DATA_ROOT/manifests/weak_scaling.tsv" \
        "$name" "$manifest"
    export PAGERANK_DATASET_MANIFEST="$manifest"
    for communication in allgather halo; do
        OMP_NUM_THREADS=4 PAGERANK_KOKKOS_THREADS=4 \
            mpiexec -x LD_LIBRARY_PATH -x OMP_NUM_THREADS -x PAGERANK_KOKKOS_THREADS \
            --map-by "ppr:${ranks_per_node}:node" --bind-to none -n "$processes" \
            python3 scripts/mpi_affinity_exec.py 4 \
            ./build-vanda-matrix-cpu/mpi_rank_hosts \
            | sort -t, -k1,1n > "$RESULT_ROOT/mapping/${name}_${communication}.csv"
        PAGERANK_HYBRID_THREADS=4 \
            mpiexec -x LD_LIBRARY_PATH -x PAGERANK_HYBRID_THREADS \
            --map-by "ppr:${ranks_per_node}:node" \
            --bind-to none -n "$processes" \
            python3 scripts/mpi_affinity_exec.py 4 \
            ./build-vanda-matrix-cpu/pagerank_hybrid --communication="$communication"
        OMP_NUM_THREADS=4 PAGERANK_KOKKOS_THREADS=4 \
            mpiexec -x LD_LIBRARY_PATH -x OMP_NUM_THREADS -x PAGERANK_KOKKOS_THREADS \
            --map-by "ppr:${ranks_per_node}:node" --bind-to none -n "$processes" \
            python3 scripts/mpi_affinity_exec.py 4 \
            ./build-vanda-matrix-cpu/pagerank_mpi_kokkos --communication="$communication"
    done
done

export PAGERANK_DATASET_MANIFEST="$DATA_ROOT/manifests/weak_scaling.tsv"
read -r -a processes_to_validate <<< "$(for cores in "${core_counts[@]}"; do printf '%s ' "$((cores / 4))"; done)"
report_suffix="_core_${WEAK_FAMILY}"
[[ "${core_counts[*]}" == '512' ]] && report_suffix="_core512_${WEAK_FAMILY}"
python3 scripts/validate_weak_matrix.py hybrid --threads 4 --graph-scale 4 \
    --processes "${processes_to_validate[@]}" --families "$WEAK_FAMILY" \
    --suffix "$report_suffix"
python3 scripts/validate_weak_matrix.py mpi_kokkos --backend OpenMP --threads 4 \
    --graph-scale 4 --processes "${processes_to_validate[@]}" \
    --families "$WEAK_FAMILY" --suffix "$report_suffix"

mkdir -p "$DESTINATION"
rsync -a --exclude='ranks.csv' "$RESULT_ROOT/." "$DESTINATION/"
if [[ "${core_counts[*]}" == '512' ]]; then
    printf '%s\n' "$PBS_JOBID" > "$DESTINATION/complete_p512.txt"
else
    printf '%s\n' "$PBS_JOBID" > "$DESTINATION/complete_p256.txt"
fi

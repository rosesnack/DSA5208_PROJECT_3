#!/usr/bin/env bash
set -euo pipefail

# Independent checks run in a dependent free-queue job when requested.
validate_result() {
    if [[ "${PAGERANK_DEFER_VALIDATION:-0}" != 1 ]]; then
        python3 "$@"
    fi
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source "$ROOT/scripts/vanda_reuse_measurements.sh"
DATA_ROOT="${DATA_ROOT:?Set DATA_ROOT to the generated Vanda data directory}"
RUN_ID="${RUN_ID:?Set RUN_ID}"
GRAPH_NAME="${GRAPH_NAME:?Set GRAPH_NAME}"
NODES="${PAGERANK_NODE_COUNTS:?Set one node count}"
RESULT_ROOT="$DATA_ROOT/results/kokkos_cpu_grid/$GRAPH_NAME/nodes$NODES"
DESTINATION="$ROOT/results/runs/$RUN_ID/kokkos_cpu_grid/$GRAPH_NAME/nodes$NODES"
MANIFEST="$DATA_ROOT/manifests/kokkos_${GRAPH_NAME}_${PBS_JOBID}.tsv"

export PAGERANK_ENVIRONMENT=vanda-gcc13-release PAGERANK_RUN_ID="$RUN_ID"
export PAGERANK_REPEATS=5 PAGERANK_WARMUPS=1
export PAGERANK_RESULTS_ROOT="$RESULT_ROOT" PAGERANK_DATASET_MANIFEST="$MANIFEST"
export OMP_DYNAMIC=FALSE OMP_PROC_BIND=spread OMP_PLACES=cores
mkdir -p "$RESULT_ROOT/serial" "$RESULT_ROOT/mapping"
python3 scripts/select_graph_manifest.py "$DATA_ROOT/manifests/strong_scaling.tsv" \
    "$GRAPH_NAME" "$MANIFEST"
mkdir -p "$RESULT_ROOT/serial/$GRAPH_NAME"
cp -al --remove-destination "$DATA_ROOT/results/serial_grid/$GRAPH_NAME/serial/$GRAPH_NAME/." "$RESULT_ROOT/serial/$GRAPH_NAME/"
validate_result scripts/validate_serial.py

{
    printf 'PBS job: %s\nGraph: %s\nNodes: %s\n' "$PBS_JOBID" "$GRAPH_NAME" "$NODES"
    uname -a
    lscpu | grep -E 'Model name|Socket\(s\)|Core\(s\) per socket|CPU\(s\)'
    mpicxx --showme:version
    grep -E '^(CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER):' build-vanda-matrix-cpu/CMakeCache.txt
    sort -u "$PBS_NODEFILE"
} > "$RESULT_ROOT/environment.txt"

bash scripts/record_vanda_allocation.sh "$RESULT_ROOT/cpu_hosts.jsonl"

for threads in 2 4 8 16 32; do
    processes=()
    for ranks_per_node in 1 2 4 8 16 32; do
        (( ranks_per_node * threads <= 32 )) || continue
        p=$((NODES * ranks_per_node))
        processes+=("$p")
        mapping="ppr:${ranks_per_node}:node"
        OMP_NUM_THREADS="$threads" PAGERANK_KOKKOS_THREADS="$threads" \
            mpiexec -x LD_LIBRARY_PATH -x OMP_NUM_THREADS -x PAGERANK_KOKKOS_THREADS \
            --map-by "$mapping" --bind-to none -n "$p" \
            python3 scripts/mpi_affinity_exec.py "$threads" \
            ./build-vanda-matrix-cpu/mpi_rank_hosts \
            | sort -t, -k1,1n > "$RESULT_ROOT/mapping/p${p}_t${threads}.csv"
        for communication in allgather halo; do
            suffix=""
            [[ "$communication" == halo ]] && suffix="_halo"
            folder="$RESULT_ROOT/mpi_kokkos$suffix/OpenMP/$GRAPH_NAME/p${p}_t${threads}"
            OMP_NUM_THREADS="$threads" PAGERANK_KOKKOS_THREADS="$threads" \
                run_or_reuse "$folder" \
                mpiexec -x LD_LIBRARY_PATH -x OMP_NUM_THREADS -x PAGERANK_KOKKOS_THREADS \
                --map-by "$mapping" --bind-to none -n "$p" \
                python3 scripts/mpi_affinity_exec.py "$threads" \
                ./build-vanda-matrix-cpu/pagerank_mpi_kokkos \
                --communication="$communication"
        done
    done
    for communication in allgather halo; do
        validate_result scripts/validate_mpi_device.py mpi_kokkos OpenMP "$communication" \
            --threads "$threads" --processes "${processes[@]}"
    done
done

if [[ "${PAGERANK_DEFER_VALIDATION:-0}" == 1 ]]; then
    printf '%s\n' "$PBS_JOBID" > "$RESULT_ROOT/measurement_complete.txt"
    exit 0
fi

find "$RESULT_ROOT" -name ranks.csv -delete
mkdir -p "$DESTINATION"
cp -a "$RESULT_ROOT/." "$DESTINATION/"
printf '%s\n' "$PBS_JOBID" > "$DESTINATION/complete.txt"

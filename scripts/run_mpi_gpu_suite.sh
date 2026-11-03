#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CUDA_BUILD_DIR="${CUDA_BUILD_DIR:-build-vanda-matrix-cuda}"
KOKKOS_BUILD_DIR="${KOKKOS_BUILD_DIR:-build-vanda-matrix-kokkos-cuda}"
read -r -a process_counts <<< "${PAGERANK_GPU_PROCESS_COUNTS:-1 2 4 8}"
read -r -a hybrid_threads <<< "${PAGERANK_GPU_HYBRID_THREADS:-1 2 4 8}"
export PAGERANK_HYBRID_MAX_TOTAL_THREADS=64
export PAGERANK_PROCESS_COUNTS="${process_counts[*]}"
export OMP_NUM_THREADS=1 OMP_DYNAMIC=FALSE OMP_PROC_BIND=spread OMP_PLACES=cores
mpi_host_options=()
if [[ -n "${PAGERANK_GPU_HOSTFILE:-}" ]]; then
    mpi_host_options=(--hostfile "$PAGERANK_GPU_HOSTFILE")
fi

run_on_gpu_nodes() {
    local processes="$1"
    local threads="$2"
    shift 2
    local mapping="ppr:1:node"
    if (( threads == 1 )); then
        mpiexec "${mpi_host_options[@]}" -x LD_LIBRARY_PATH --map-by "$mapping" --bind-to core -n "$processes" "$@"
    else
        mpiexec "${mpi_host_options[@]}" -x LD_LIBRARY_PATH --map-by "$mapping" --bind-to none -n "$processes" \
            python3 scripts/mpi_affinity_exec.py "$threads" "$@"
    fi
}

mkdir -p "$PAGERANK_RESULTS_ROOT/mapping"
for processes in "${process_counts[@]}"; do
    printf 'Matched GPU-node layout: %s nodes, %s ranks, one rank and one GPU per node\n' \
        "$processes" "$processes"
    run_on_gpu_nodes "$processes" 1 "$CUDA_BUILD_DIR/mpi_rank_hosts" \
        | sort -t, -k1,1n > "$PAGERANK_RESULTS_ROOT/mapping/p${processes}.csv"
    for threads in "${hybrid_threads[@]}"; do
        run_on_gpu_nodes "$processes" "$threads" "$CUDA_BUILD_DIR/mpi_rank_hosts" \
            | sort -t, -k1,1n > "$PAGERANK_RESULTS_ROOT/mapping/hybrid_p${processes}_t${threads}.csv"
    done
    for communication in allgather halo; do
        run_on_gpu_nodes "$processes" 1 "$CUDA_BUILD_DIR/pagerank_mpi" \
            --communication="$communication"
        for threads in "${hybrid_threads[@]}"; do
            PAGERANK_HYBRID_THREADS="$threads" \
                run_on_gpu_nodes "$processes" "$threads" "$CUDA_BUILD_DIR/pagerank_hybrid" \
                --communication="$communication"
        done
        run_on_gpu_nodes "$processes" 1 "$CUDA_BUILD_DIR/pagerank_mpi_cuda" \
            --communication="$communication"
        run_on_gpu_nodes "$processes" 1 "$KOKKOS_BUILD_DIR/pagerank_mpi_kokkos" \
            --communication="$communication"
    done
done

if [[ "${PAGERANK_SKIP_VALIDATION:-0}" == 1 ]]; then exit 0; fi

for communication in allgather halo; do
    python3 scripts/validate_mpi.py "$communication" --processes "${process_counts[@]}"
    configs=()
    for processes in "${process_counts[@]}"; do
        for threads in "${hybrid_threads[@]}"; do configs+=("${processes}:${threads}"); done
    done
    export PAGERANK_HYBRID_CONFIGS="${configs[*]}"
    python3 scripts/validate_hybrid.py "$communication" --processes "${process_counts[@]}"
    python3 scripts/validate_mpi_device.py mpi_cuda Cuda "$communication" \
        --processes "${process_counts[@]}"
    python3 scripts/validate_mpi_device.py mpi_kokkos Cuda "$communication" \
        --processes "${process_counts[@]}"
done

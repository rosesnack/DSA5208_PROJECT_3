#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BUILD_DIR="${LOCAL_BUILD_DIR:-/private/tmp/proj3-kokkos45-project-build2}"
MPIEXEC="${LOCAL_MPIEXEC:-/private/tmp/proj3-kokkos/bin/mpiexec}"
export DYLD_LIBRARY_PATH="${LOCAL_MPI_LIBRARY_DIR:-/private/tmp/proj3-kokkos/lib}${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
export FI_PROVIDER=sockets
export PAGERANK_DATASET_MANIFEST="${PAGERANK_DATASET_MANIFEST:-$ROOT/data/local_matrix_20261031/manifests/fixed_graphs.tsv}"
export PAGERANK_RESULTS_ROOT="${PAGERANK_RESULTS_ROOT:-$ROOT/results/updated_local_macos/20261031_full_cpu_kokkos45}"
export PAGERANK_ENVIRONMENT=local-macos-clang23-kokkos4501-release
export PAGERANK_REPEATS=5 PAGERANK_WARMUPS=1
export PAGERANK_OPENMP_THREADS='1 2 4 8'
export PAGERANK_HYBRID_MAX_TOTAL_THREADS=8
export OMP_DYNAMIC=FALSE OMP_PROC_BIND=FALSE
mkdir -p "$PAGERANK_RESULTS_ROOT"
{
    date -u
    uname -a
    system_profiler SPHardwareDataType | grep -E 'Chip:|Total Number of Cores:|Memory:'
    grep -E '^(CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER|Kokkos_DIR):' "$BUILD_DIR/CMakeCache.txt"
    compiler=$(sed -n 's/^CMAKE_CXX_COMPILER:STRING=//p' "$BUILD_DIR/CMakeCache.txt")
    "$compiler" --version | head -n 1
    "$(dirname "$MPIEXEC")/mpichversion" | head -n 2
    git -C third_party/kokkos describe --tags --exact-match
    printf 'Warmups=%s Repeats=%s OpenMP threads=%s MPI ranks=1,2,4,8 FI_PROVIDER=%s\n' \
        "$PAGERANK_WARMUPS" "$PAGERANK_REPEATS" "$PAGERANK_OPENMP_THREADS" "$FI_PROVIDER"
} > "$PAGERANK_RESULTS_ROOT/environment.txt"

if [[ ! -f "$PAGERANK_RESULTS_ROOT/serial.complete" ]]; then
    "$BUILD_DIR/pagerank_serial"
    python3 scripts/validate_serial.py
    printf 'serial complete\n' > "$PAGERANK_RESULTS_ROOT/serial.complete"
fi

if [[ ! -f "$PAGERANK_RESULTS_ROOT/openmp.complete" ]]; then
    "$BUILD_DIR/pagerank_openmp"
    python3 scripts/validate_openmp.py
    printf 'openmp complete\n' > "$PAGERANK_RESULTS_ROOT/openmp.complete"
fi

for threads in 1 2 4 8; do
    KOKKOS_ROOT="$PAGERANK_RESULTS_ROOT/kokkos_threads_${threads}"
    mkdir -p "$KOKKOS_ROOT"
    ln -sfn ../serial "$KOKKOS_ROOT/serial"
    printf 'Requested OMP_NUM_THREADS=%s\nKokkos tag=4.5.01\n' "$threads" > "$KOKKOS_ROOT/environment.txt"
    if [[ ! -f "$KOKKOS_ROOT/complete.txt" ]]; then
        PAGERANK_RESULTS_ROOT="$KOKKOS_ROOT" OMP_NUM_THREADS="$threads" \
            "$BUILD_DIR/pagerank_kokkos"
        PAGERANK_RESULTS_ROOT="$KOKKOS_ROOT" python3 scripts/validate_gpu.py kokkos OpenMP
        printf 'kokkos OpenMP T=%s complete\n' "$threads" > "$KOKKOS_ROOT/complete.txt"
    fi
done

if [[ ! -f "$PAGERANK_RESULTS_ROOT/mpi.complete" ]]; then
    for processes in 1 2 4 8; do
        for communication in allgather halo; do
            "$MPIEXEC" -n "$processes" "$BUILD_DIR/pagerank_mpi" \
                --communication="$communication"
            OMP_NUM_THREADS=1 "$MPIEXEC" -n "$processes" "$BUILD_DIR/pagerank_mpi_kokkos" \
                --communication="$communication"
        done
    done
    for communication in allgather halo; do
        python3 scripts/validate_mpi.py "$communication" --processes 1 2 4 8
        python3 scripts/validate_mpi_device.py mpi_kokkos OpenMP "$communication" \
            --processes 1 2 4 8
    done
    printf 'mpi and mpi_kokkos complete\n' > "$PAGERANK_RESULTS_ROOT/mpi.complete"
fi

if [[ ! -f "$PAGERANK_RESULTS_ROOT/hybrid.complete" ]]; then
    for processes in 1 2 4 8; do
        case "$processes" in
            1) export PAGERANK_HYBRID_THREADS='1 2 4 8' ;;
            2) export PAGERANK_HYBRID_THREADS='1 2 4' ;;
            4) export PAGERANK_HYBRID_THREADS='1 2' ;;
            8) export PAGERANK_HYBRID_THREADS='1' ;;
        esac
        for communication in allgather halo; do
            "$MPIEXEC" -n "$processes" "$BUILD_DIR/pagerank_hybrid" \
                --communication="$communication"
        done
    done
    export PAGERANK_HYBRID_THREADS='1 2 4 8'
    for communication in allgather halo; do
        python3 scripts/validate_hybrid.py "$communication" --processes 1 2 4 8
    done
    printf 'hybrid complete\n' > "$PAGERANK_RESULTS_ROOT/hybrid.complete"
fi
printf 'Local 42-graph CPU matrix complete: %s\n' "$PAGERANK_RESULTS_ROOT"

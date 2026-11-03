#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BUILD_DIR="${LOCAL_BUILD_DIR:-/private/tmp/proj3-kokkos45-project-build2}"
MPIEXEC="${LOCAL_MPIEXEC:-/private/tmp/proj3-kokkos/bin/mpiexec}"
export DYLD_LIBRARY_PATH="${LOCAL_MPI_LIBRARY_DIR:-/private/tmp/proj3-kokkos/lib}${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
export FI_PROVIDER=sockets
export PAGERANK_DATASET_MANIFEST="$ROOT/data/local_weak_20261031/manifests/weak_scaling.tsv"
export PAGERANK_RESULTS_ROOT="$ROOT/results/updated_local_macos/20261031_weak_cpu_kokkos45"
export PAGERANK_ENVIRONMENT=local-macos-clang23-kokkos4501-release
export PAGERANK_REPEATS=5 PAGERANK_WARMUPS=1
export PAGERANK_OPENMP_THREADS='1 2 4 8'
export PAGERANK_HYBRID_MAX_TOTAL_THREADS=8
export OMP_DYNAMIC=FALSE OMP_PROC_BIND=FALSE
mkdir -p "$PAGERANK_RESULTS_ROOT"
cp results/updated_local_macos/20261031_full_cpu_kokkos45/environment.txt \
    "$PAGERANK_RESULTS_ROOT/environment.txt"

"$BUILD_DIR/pagerank_serial"
python3 scripts/validate_serial.py
printf 'serial complete\n' > "$PAGERANK_RESULTS_ROOT/serial.complete"
"$BUILD_DIR/pagerank_openmp"
python3 scripts/validate_openmp.py
printf 'openmp complete\n' > "$PAGERANK_RESULTS_ROOT/openmp.complete"

for threads in 1 2 4 8; do
    KOKKOS_ROOT="$PAGERANK_RESULTS_ROOT/kokkos_threads_${threads}"
    mkdir -p "$KOKKOS_ROOT"
    ln -sfn ../serial "$KOKKOS_ROOT/serial"
    printf 'Requested OMP_NUM_THREADS=%s\nKokkos tag=4.5.01\n' "$threads" > "$KOKKOS_ROOT/environment.txt"
    PAGERANK_RESULTS_ROOT="$KOKKOS_ROOT" OMP_NUM_THREADS="$threads" \
        "$BUILD_DIR/pagerank_kokkos"
    PAGERANK_RESULTS_ROOT="$KOKKOS_ROOT" python3 scripts/validate_gpu.py kokkos OpenMP
    printf 'kokkos OpenMP T=%s complete\n' "$threads" > "$KOKKOS_ROOT/complete.txt"
done

WEAK_MANIFEST="$PAGERANK_DATASET_MANIFEST"
for processes in 1 2 4 8; do
    export PAGERANK_DATASET_MANIFEST="$ROOT/data/local_weak_20261031/manifests/weak_p$(printf '%03d' "$processes").tsv"
    for mode in allgather halo; do
        "$MPIEXEC" -n "$processes" "$BUILD_DIR/pagerank_mpi" --communication="$mode"
        OMP_NUM_THREADS=1 "$MPIEXEC" -n "$processes" "$BUILD_DIR/pagerank_mpi_kokkos" \
            --communication="$mode"
        case "$processes" in
            1) hybrid_threads='1 2 4 8' ;;
            2) hybrid_threads='1 2 4' ;;
            4) hybrid_threads='1 2' ;;
            8) hybrid_threads='1' ;;
        esac
        PAGERANK_HYBRID_THREADS="$hybrid_threads" "$MPIEXEC" -n "$processes" \
            "$BUILD_DIR/pagerank_hybrid" --communication="$mode"
    done
done
export PAGERANK_DATASET_MANIFEST="$WEAK_MANIFEST"
python3 scripts/validate_weak_matrix.py mpi --processes 1 2 4 8
python3 scripts/validate_weak_matrix.py mpi_kokkos --backend OpenMP --processes 1 2 4 8
for threads in 1 2 4 8; do
    case "$threads" in
        1) process_counts=(1 2 4 8) ;;
        2) process_counts=(1 2 4) ;;
        4) process_counts=(1 2) ;;
        8) process_counts=(1) ;;
    esac
    python3 scripts/validate_weak_matrix.py hybrid --threads "$threads" \
        --processes "${process_counts[@]}"
done
printf 'weak matrix complete\n' > "$PAGERANK_RESULTS_ROOT/complete.txt"

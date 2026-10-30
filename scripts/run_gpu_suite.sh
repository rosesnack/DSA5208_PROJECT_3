#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CUDA_BUILD_DIR="${CUDA_BUILD_DIR:-build-cuda}"
KOKKOS_BUILD_DIR="${KOKKOS_BUILD_DIR:-build-kokkos-cuda}"
KOKKOS_BACKEND="${KOKKOS_BACKEND:-Cuda}"
PAGERANK_ENVIRONMENT="${PAGERANK_ENVIRONMENT:-google-cloud-gpu}"
PAGERANK_RUN_ID="${PAGERANK_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
PAGERANK_RESULTS_ROOT="${PAGERANK_RESULTS_ROOT:-results/${PAGERANK_ENVIRONMENT}/${PAGERANK_RUN_ID}}"
PAGERANK_REPEATS="${PAGERANK_REPEATS:-5}"
PAGERANK_WARMUPS="${PAGERANK_WARMUPS:-1}"
export PAGERANK_ENVIRONMENT PAGERANK_RESULTS_ROOT PAGERANK_REPEATS PAGERANK_WARMUPS

CUDA_BIN="${CUDA_BUILD_DIR}/pagerank_cuda"
KOKKOS_BIN="${KOKKOS_BUILD_DIR}/pagerank_kokkos"
SERIAL_BIN="${CUDA_BUILD_DIR}/pagerank_serial"
for executable in "$SERIAL_BIN" "$CUDA_BIN" "$KOKKOS_BIN"; do
    if [[ ! -x "$executable" ]]; then
        echo "Missing executable: $executable. Build all targets in both Release build directories first." >&2
        exit 2
    fi
done

mkdir -p "$PAGERANK_RESULTS_ROOT"
{
    printf 'Environment: %s\nRun ID: %s\nHost: %s\n' \
        "$PAGERANK_ENVIRONMENT" "$PAGERANK_RUN_ID" "$(hostname)"
    uname -a
    lscpu | grep -E 'Model name|Socket\(s\)|Core\(s\) per socket|CPU\(s\)'
    ${CXX:-c++} --version | head -n 1
    nvcc --version | tail -n 4
    cmake --version | head -n 1
    grep -E '^(CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER|CMAKE_CUDA_COMPILER):' build-cuda/CMakeCache.txt
    grep -E '^(CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER):' build-kokkos-cuda/CMakeCache.txt
    module list 2>&1
    nvidia-smi
} > "$PAGERANK_RESULTS_ROOT/environment.txt"

"$SERIAL_BIN"
"$CUDA_BIN"
python3 scripts/validate_gpu.py cuda

"$KOKKOS_BIN"
python3 scripts/validate_gpu.py kokkos "$KOKKOS_BACKEND"

printf 'GPU suite complete: %s\n' "$PAGERANK_RESULTS_ROOT"

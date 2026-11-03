#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CUDA_ARCH="${PAGERANK_CUDA_ARCH:?Set the NVIDIA CUDA compute capability without a dot, e.g. 86}"
KOKKOS_ARCH="${PAGERANK_KOKKOS_ARCH:?Set the matching Kokkos architecture, e.g. AMPERE86}"
BUILD_JOBS="${PAGERANK_BUILD_JOBS:-8}"
CUDA_BUILD_DIR="${CUDA_BUILD_DIR:-build-cloud-cuda}"
KOKKOS_BUILD_DIR="${KOKKOS_BUILD_DIR:-build-cloud-kokkos-cuda}"
KOKKOS_SOURCE_BUILD="${KOKKOS_SOURCE_BUILD:-build-cloud-kokkos-source}"
KOKKOS_INSTALL="${KOKKOS_INSTALL:-$ROOT/kokkos-install-cloud-cuda}"
test -x third_party/kokkos/bin/nvcc_wrapper

cmake -S third_party/kokkos -B "$KOKKOS_SOURCE_BUILD" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_COMPILER="$ROOT/third_party/kokkos/bin/nvcc_wrapper" \
    -DKokkos_ENABLE_CUDA=ON "-DKokkos_ARCH_${KOKKOS_ARCH}=ON" \
    -DCMAKE_INSTALL_PREFIX="$KOKKOS_INSTALL"
cmake --build "$KOKKOS_SOURCE_BUILD" --parallel "$BUILD_JOBS"
cmake --install "$KOKKOS_SOURCE_BUILD"

cmake -S . -B "$CUDA_BUILD_DIR" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_COMPILER=mpicxx -DBUILD_CUDA=ON -DBUILD_MPI_CUDA=ON \
    -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCH"
cmake --build "$CUDA_BUILD_DIR" --parallel "$BUILD_JOBS"
mpicxx -O3 -DNDEBUG scripts/mpi_rank_hosts.cpp -o "$CUDA_BUILD_DIR/mpi_rank_hosts"

cmake -S . -B "$KOKKOS_BUILD_DIR" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_COMPILER="$ROOT/third_party/kokkos/bin/nvcc_wrapper" \
    -DBUILD_KOKKOS=ON -DBUILD_MPI_KOKKOS=ON \
    -DCMAKE_PREFIX_PATH="$KOKKOS_INSTALL"
cmake --build "$KOKKOS_BUILD_DIR" --parallel "$BUILD_JOBS"

{
    printf 'CUDA architecture: %s\nKokkos architecture: %s\n' "$CUDA_ARCH" "$KOKKOS_ARCH"
    mpicxx --version | head -n 1
    nvcc --version | tail -n 4
    cmake --version | head -n 1
    cat third_party/kokkos_commit.txt
    grep -E '^(CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER|CMAKE_CUDA_COMPILER):' \
        "$CUDA_BUILD_DIR/CMakeCache.txt"
    grep -E '^(CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER):' \
        "$KOKKOS_BUILD_DIR/CMakeCache.txt"
} > "$KOKKOS_BUILD_DIR/cloud_build_environment.txt"

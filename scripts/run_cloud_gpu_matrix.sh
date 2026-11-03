#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PAGERANK_GPU_HOSTFILE="${PAGERANK_GPU_HOSTFILE:?Set a hostfile with one GPU node per line}"
export PAGERANK_DATASET_MANIFEST="${PAGERANK_DATASET_MANIFEST:?Set the shared 45-graph manifest}"
export PAGERANK_RESULTS_ROOT="${PAGERANK_RESULTS_ROOT:?Set a shared output directory}"
export PAGERANK_GPU_PROCESS_COUNTS='1 2 4 8'
export PAGERANK_GPU_HYBRID_THREADS='1 2 4 8'
export PAGERANK_OPENMP_THREADS='1 2 4 8'
export PAGERANK_RUN_OPENMP_ABLATION=1
export PAGERANK_ENVIRONMENT="${PAGERANK_ENVIRONMENT:-google-cloud-gpu-release}"
export PAGERANK_RUN_ID="${PAGERANK_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
export PAGERANK_REPEATS=5 PAGERANK_WARMUPS=1
export CUDA_BUILD_DIR="${CUDA_BUILD_DIR:-build-cloud-cuda}"
export KOKKOS_BUILD_DIR="${KOKKOS_BUILD_DIR:-build-cloud-kokkos-cuda}"
export KOKKOS_BACKEND=Cuda

test "$(sort -u "$PAGERANK_GPU_HOSTFILE" | wc -l | tr -d ' ')" -eq 8
test "$(wc -l < "$PAGERANK_DATASET_MANIFEST" | tr -d ' ')" -eq 45
mkdir -p "$PAGERANK_RESULTS_ROOT"
{
    printf 'Run ID: %s\nEnvironment: %s\n' "$PAGERANK_RUN_ID" "$PAGERANK_ENVIRONMENT"
    printf 'GPU hostfile:\n'
    cat "$PAGERANK_GPU_HOSTFILE"
    printf 'Dataset count: %s\n' "$(wc -l < "$PAGERANK_DATASET_MANIFEST" | tr -d ' ')"
    mpiexec --version | head -n 1
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
} > "$PAGERANK_RESULTS_ROOT/cloud_layout.txt"

bash scripts/run_gpu_suite.sh
bash scripts/run_mpi_gpu_suite.sh
printf '%s\n' "$PAGERANK_RUN_ID" > "$PAGERANK_RESULTS_ROOT/complete.txt"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "${PBS_JOBID:-}" && "${ALLOW_UNSCHEDULED_RUN:-0}" != "1" ]]; then
    echo "Run this suite inside a PBS allocation; set ALLOW_UNSCHEDULED_RUN=1 only for a controlled local run." >&2
    exit 2
fi

CPU_BUILD_DIR="${CPU_BUILD_DIR:-build}"
PAGERANK_ENVIRONMENT="${PAGERANK_ENVIRONMENT:-nus-hpc}"
PAGERANK_RUN_ID="${PAGERANK_RUN_ID:-${PBS_JOBID:-local-$(date -u +%Y%m%dT%H%M%SZ)}}"
PAGERANK_RESULTS_ROOT="${PAGERANK_RESULTS_ROOT:-results/runs/${PAGERANK_ENVIRONMENT}/${PAGERANK_RUN_ID}}"
PAGERANK_REPEATS="${PAGERANK_REPEATS:-5}"
PAGERANK_WARMUPS="${PAGERANK_WARMUPS:-1}"
read -r -a process_counts <<< "${PAGERANK_PROCESS_COUNTS:-1 2 4 8}"
export PAGERANK_ENVIRONMENT PAGERANK_RESULTS_ROOT PAGERANK_REPEATS PAGERANK_WARMUPS

if [[ ! -x ${CPU_BUILD_DIR}/pagerank_serial ]]; then
    echo "Missing ${CPU_BUILD_DIR}/pagerank_serial; configure and build the Release targets first." >&2
    exit 2
fi

printf 'Environment: %s\nRun ID: %s\nResults: %s\n' \
    "$PAGERANK_ENVIRONMENT" "$PAGERANK_RUN_ID" "$PAGERANK_RESULTS_ROOT"
mkdir -p "$PAGERANK_RESULTS_ROOT"
{
    printf 'PBS job: %s\nHost: %s\nMPI process counts: %s\n' \
        "${PBS_JOBID:-local}" "$(hostname)" "${process_counts[*]}"
    uname -a
    case "$(uname -s)" in
        Darwin)
            sysctl -n machdep.cpu.brand_string
            sysctl -n hw.physicalcpu hw.logicalcpu
            ;;
        *)
            lscpu | grep -E 'Model name|Socket\(s\)|Core\(s\) per socket|CPU\(s\)'
            module list 2>&1
            ;;
    esac
    ${CXX:-c++} --version | head -n 1
    mpicxx -show
    mpiexec --version | head -n 2
    cmake --version | head -n 1
    grep -E '^(CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER):' ${CPU_BUILD_DIR}/CMakeCache.txt
} | tee "$PAGERANK_RESULTS_ROOT/environment.txt"

./${CPU_BUILD_DIR}/pagerank_serial
./${CPU_BUILD_DIR}/pagerank_openmp

for processes in "${process_counts[@]}"; do
    mpiexec -n "$processes" ./${CPU_BUILD_DIR}/pagerank_mpi --communication=allgather
    mpiexec -n "$processes" ./${CPU_BUILD_DIR}/pagerank_mpi --communication=halo
done

for processes in "${process_counts[@]}"; do
    mpiexec -n "$processes" ./${CPU_BUILD_DIR}/pagerank_hybrid --communication=allgather
    mpiexec -n "$processes" ./${CPU_BUILD_DIR}/pagerank_hybrid --communication=halo
done

if [[ "${PAGERANK_DEFER_VALIDATION:-0}" != 1 ]]; then
python3 scripts/validate_serial.py
python3 scripts/validate_openmp.py
python3 scripts/validate_mpi.py allgather --processes "${process_counts[@]}"
python3 scripts/validate_mpi.py halo --processes "${process_counts[@]}"
python3 scripts/validate_hybrid.py --processes "${process_counts[@]}"
python3 scripts/validate_hybrid.py halo --processes "${process_counts[@]}"

fi

printf 'CPU suite complete: %s\n' "$PAGERANK_RESULTS_ROOT"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DATA_ROOT="${DATA_ROOT:?Set DATA_ROOT}"
RUN_ID="${RUN_ID:?Set RUN_ID}"
GRAPH_NAME="${GRAPH_NAME:?Set GRAPH_NAME}"
RESULT_ROOT="$DATA_ROOT/results/kokkos_cpu_512/$GRAPH_NAME"
DESTINATION="$ROOT/results/updated_vanda_scaling/$RUN_ID/kokkos_cpu_512/$GRAPH_NAME"
MANIFEST="$DATA_ROOT/manifests/kokkos_512_${GRAPH_NAME}_${PBS_JOBID}.tsv"
export PAGERANK_ENVIRONMENT=vanda-gcc13-release PAGERANK_RUN_ID="$RUN_ID"
export PAGERANK_REPEATS=5 PAGERANK_WARMUPS=1
export PAGERANK_RESULTS_ROOT="$RESULT_ROOT" PAGERANK_DATASET_MANIFEST="$MANIFEST"
export OMP_DYNAMIC=FALSE OMP_PROC_BIND=spread OMP_PLACES=cores
mkdir -p "$RESULT_ROOT/serial" "$RESULT_ROOT/mapping"
python3 scripts/select_graph_manifest.py "$DATA_ROOT/manifests/strong_scaling.tsv" \
    "$GRAPH_NAME" "$MANIFEST"
cp -al "$DATA_ROOT/results/serial_grid/$GRAPH_NAME/serial/$GRAPH_NAME" "$RESULT_ROOT/serial/"
python3 scripts/validate_serial.py
{
    printf 'PBS job: %s\nGraph: %s\nLayout: 8 nodes, 16 ranks/node, 4 threads/rank, 512 CPU cores\n' \
        "$PBS_JOBID" "$GRAPH_NAME"
    uname -a
    lscpu | grep -E 'Model name|Socket\(s\)|Core\(s\) per socket|CPU\(s\)'
    mpicxx --showme:version
    grep -E '^(CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER):' build-vanda-matrix-cpu/CMakeCache.txt
    sort -u "$PBS_NODEFILE"
} > "$RESULT_ROOT/environment.txt"

for communication in allgather halo; do
    OMP_NUM_THREADS=4 PAGERANK_KOKKOS_THREADS=4 \
        mpiexec -x LD_LIBRARY_PATH -x OMP_NUM_THREADS -x PAGERANK_KOKKOS_THREADS \
        --map-by ppr:16:node --bind-to none -n 128 \
        python3 scripts/mpi_affinity_exec.py 4 \
        ./build-vanda-matrix-cpu/mpi_rank_hosts \
        | sort -t, -k1,1n > "$RESULT_ROOT/mapping/${communication}_p128_t4.csv"
    OMP_NUM_THREADS=4 PAGERANK_KOKKOS_THREADS=4 \
        mpiexec -x LD_LIBRARY_PATH -x OMP_NUM_THREADS -x PAGERANK_KOKKOS_THREADS \
        --map-by ppr:16:node --bind-to none -n 128 \
        python3 scripts/mpi_affinity_exec.py 4 \
        ./build-vanda-matrix-cpu/pagerank_mpi_kokkos \
        --communication="$communication"
    python3 scripts/validate_mpi_device.py mpi_kokkos OpenMP "$communication" \
        --threads 4 --processes 128
done

find "$RESULT_ROOT" -name ranks.csv -delete
mkdir -p "$DESTINATION"
cp -a "$RESULT_ROOT/." "$DESTINATION/"
printf '%s\n' "$PBS_JOBID" > "$DESTINATION/complete.txt"

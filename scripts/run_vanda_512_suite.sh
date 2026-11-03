#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DATA_ROOT="${DATA_ROOT:?Set DATA_ROOT}"
RUN_ID="${RUN_ID:?Set RUN_ID}"
GRAPH_NAME="${GRAPH_NAME:-}"
export PAGERANK_REPEATS=5 PAGERANK_WARMUPS=1
export PAGERANK_ENVIRONMENT=vanda-gcc13-release PAGERANK_RUN_ID="$RUN_ID"
export PAGERANK_HYBRID_MAX_TOTAL_THREADS=512
export OMP_DYNAMIC=FALSE OMP_PROC_BIND=spread OMP_PLACES=cores

run_layout() {
    local processes="$1" elements="$2"
    shift 2
    local mapping="ppr:$((processes / 8)):node"
    if (( elements == 1 )); then
        mpiexec -x LD_LIBRARY_PATH --map-by "$mapping" \
            --bind-to core -n "$processes" "$@"
    else
        mpiexec -x LD_LIBRARY_PATH --map-by "$mapping" \
            --bind-to none -n "$processes" \
            python3 scripts/mpi_affinity_exec.py "$elements" "$@"
    fi
}

map_layout() {
    local processes="$1" elements="$2" destination="$3"
    run_layout "$processes" "$elements" ./build-vanda-matrix-cpu/mpi_rank_hosts \
        | sort -t, -k1,1n > "$destination"
}

if [[ -n "$GRAPH_NAME" ]]; then
    NODE_ROOT="$DATA_ROOT/results/strong/$GRAPH_NAME/nodes8_p512"
    mkdir -p "$NODE_ROOT/mapping" "$NODE_ROOT/serial"
    manifest="$DATA_ROOT/manifests/strong_${GRAPH_NAME}_${PBS_JOBID}.tsv"
    python3 scripts/select_graph_manifest.py "$DATA_ROOT/manifests/strong_scaling.tsv" \
        "$GRAPH_NAME" "$manifest"
    export PAGERANK_DATASET_MANIFEST="$manifest" PAGERANK_RESULTS_ROOT="$NODE_ROOT"
    cp -al "$DATA_ROOT/results/serial_grid/$GRAPH_NAME/serial/$GRAPH_NAME" "$NODE_ROOT/serial/"
    python3 scripts/validate_serial.py
    for mode in allgather halo; do
        map_layout 512 1 "$NODE_ROOT/mapping/${mode}_p512.csv"
        run_layout 512 1 ./build-vanda-matrix-cpu/pagerank_mpi --communication="$mode"
        OMP_NUM_THREADS=1 run_layout 512 1 ./build-vanda-matrix-cpu/pagerank_mpi_kokkos \
            --communication="$mode"
        map_layout 512 1 "$NODE_ROOT/mapping/hybrid_${mode}_p512_t1.csv"
        PAGERANK_HYBRID_THREADS=1 run_layout 512 1 ./build-vanda-matrix-cpu/pagerank_hybrid \
            --communication="$mode"
        map_layout 128 4 "$NODE_ROOT/mapping/hybrid_${mode}_p128_t4.csv"
        PAGERANK_HYBRID_THREADS=4 run_layout 128 4 ./build-vanda-matrix-cpu/pagerank_hybrid \
            --communication="$mode"
    done
    for mode in allgather halo; do
        python3 scripts/validate_mpi.py "$mode" --processes 512
        python3 scripts/validate_mpi_device.py mpi_kokkos OpenMP "$mode" --processes 512
        PAGERANK_HYBRID_CONFIGS='512:1 128:4' \
            python3 scripts/validate_hybrid.py "$mode" --processes 128 512
    done
    find "$NODE_ROOT" -name ranks.csv -delete
    destination="$ROOT/results/updated_vanda_scaling/$RUN_ID/strong/$GRAPH_NAME"
    mkdir -p "$destination"
    cp -a "$NODE_ROOT" "$destination/"
    printf '%s\n' "$PBS_JOBID" > "$destination/nodes8_p512/complete.txt"
else
    family="${WEAK_FAMILY:?Set WEAK_FAMILY to uniform, hub, or controlled}"
    WEAK_ROOT="$DATA_ROOT/results/weak"
    mkdir -p "$WEAK_ROOT/mapping"
    export PAGERANK_RESULTS_ROOT="$WEAK_ROOT"
    manifest_512="$DATA_ROOT/manifests/weak_512_${family}_${PBS_JOBID}.tsv"
    manifest_128="$DATA_ROOT/manifests/weak_128_${family}_${PBS_JOBID}.tsv"
    python3 scripts/select_graph_manifest.py "$DATA_ROOT/manifests/weak_p512.tsv" \
        "weak_${family}_p512" "$manifest_512"
    python3 scripts/select_graph_manifest.py "$DATA_ROOT/manifests/weak_p128.tsv" \
        "weak_${family}_p128" "$manifest_128"
    for mode in allgather halo; do
        export PAGERANK_DATASET_MANIFEST="$manifest_512"
        map_layout 512 1 "$WEAK_ROOT/mapping/${family}_${mode}_p512.csv"
        run_layout 512 1 ./build-vanda-matrix-cpu/pagerank_mpi --communication="$mode"
        OMP_NUM_THREADS=1 run_layout 512 1 ./build-vanda-matrix-cpu/pagerank_mpi_kokkos \
            --communication="$mode"
        export PAGERANK_DATASET_MANIFEST="$manifest_128"
        map_layout 128 4 "$WEAK_ROOT/mapping/${family}_hybrid_${mode}_p128_t4.csv"
        PAGERANK_HYBRID_THREADS=4 run_layout 128 4 ./build-vanda-matrix-cpu/pagerank_hybrid \
            --communication="$mode"
    done
    export PAGERANK_DATASET_MANIFEST="$manifest_512"
    python3 scripts/validate_weak_matrix.py mpi --processes 512 \
        --families "$family" --suffix "_extension_p512_${family}"
    python3 scripts/validate_weak_matrix.py mpi_kokkos --backend OpenMP \
        --processes 512 --families "$family" --suffix "_extension_p512_${family}"
    export PAGERANK_DATASET_MANIFEST="$manifest_128"
    python3 scripts/validate_weak_matrix.py hybrid --threads 4 --processes 128 \
        --families "$family" --suffix "_extension_p128_${family}"
    destination="$ROOT/results/updated_vanda_scaling/$RUN_ID/weak_512/$family"
    mkdir -p "$destination/mapping"
    cp "$DATA_ROOT/results/weak_512/$family/environment.txt" "$destination/environment.txt"
    cp "$WEAK_ROOT/mapping/${family}_"* "$destination/mapping/"
    cp -a "$WEAK_ROOT"/weak_*extension*"_${family}" "$destination/"
    for implementation in mpi mpi_halo mpi_kokkos/OpenMP mpi_kokkos_halo/OpenMP; do
        mkdir -p "$destination/$implementation"
        cp -a "$WEAK_ROOT/$implementation/weak_${family}_p512" "$destination/$implementation/"
    done
    for implementation in hybrid hybrid_halo; do
        mkdir -p "$destination/$implementation"
        cp -a "$WEAK_ROOT/$implementation/weak_${family}_p128" "$destination/$implementation/"
    done
    find "$destination" -name ranks.csv -delete
    printf '%s\n' "$PBS_JOBID" > "$destination/complete.txt"
fi

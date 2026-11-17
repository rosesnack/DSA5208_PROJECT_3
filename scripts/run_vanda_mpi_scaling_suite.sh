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
DATA_ROOT="${DATA_ROOT:?Set DATA_ROOT to the generated shared graph directory}"
RUN_ID="${RUN_ID:?Set RUN_ID when submitting the experiment suite}"
PAGERANK_REPEATS=5
PAGERANK_WARMUPS=1
RANKS_PER_NODE=(1 2 4 8 16 32)
PROCESS_COUNTS=(1 2 4 8 16 32 64 128 256)
read -r -a NODE_COUNTS <<< "${PAGERANK_NODE_COUNTS:-1 2 4 8}"
RUN_STRONG="${PAGERANK_RUN_STRONG:-1}"
RUN_WEAK="${PAGERANK_RUN_WEAK:-1}"
GRAPH_NAME="${GRAPH_NAME:-}"
RESUME_EXISTING="${PAGERANK_RESUME_EXISTING:-0}"
export PAGERANK_REPEATS PAGERANK_WARMUPS
export PAGERANK_HYBRID_MAX_TOTAL_THREADS=256

allocated_nodes=$(sort -u "$PBS_NODEFILE" | wc -l | tr -d ' ')
for nodes in "${NODE_COUNTS[@]}"; do test "$allocated_nodes" -ge "$nodes"; done
mkdir -p "$DATA_ROOT/results/weak/mapping"

run_on_layout() {
    local nodes="$1"
    local processes="$2"
    local processing_elements="$3"
    shift 3
    local ranks_per_node=$((processes / nodes))
    local mapping="ppr:${ranks_per_node}:node"
    if (( processing_elements == 1 )); then
        mpiexec -x LD_LIBRARY_PATH --map-by "$mapping" --bind-to core \
            -n "$processes" "$@"
    else
        mpiexec -x LD_LIBRARY_PATH --map-by "$mapping" --bind-to none \
            -n "$processes" python3 scripts/mpi_affinity_exec.py "$processing_elements" "$@"
    fi
}

saved_measurement() {
    local folder="$1"
    [[ "$RESUME_EXISTING" == 1 && -n "$GRAPH_NAME" &&
       -s "$folder/summary.json" && -s "$folder/ranks.csv" &&
       -s "$folder/history.csv" && -s "$folder/timings.csv" &&
       $(wc -l < "$folder/timings.csv") -eq $((PAGERANK_REPEATS + 1)) ]]
}

run_or_reuse() {
    local folder="$1"
    shift
    if saved_measurement "$folder"; then
        printf 'Reusing completed measurement: %s\n' "$folder"
    else
        "$@"
    fi
}

report_passed() {
    [[ "$RESUME_EXISTING" == 1 && -n "$GRAPH_NAME" && -s "$1" ]] || return 1
    python3 - "$1" "$2" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as source:
    report = json.load(source)
expected = int(sys.argv[2])
raise SystemExit(0 if report.get("failed") == 0 and report.get("passed") == expected
                 and len(report.get("checks", [])) == expected else 1)
PY
}

record_mapping() {
    local nodes="$1"
    local processes="$2"
    local processing_elements="$3"
    local destination="$4"
    run_on_layout "$nodes" "$processes" "$processing_elements" ./build-vanda-matrix-cpu/mpi_rank_hosts \
        | sort -t, -k1,1n > "$destination"
}

STRONG_ROOT="$DATA_ROOT/results/strong"
if [[ -n "$GRAPH_NAME" ]]; then
    STRONG_ROOT="$STRONG_ROOT/$GRAPH_NAME"
    STRONG_MANIFEST="$DATA_ROOT/manifests/strong_${GRAPH_NAME}_${PBS_JOBID}.tsv"
    python3 scripts/select_graph_manifest.py "$DATA_ROOT/manifests/strong_scaling.tsv" \
        "$GRAPH_NAME" "$STRONG_MANIFEST"
else
    STRONG_MANIFEST="$DATA_ROOT/manifests/strong_scaling.tsv"
fi
export PAGERANK_DATASET_MANIFEST="$STRONG_MANIFEST"
export PAGERANK_ENVIRONMENT=vanda-gcc13-release
export PAGERANK_RUN_ID="$RUN_ID"
if [[ "$RUN_STRONG" == 1 ]]; then
for nodes in "${NODE_COUNTS[@]}"; do
    NODE_ROOT="$STRONG_ROOT/nodes${nodes}"
    mkdir -p "$NODE_ROOT/mapping"
    bash scripts/record_vanda_allocation.sh "$NODE_ROOT/cpu_hosts.jsonl"
    export PAGERANK_RESULTS_ROOT="$NODE_ROOT"
    mkdir -p "$NODE_ROOT/serial"
    if [[ -n "$GRAPH_NAME" ]]; then
        mkdir -p "$NODE_ROOT/serial/$GRAPH_NAME"
        cp -al --remove-destination "$DATA_ROOT/results/serial_grid/$GRAPH_NAME/serial/$GRAPH_NAME/."             "$NODE_ROOT/serial/$GRAPH_NAME/"
    else
        cp -al "$DATA_ROOT/results/serial_grid/serial/." "$NODE_ROOT/serial/"
    fi
    report_passed "$NODE_ROOT/serial/validation.json" 1 || validate_result scripts/validate_serial.py
    node_process_counts=()
    for ranks_per_node in "${RANKS_PER_NODE[@]}"; do
        processes=$((nodes * ranks_per_node))
        node_process_counts+=("$processes")
        for communication in allgather halo; do
            suffix=""
            if [[ "$communication" == halo ]]; then suffix="_halo"; fi
            printf 'Strong scaling: nodes=%s ranks/node=%s p=%s communication=%s\n' \
                "$nodes" "$ranks_per_node" "$processes" "$communication"
            record_mapping "$nodes" "$processes" 1 \
                "$NODE_ROOT/mapping/${communication}_p${processes}.csv"
            if [[ "$communication" == halo ]]; then
                run_or_reuse "$NODE_ROOT/mpi_halo/$GRAPH_NAME/p$processes" \
                    run_on_layout "$nodes" "$processes" 1 \
                    ./build-vanda-matrix-cpu/pagerank_mpi --communication=halo
            else
                run_or_reuse "$NODE_ROOT/mpi/$GRAPH_NAME/p$processes" \
                    run_on_layout "$nodes" "$processes" 1 \
                    ./build-vanda-matrix-cpu/pagerank_mpi --communication=allgather
            fi
            OMP_NUM_THREADS=1 OMP_PROC_BIND=spread OMP_PLACES=cores \
                run_or_reuse "$NODE_ROOT/mpi_kokkos$suffix/OpenMP/$GRAPH_NAME/p$processes" \
                run_on_layout "$nodes" "$processes" 1 \
                ./build-vanda-matrix-cpu/pagerank_mpi_kokkos --communication="$communication"
        done
    done
    for communication in allgather halo; do
        suffix=""
        if [[ "$communication" == halo ]]; then suffix="_halo"; fi
        report_passed "$NODE_ROOT/mpi$suffix/validation.json" "${#node_process_counts[@]}" || \
            validate_result scripts/validate_mpi.py "$communication" --processes "${node_process_counts[@]}"
        report_passed "$NODE_ROOT/mpi_kokkos$suffix/OpenMP/validation.json" "${#node_process_counts[@]}" || \
            validate_result scripts/validate_mpi_device.py mpi_kokkos OpenMP "$communication" \
            --processes "${node_process_counts[@]}"
    done

    hybrid_configurations=()
    export OMP_DYNAMIC=FALSE OMP_PROC_BIND=spread OMP_PLACES=cores
    for ranks_per_node in "${RANKS_PER_NODE[@]}"; do
        processes=$((nodes * ranks_per_node))
        for threads in 1 2 4 8 16 32; do
            (( ranks_per_node * threads <= 32 )) || continue
            hybrid_configurations+=("${processes}:${threads}")
            printf 'MPI+OpenMP: nodes=%s ranks/node=%s p=%s threads/rank=%s\n' \
                "$nodes" "$ranks_per_node" "$processes" "$threads"
            for communication in allgather halo; do
                suffix=""
                if [[ "$communication" == halo ]]; then suffix="_halo"; fi
                record_mapping "$nodes" "$processes" "$threads" \
                    "$NODE_ROOT/mapping/hybrid_${communication}_p${processes}_t${threads}.csv"
                PAGERANK_HYBRID_THREADS="$threads" \
                    run_or_reuse "$NODE_ROOT/hybrid$suffix/$GRAPH_NAME/p${processes}_t${threads}" \
                    run_on_layout "$nodes" "$processes" "$threads" \
                    ./build-vanda-matrix-cpu/pagerank_hybrid --communication="$communication"
            done
        done
    done
    export PAGERANK_PROCESS_COUNTS="${node_process_counts[*]}"
    export PAGERANK_HYBRID_THREADS='1 2 4 8 16 32'
    export PAGERANK_HYBRID_CONFIGS="${hybrid_configurations[*]}"
    for communication in allgather halo; do
        suffix=""
        if [[ "$communication" == halo ]]; then suffix="_halo"; fi
        report_passed "$NODE_ROOT/hybrid$suffix/validation.json" "${#hybrid_configurations[@]}" || \
            validate_result scripts/validate_hybrid.py "$communication" --processes "${node_process_counts[@]}"
    done
done
fi

WEAK_ROOT="$DATA_ROOT/results/weak"
if [[ "$RUN_WEAK" == 1 ]]; then
export PAGERANK_RESULTS_ROOT="$WEAK_ROOT"
for communication in allgather halo; do
    for processes in "${PROCESS_COUNTS[@]}"; do
        name=$(printf 'weak_p%03d' "$processes")
        export PAGERANK_DATASET_MANIFEST="$DATA_ROOT/manifests/${name}.tsv"
        printf 'Weak scaling: %s, controlled/uniform/hub, p=%s (%s vertices, %s edges per family)\n' \
            "$communication" "$processes" "$((50000 * processes))" "$((800000 * processes))"
        nodes=$((processes / 32))
        (( nodes < 1 )) && nodes=1
        record_mapping "$nodes" "$processes" 1 "$WEAK_ROOT/mapping/${communication}_p${processes}.csv"
        if [[ "$communication" == halo ]]; then
            run_on_layout "$nodes" "$processes" 1 ./build-vanda-matrix-cpu/pagerank_mpi --communication=halo
        else
            run_on_layout "$nodes" "$processes" 1 ./build-vanda-matrix-cpu/pagerank_mpi --communication=allgather
        fi
        OMP_NUM_THREADS=1 OMP_PROC_BIND=spread OMP_PLACES=cores \
            run_on_layout "$nodes" "$processes" 1 \
            ./build-vanda-matrix-cpu/pagerank_mpi_kokkos --communication="$communication"
    done
done
export PAGERANK_DATASET_MANIFEST="$DATA_ROOT/manifests/weak_scaling.tsv"
export PAGERANK_PROCESS_COUNTS='1 2 4 8 16 32 64 128 256'
export PAGERANK_WEAK_VERTICES_PER_RANK=50000
export PAGERANK_WEAK_EDGES_PER_RANK=800000
validate_result scripts/validate_weak_scaling.py
validate_result scripts/validate_weak_matrix.py mpi_kokkos --backend OpenMP \
    --processes "${PROCESS_COUNTS[@]}"

for processes in 1 2 4 8 16 32 64; do
    name=$(printf 'weak_p%03d' "$processes")
    export PAGERANK_DATASET_MANIFEST="$DATA_ROOT/manifests/${name}.tsv"
    nodes=$((processes / 8))
    (( nodes < 1 )) && nodes=1
    for communication in allgather halo; do
        record_mapping "$nodes" "$processes" 4 \
            "$WEAK_ROOT/mapping/hybrid_${communication}_p${processes}_t4.csv"
        PAGERANK_HYBRID_THREADS=4 run_on_layout "$nodes" "$processes" 4 \
            ./build-vanda-matrix-cpu/pagerank_hybrid --communication="$communication"
    done
done
export PAGERANK_DATASET_MANIFEST="$DATA_ROOT/manifests/weak_scaling.tsv"
validate_result scripts/validate_weak_hybrid.py
fi

if [[ "${PAGERANK_DEFER_VALIDATION:-0}" == 1 ]]; then
    if [[ "$RUN_STRONG" == 1 ]]; then
        for nodes in "${NODE_COUNTS[@]}"; do
            printf '%s\n' "$PBS_JOBID" > "$STRONG_ROOT/nodes${nodes}/measurement_complete.txt"
        done
    fi
    if [[ "$RUN_WEAK" == 1 ]]; then
        printf '%s\n' "$PBS_JOBID" > "$WEAK_ROOT/measurement_complete.txt"
    fi
    exit 0
fi

if [[ "$RUN_STRONG" == 1 ]]; then
    DEST_STRONG="$ROOT/results/runs/$RUN_ID/strong"
    if [[ -n "$GRAPH_NAME" ]]; then DEST_STRONG="$DEST_STRONG/$GRAPH_NAME"; fi
    mkdir -p "$DEST_STRONG"
    for nodes in "${NODE_COUNTS[@]}"; do
        NODE_ROOT="$STRONG_ROOT/nodes${nodes}"
        find "$NODE_ROOT" -name ranks.csv -delete
        cp -a "$NODE_ROOT" "$DEST_STRONG/"
        printf '%s\n' "$PBS_JOBID" > "$DEST_STRONG/nodes${nodes}/complete.txt"
    done
fi
if [[ "$RUN_WEAK" == 1 ]]; then
    find "$WEAK_ROOT" -name ranks.csv -delete
    mkdir -p "$ROOT/results/runs/$RUN_ID/weak"
    cp -a "$WEAK_ROOT/." "$ROOT/results/runs/$RUN_ID/weak/"
    printf '%s\n' "$PBS_JOBID" > "$ROOT/results/runs/$RUN_ID/weak/complete.txt"
fi
printf 'Strong/weak MPI scaling finished and validated: %s\n' "$RUN_ID"

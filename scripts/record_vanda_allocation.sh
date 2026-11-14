#!/usr/bin/env bash
set -euo pipefail
destination="${1:?Set output file}"
nodes=$(sort -u "$PBS_NODEFILE" | wc -l)
timeout 120s mpiexec -x LD_LIBRARY_PATH --map-by ppr:1:node --bind-to none \
    -n "$nodes" python3 scripts/record_cpu_host.py > "$destination"

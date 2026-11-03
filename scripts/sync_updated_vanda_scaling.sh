#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_ID="${1:?Pass the Vanda run ID}"
source="hongxinran@vanda.nus.edu.sg:/scratch/hongxinran/DSA5208_PROJECT_3/results/updated_vanda_scaling/$RUN_ID/"
destination="$ROOT/results/updated_vanda_scaling/$RUN_ID/"
mkdir -p "$destination"
rsync -az --partial -e "ssh -o BatchMode=yes -o ProxyCommand=none -o ProxyJump=none" \
    "$source" "$destination"

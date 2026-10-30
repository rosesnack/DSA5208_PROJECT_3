#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <cpu-pbs-job-id> <gpu-pbs-job-id>" >&2
    exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPU_JOB_ID="$1"
GPU_JOB_ID="$2"
SSH_KEY="$HOME/.ssh/id_rsa"
mkdir -p "$ROOT/results/updated_vanda/$CPU_JOB_ID" \
         "$ROOT/results/updated_vanda_gpu/$GPU_JOB_ID"

rsync -az --progress -e "ssh -i $SSH_KEY -o IdentitiesOnly=yes" \
    "hongxinran@vanda.nus.edu.sg:~/dsa5208_proj3/results/vanda/$CPU_JOB_ID/" \
    "$ROOT/results/updated_vanda/$CPU_JOB_ID/"

rsync -az --progress -e "ssh -i $SSH_KEY -o IdentitiesOnly=yes" \
    "hongxinran@vanda.nus.edu.sg:~/dsa5208_proj3/results/vanda-a40-gpu/$GPU_JOB_ID/" \
    "$ROOT/results/updated_vanda_gpu/$GPU_JOB_ID/"

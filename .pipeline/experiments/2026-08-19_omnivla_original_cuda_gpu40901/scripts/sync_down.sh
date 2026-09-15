#!/usr/bin/env bash
# Pull evidence back from the remote execution copy. Weights never come back.
set -euo pipefail
ROOT=/Users/sun/tongbu/study/phdproject/vla
EXP="$ROOT/.pipeline/experiments/2026-08-19_omnivla_original_cuda_gpu40901"
HOST=gpu40901
REMOTE=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda
for d in env verify runs logs; do
  mkdir -p "$EXP/$d"
  rsync -az --exclude '*.pth' --exclude '*.safetensors' --exclude '*.pt' \
        --exclude '*.whl' \
        "$HOST:$REMOTE/$d/" "$EXP/$d/"
done
echo "[sync_down] done -> $EXP"

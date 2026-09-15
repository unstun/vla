#!/usr/bin/env bash
# Push the local source of truth to the remote execution copy (AGENTS.md rule 7).
# Never pushes weights; never pulls remote edits back silently.
set -euo pipefail
ROOT=/Users/sun/tongbu/study/phdproject/vla
TP="$ROOT/third_party/2026-08-18_omnivla_5182600"
EXP0="$ROOT/.pipeline/experiments/2026-08-18_omnivla_offline_smoke"
EXP="$ROOT/.pipeline/experiments/2026-08-19_omnivla_original_cuda_gpu40901"
HOST=gpu40901
REMOTE=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda

ssh -o BatchMode=yes "$HOST" "mkdir -p $REMOTE/{pristine,work,checkpoints,env,verify,runs,logs,scripts,patches_edge,patches_original}"
rsync -az --delete "$TP/OmniVLA/"            "$HOST:$REMOTE/pristine/OmniVLA/"
rsync -az "$TP/SOURCE_MANIFEST.sha256"       "$HOST:$REMOTE/"
rsync -az "$TP/checkpoints/CHECKPOINT_MANIFEST.tsv" "$HOST:$REMOTE/"
rsync -az --delete "$EXP0/patches/"          "$HOST:$REMOTE/patches_edge/"
rsync -az --delete "$EXP/patches/"           "$HOST:$REMOTE/patches_original/"
rsync -az "$EXP/scripts/"                    "$HOST:$REMOTE/scripts/"
echo "[sync_up] done -> $HOST:$REMOTE"

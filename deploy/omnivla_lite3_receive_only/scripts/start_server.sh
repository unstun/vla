#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_lite3_receive_only
ORIGINAL=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda
PYTHON=$ORIGINAL/envs/omnivla_sun/bin/python
BIND=192.168.2.109
PORT=8765
PID_FILE=$ROOT/runtime/server.pid
TOKEN_FILE=$ROOT/runtime/token
AUDIT_DIR=$ROOT/runtime/audit
LOG_FILE=$ROOT/runtime/server.log

mkdir -p "$ROOT/runtime" "$AUDIT_DIR"
chmod 700 "$ROOT/runtime" "$AUDIT_DIR"
if [ -s "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "server already running: pid=$(cat "$PID_FILE")" >&2
  exit 1
fi
if ss -ltn 'sport = :8765' | grep -q LISTEN; then
  echo "port 8765 is already in use; refusing to start" >&2
  exit 1
fi
if [ ! -s "$TOKEN_FILE" ]; then
  umask 077
  "$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(48))' > "$TOKEN_FILE"
fi
chmod 600 "$TOKEN_FILE"

"$ROOT/deploy/omnivla_lite3_receive_only/scripts/preflight_vram.sh" \
  "$ROOT/runtime/vram_preflight.csv"
cd "$ORIGINAL/work/OmniVLA"
OMNIVLA_CUDA_MEM_FRACTION=0.45 \
MPLBACKEND=Agg \
HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 \
PYTHONPATH="$ROOT" \
nohup nice -n 10 timeout 1800 "$PYTHON" -m deploy.omnivla_lite3_receive_only.server \
  --bind "$BIND" \
  --port "$PORT" \
  --token-file "$TOKEN_FILE" \
  --audit-dir "$AUDIT_DIR" \
  --backend original \
  --upstream-root "$ORIGINAL/work/OmniVLA" \
  --checkpoint-path "$ORIGINAL/checkpoints/omnivla-original" \
  > "$LOG_FILE" 2>&1 </dev/null &
pid=$!
echo "$pid" > "$PID_FILE"
echo "started pid=$pid bind=$BIND port=$PORT"

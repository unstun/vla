#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_lite3_receive_only
PID_FILE=$ROOT/runtime/server.pid
if [ -s "$PID_FILE" ]; then
  pid=$(cat "$PID_FILE")
  ps -o pid,ppid,etime,stat,%cpu,%mem,args -p "$pid" || true
fi
ss -ltnp 'sport = :8765' || true


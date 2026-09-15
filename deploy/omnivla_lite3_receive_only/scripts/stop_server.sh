#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_lite3_receive_only
PID_FILE=$ROOT/runtime/server.pid
if [ ! -s "$PID_FILE" ]; then
  if ss -ltn 'sport = :8765' | grep -q LISTEN; then
    echo "port 8765 is open but no task PID is recorded; refusing to signal any process" >&2
    exit 5
  fi
  echo "server is not recorded as running"
  exit 0
fi
pid=$(cat "$PID_FILE")
args=$(ps -p "$pid" -o args= 2>/dev/null || true)
case "$args" in
  *"deploy.omnivla_lite3_receive_only.server"*) ;;
  "")
    if ss -ltn 'sport = :8765' | grep -q LISTEN; then
      echo "recorded PID exited but port 8765 remains open; refusing to signal an unrecorded process" >&2
      exit 5
    fi
    rm -f "$PID_FILE"
    echo "recorded process already exited"
    exit 0
    ;;
  *) echo "refusing to stop unexpected pid $pid: $args" >&2; exit 2 ;;
esac
kill -TERM "$pid"
for _attempt in $(seq 1 60); do
  kill -0 "$pid" 2>/dev/null || break
  sleep 0.5
done
if kill -0 "$pid" 2>/dev/null; then
  echo "server did not stop on TERM; no stronger signal sent" >&2
  exit 3
fi
if ss -ltn 'sport = :8765' | grep -q LISTEN; then
  echo "recorded process exited but port 8765 is still open; no other PID was signalled" >&2
  exit 4
fi
rm -f "$PID_FILE"
echo "stopped pid=$pid"

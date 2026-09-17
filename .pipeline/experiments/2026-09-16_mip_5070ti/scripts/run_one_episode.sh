#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
mode=navigation
if [[ "${1:-}" == --protocol-smoke ]]; then
  mode=protocol-smoke
  shift
  [[ $# == 0 ]] || { echo 'The protocol smoke takes no episode arguments'; exit 2; }
else
  : "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY in this server shell first}"
fi
export PYTHONNOUSERSITE=1
test -f "$root/setup/mp3d_subset_complete.json"
exec 9>"$root/setup/episode.lock"
flock -n 9 || { echo 'An episode is already running'; exit 73; }
python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 19200))  # Refuse to reuse an unowned simulator.
PY
stamp=$(date -u +%Y%m%dT%H%M%SZ)
bash "$root/scripts/start_simulator.sh" > "$root/setup/simulator_${stamp}.log" 2>&1 &
server_pid=$!
cleanup() {
  local run_rc=$? server_rc=0
  kill -TERM "$server_pid" 2>/dev/null || true
  for _ in {1..20}; do
    kill -0 "$server_pid" 2>/dev/null || break
    sleep 0.5
  done
  kill -KILL "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || server_rc=$?
  printf '%s\n' "$server_rc" > "$root/setup/simulator_${stamp}.exit"
  if [[ "$server_rc" != 0 && "$server_rc" != 143 ]]; then
    echo "Simulator teardown failed: exit $server_rc"
    [[ "$run_rc" != 0 ]] || run_rc=1
  fi
  exit "$run_rc"
}
trap cleanup EXIT
ready=0
for _ in {1..120}; do
  sleep 1
  kill -0 "$server_pid" 2>/dev/null || { echo 'Simulator exited; inspect setup/simulator_*.log'; exit 1; }
  if curl -fsS --max-time 2 http://127.0.0.1:19200/health > /dev/null; then
    ready=1
    break
  fi
done
[[ "$ready" == 1 ]] || { echo 'Simulator readiness timed out'; exit 1; }
if [[ "$mode" == protocol-smoke ]]; then
  /home/sun/miniconda3/envs/agentcanvas/bin/python \
    "$root/scripts/protocol_smoke.py" --root "$root"
else
  /home/sun/miniconda3/envs/agentcanvas/bin/python \
    "$root/scripts/run_one_episode.py" --root "$root" "$@"
fi

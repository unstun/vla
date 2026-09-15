#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/nvidia/sun/vla_exec/2026-08-19_omnivla_vla_evidence_audit
OLD=/home/nvidia/sun/vla_exec/2026-08-19_omnivla_edge_orin64
LOGS="$ROOT/raw/omnivla_edge"
mkdir -p "$LOGS"

(
  echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  hostname
  tr -d '\0' < /proc/device-tree/model; echo
  sed -n '1p' /etc/nv_tegra_release
  python3 --version
  free -h
  df -h /
  ip -brief address show eth0
  ip -brief address show wlP7p1s0
  ip route
  pgrep -af "2026-08-19_omnivla_vla_evidence_audit|run_omnivla_edge.py|tegrastats" || true
) > "$LOGS/preflight.txt"

sha256sum \
  "$OLD/checkpoints/omnivla-edge/omnivla-edge.pth" \
  "$OLD/checkpoints/clip/ViT-B-32.pt" > "$LOGS/weight_hashes.txt"

if grep -RInE --include='*.py' 'MotionSDK|rospy|rclpy|cmd_vel|sendto\(|socket\.socket\(|joint.target|locomotion.command|ros.*publish' \
  "$ROOT/scripts"; then
  echo "receive-only static scan failed" >&2
  exit 76
fi

export MPLBACKEND=Agg
export PYTHONPATH="$OLD/python_deps:$ROOT/scripts"

if command -v tegrastats >/dev/null 2>&1; then
  tegrastats --interval 500 > "$LOGS/tegrastats.log" 2>&1 &
  monitor_pid=$!
else
  monitor_pid=""
fi
cleanup() {
  if [[ -n "$monitor_pid" ]]; then
    kill "$monitor_pid" >/dev/null 2>&1 || true
    wait "$monitor_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

set +e
(
  cd "$ROOT/work/OmniVLA"
  exec timeout 1500 nice -n 10 python3 "$ROOT/scripts/run_edge_batch.py" \
    --experiment-root "$ROOT" \
    --upstream-root "$ROOT/work/OmniVLA" \
    --checkpoint-path "$OLD/checkpoints/omnivla-edge/omnivla-edge.pth" \
    --clip-root "$OLD/checkpoints/clip"
) > "$LOGS/stdout.log" 2> "$LOGS/stderr.log"
status=$?
set -e
printf '%s\n' "$status" > "$LOGS/exit_status.txt"
cleanup
trap - EXIT INT TERM

(
  echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "exit_status=$status"
  if pgrep -af "$ROOT" | grep -v "pgrep -af"; then
    echo "task_processes_absent=0"
  else
    echo "task_processes_absent=1"
  fi
  if pgrep -x tegrastats >/dev/null 2>&1; then echo "task_monitor_absent=0"; else echo "task_monitor_absent=1"; fi
  ip -brief address show eth0
  ip -brief address show wlP7p1s0
  ip route
) > "$LOGS/postflight.txt"

(
  cd "$ROOT"
  find . -type f ! -path './manifests/remote_artifacts.sha256' -print0 \
    | sort -z | xargs -0 sha256sum
) > "$ROOT/manifests/remote_artifacts.sha256"
exit "$status"

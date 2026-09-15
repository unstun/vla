#!/usr/bin/env bash
set -euo pipefail

REMOTE_ROOT="${OMNIVLA_REMOTE_ROOT:-/home/nvidia/sun/vla_exec/2026-08-19_omnivla_edge_orin64}"
RUN_ID="${1:-}"
if [[ -z "$RUN_ID" || ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "usage: remote_run_once.sh SAFE_RUN_ID" >&2
  exit 30
fi

WORK="$REMOTE_ROOT/work/OmniVLA"
PYTHON=python3
PY_DEPS="$REMOTE_ROOT/python_deps"
RUN_DIR="$REMOTE_ROOT/runs/$RUN_ID"
INPUT="$REMOTE_ROOT/inputs/lite3_real_frame.jpg"

if [[ -e "$RUN_DIR" ]]; then
  echo "refusing to reuse run directory: $RUN_DIR" >&2
  exit 31
fi
mkdir -p "$RUN_DIR"

(
  echo "utc_start=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  uname -a
  sed -n '1p' /etc/nv_tegra_release
  free -h
  df -h "$REMOTE_ROOT"
  ip -brief address
  ip route
) > "$RUN_DIR/pre_run_environment.txt"

PYTHONPATH="$PY_DEPS${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" - <<'PY' > "$RUN_DIR/cuda_probe.json"
import json
import torch
print(json.dumps({
    "torch": torch.__version__,
    "cuda_available": torch.cuda.is_available(),
    "device_count": torch.cuda.device_count(),
    "device_0": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
}, indent=2))
if not torch.cuda.is_available():
    raise SystemExit("CUDA unavailable")
PY

sha256sum \
  "$REMOTE_ROOT/checkpoints/omnivla-edge/omnivla-edge.pth" \
  "$REMOTE_ROOT/checkpoints/clip/ViT-B-32.pt" \
  "$INPUT" > "$RUN_DIR/selected_input_hashes.sha256"

cp "$REMOTE_ROOT/pristine/OmniVLA/inference/current_img.jpg" \
  "$RUN_DIR/upstream_current_img.jpg"
cp "$INPUT" "$WORK/inference/current_img.jpg"
cp "$INPUT" "$RUN_DIR/lite3_real_frame.jpg"

if command -v tegrastats >/dev/null 2>&1; then
  tegrastats --interval 500 > "$RUN_DIR/tegrastats.log" 2>&1 &
  tegra_pid=$!
else
  tegra_pid=""
fi
cleanup_monitor() {
  if [[ -n "$tegra_pid" ]]; then
    kill "$tegra_pid" >/dev/null 2>&1 || true
    wait "$tegra_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup_monitor EXIT

run_start_ns="$(date +%s%N)"
set +e
(
  cd "$WORK"
  env \
    MPLBACKEND=Agg \
    OMNIVLA_RUN_DIR="$RUN_DIR" \
    OMNIVLA_PROMPT="move forward" \
    OMNIVLA_POSE_GOAL=0 \
    OMNIVLA_SATELLITE=0 \
    OMNIVLA_IMAGE_GOAL=0 \
    OMNIVLA_LAN_PROMPT=1 \
    OMNIVLA_CLIP_ROOT="$REMOTE_ROOT/checkpoints/clip" \
    PYTHONPATH="$PY_DEPS${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON" inference/run_omnivla_edge.py
) > "$RUN_DIR/stdout.log" 2> "$RUN_DIR/stderr.log"
run_status=$?
set -e
run_end_ns="$(date +%s%N)"
"$PYTHON" - "$run_start_ns" "$run_end_ns" <<'PY' > "$RUN_DIR/wall_time.json"
import json
import sys

start_ns = int(sys.argv[1])
end_ns = int(sys.argv[2])
print(json.dumps({
    "start_ns": start_ns,
    "end_ns": end_ns,
    "wall_seconds": (end_ns - start_ns) / 1_000_000_000.0,
}, indent=2))
PY
printf '%s\n' "$run_status" > "$RUN_DIR/exit_status.txt"
cleanup_monitor
trap - EXIT

if [[ "$run_status" -ne 0 ]]; then
  echo "one-shot inference failed with status $run_status" >&2
  exit "$run_status"
fi

PYTHONPATH="$PY_DEPS${PYTHONPATH:+:$PYTHONPATH}" \
  "$PYTHON" "$REMOTE_ROOT/scripts/validate_outputs.py" "$RUN_DIR" \
  | tee "$RUN_DIR/validation.log"

(
  echo "utc_end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  df -h "$REMOTE_ROOT"
  task_runner_found=0
  for pid in $(pgrep -x python3 2>/dev/null || true); do
    cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
    if [[ "$cmdline" == *"inference/run_omnivla_edge.py"* ]]; then
      echo "task runner remains: pid=$pid cmd=$cmdline"
      task_runner_found=1
    fi
  done
  echo "task_runner_found=$task_runner_found"
  if pgrep -x tegrastats >/dev/null 2>&1; then
    echo "tegrastats remains"
  else
    echo "tegrastats_absent=1"
  fi
  ss -ltnp 2>/dev/null || true
) > "$RUN_DIR/post_run_environment.txt"

(
  cd "$RUN_DIR"
  find . -type f ! -name retained_artifacts.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum
) > "$RUN_DIR/retained_artifacts.sha256"

echo "one-shot inference complete: $RUN_DIR"

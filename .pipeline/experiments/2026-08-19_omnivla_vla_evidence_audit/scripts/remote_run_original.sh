#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_vla_evidence_audit
PYTHON=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/envs/omnivla_sun/bin/python
CHECKPOINT=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/checkpoints/omnivla-original
LOGS="$ROOT/raw/omnivla_original"
mkdir -p "$LOGS"

(
  echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  hostname
  "$PYTHON" --version
  nvidia-smi --query-gpu=name,memory.total,memory.free,memory.used,utilization.gpu --format=csv,noheader
  free -h
  df -h /home
  pgrep -af "2026-08-19_omnivla_vla_evidence_audit|run_omnivla.py" || true
  nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader || true
) > "$LOGS/preflight.txt"

free_mib=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1 | tr -d ' ')
if [[ -z "$free_mib" || "$free_mib" -lt 24576 ]]; then
  echo "VRAM guard failed: free_mib=$free_mib required_mib=24576" >&2
  exit 75
fi

if grep -RInE --include='*.py' 'MotionSDK|rospy|rclpy|cmd_vel|sendto\(|socket\.socket\(|joint.target|locomotion.command|ros.*publish' \
  "$ROOT/scripts" "$ROOT/runtime"; then
  echo "receive-only static scan failed" >&2
  exit 76
fi

export OMNIVLA_CUDA_MEM_FRACTION=0.45
export TOKENIZERS_PARALLELISM=false
export MPLBACKEND=Agg
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONPATH="$ROOT/scripts"

echo 'timestamp_utc,memory_free_mib,memory_used_mib,utilization_gpu_percent' > "$LOGS/gpu_samples.csv"
(
  while true; do
    nvidia-smi --query-gpu=timestamp,memory.free,memory.used,utilization.gpu \
      --format=csv,noheader,nounits >> "$LOGS/gpu_samples.csv" 2>/dev/null || true
    sleep 1
  done
) &
monitor_pid=$!
cleanup() {
  kill "$monitor_pid" >/dev/null 2>&1 || true
  wait "$monitor_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

set +e
(
  cd "$ROOT"
  exec timeout 1500 nice -n 10 "$PYTHON" scripts/run_original_batch.py \
    --experiment-root "$ROOT" \
    --runtime-root "$ROOT/runtime" \
    --upstream-root "$ROOT/work/OmniVLA" \
    --checkpoint-path "$CHECKPOINT"
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
  nvidia-smi --query-gpu=name,memory.total,memory.free,memory.used,utilization.gpu --format=csv,noheader
) > "$LOGS/postflight.txt"

(
  cd "$ROOT"
  find . -type f ! -path './manifests/remote_artifacts.sha256' -print0 \
    | sort -z | xargs -0 sha256sum
) > "$ROOT/manifests/remote_artifacts.sha256"
exit "$status"

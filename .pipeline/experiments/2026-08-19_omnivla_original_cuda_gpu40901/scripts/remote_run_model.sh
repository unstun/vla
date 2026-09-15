#!/usr/bin/env bash
# Run one guarded OmniVLA-original process on the shared gpu40901 host.
# Usage: remote_run_model.sh TAG
set -uo pipefail

REMOTE=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda
WORK=$REMOTE/work/OmniVLA
PYTHON=$REMOTE/envs/omnivla_sun/bin/python
TAG=${1:?usage: remote_run_model.sh TAG}
TIMEOUT_SECONDS=${OMNIVLA_TIMEOUT_SECONDS:-1800}
MIN_FREE_MIB=24576

case "$TAG" in
  *[!a-zA-Z0-9_-]*|'') echo "invalid tag: $TAG" >&2; exit 64 ;;
esac

RUN=$REMOTE/runs/$(date -u +%Y%m%dT%H%M%SZ)_original_$TAG
mkdir -p "$RUN"
chmod 700 "$RUN"

echo "timestamp_utc,memory_free_mib,memory_used_mib,utilization_gpu_percent" \
  > "$RUN/vram_preflight.csv"
for sample in $(seq 1 12); do
  nvidia-smi --query-gpu=timestamp,memory.free,memory.used,utilization.gpu \
    --format=csv,noheader,nounits >> "$RUN/vram_preflight.csv"
  if [ "$sample" -lt 12 ]; then sleep 5; fi
done
minimum_free_mib=$(awk -F, 'NR > 1 {gsub(/ /,"",$2); if (min == "" || $2 < min) min=$2} END {print min}' "$RUN/vram_preflight.csv")
echo "minimum_free_mib=$minimum_free_mib required_mib=$MIN_FREE_MIB" | tee "$RUN/vram_guard.txt"
if [ -z "$minimum_free_mib" ] || [ "$minimum_free_mib" -lt "$MIN_FREE_MIB" ]; then
  echo "VRAM guard failed; model process was not started" | tee -a "$RUN/vram_guard.txt" >&2
  exit 75
fi

export OMNIVLA_ORIGINAL_PATH=$REMOTE/checkpoints/omnivla-original
export OMNIVLA_RUN_DIR=$RUN
export OMNIVLA_CUDA_MEM_FRACTION=0.45
export TOKENIZERS_PARALLELISM=false
export MPLBACKEND=Agg
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

echo "timestamp_utc,memory_free_mib,memory_used_mib,utilization_gpu_percent" \
  > "$RUN/gpu_samples.csv"
(
  while [ ! -e "$RUN/.stop_sampler" ]; do
    nvidia-smi --query-gpu=timestamp,memory.free,memory.used,utilization.gpu \
      --format=csv,noheader,nounits >> "$RUN/gpu_samples.csv" 2>/dev/null || true
    sleep 1
  done
) &
sampler_pid=$!
cleanup() {
  touch "$RUN/.stop_sampler"
  wait "$sampler_pid" 2>/dev/null || true
  rm -f "$RUN/.stop_sampler"
}
trap cleanup EXIT INT TERM

started_epoch=$(date +%s)
set +e
(
  cd "$WORK" || exit 70
  echo "entry_point=python inference/run_omnivla.py"
  echo "cwd=$WORK"
  echo "nice=10 timeout_seconds=$TIMEOUT_SECONDS"
  echo "cuda_memory_fraction=$OMNIVLA_CUDA_MEM_FRACTION"
  echo "original_path=$OMNIVLA_ORIGINAL_PATH"
  exec timeout "$TIMEOUT_SECONDS" nice -n 10 /usr/bin/time -v \
    "$PYTHON" inference/run_omnivla.py
) > "$RUN/stdout.log" 2> "$RUN/stderr.log"
exit_code=$?
set -e
ended_epoch=$(date +%s)
wall_seconds=$((ended_epoch - started_epoch))
cleanup
trap - EXIT INT TERM

peak_gpu_used_mib=$(awk -F, 'NR > 1 {gsub(/ /,"",$3); if (max == "" || $3 > max) max=$3} END {print max}' "$RUN/gpu_samples.csv")
peak_rss_kib=$(awk -F: '/Maximum resident set size/ {gsub(/^[ \t]+/,"",$2); print $2}' "$RUN/stderr.log" | tail -1)

"$PYTHON" - "$RUN" "$TAG" "$exit_code" "$wall_seconds" \
  "$minimum_free_mib" "$peak_gpu_used_mib" "${peak_rss_kib:-}" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

run = Path(sys.argv[1])
tag = sys.argv[2]
exit_code = int(sys.argv[3])
wall_seconds = int(sys.argv[4])
minimum_free_mib = int(sys.argv[5])
peak_gpu_used_mib = int(sys.argv[6]) if sys.argv[6] else None
peak_rss_kib = int(sys.argv[7]) if sys.argv[7] else None
remote = Path("/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda")

def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()

patches = sorted((remote / "patches_original").glob("*.patch"))
meta = {
    "tag": tag,
    "run_dir": str(run),
    "exit_code": exit_code,
    "wall_seconds": wall_seconds,
    "timeout_seconds": int(os.environ.get("OMNIVLA_TIMEOUT_SECONDS", "1800")),
    "nice": 10,
    "preflight_minimum_free_mib": minimum_free_mib,
    "preflight_required_free_mib": 24576,
    "nvidia_smi_peak_total_used_mib": peak_gpu_used_mib,
    "peak_rss_kib": peak_rss_kib,
    "entry_point": "python inference/run_omnivla.py",
    "upstream_commit": "5182600cb4a9ee07684e17cdd2a6cbafc56b8a68",
    "checkpoint_revision": "e36a84d4923c041149d441f93f3bdb7092bb5f07",
    "checkpoint_path": str(remote / "checkpoints/omnivla-original"),
    "cuda_memory_fraction": 0.45,
    "python": platform.python_version(),
    "patches_applied": [
        {"file": path.name, "sha256": sha256(path)} for path in patches
    ],
    "env_overrides": {
        key: value for key, value in os.environ.items() if key.startswith("OMNIVLA_")
    },
}
(run / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
PY

echo "run_dir=$RUN exit_code=$exit_code wall_seconds=$wall_seconds"
exit "$exit_code"

#!/usr/bin/env bash
set -euo pipefail

OUT=${1:?usage: preflight_vram.sh OUTPUT_FILE}
SAMPLES=${OMNIVLA_VRAM_SAMPLES:-12}
INTERVAL=${OMNIVLA_VRAM_INTERVAL_SECONDS:-5}
MIN_REQUIRED_MIB=${OMNIVLA_MIN_FREE_MIB:-24576}

: > "$OUT"
for _sample in $(seq 1 "$SAMPLES"); do
  nvidia-smi --query-gpu=timestamp,memory.free,memory.used,utilization.gpu \
    --format=csv,noheader,nounits | tee -a "$OUT"
  if [ "$_sample" -lt "$SAMPLES" ]; then sleep "$INTERVAL"; fi
done

minimum=$(awk -F, 'BEGIN { min = 999999999 } { gsub(/ /, "", $2); if ($2 < min) min = $2 } END { print min }' "$OUT")
echo "minimum_free_mib=$minimum required_mib=$MIN_REQUIRED_MIB" | tee -a "$OUT"
if [ "$minimum" -lt "$MIN_REQUIRED_MIB" ]; then
  echo "VRAM guard failed" >&2
  exit 1
fi


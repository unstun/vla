#!/usr/bin/env bash
# Phase B.2, last part: InternVLA-N1 resident on the GPU while the dual-720p Isaac probe runs beside it.
#
#   phase_b_vla_resident.sh RUN_ID [ISAAC_CONFIG]
#
# Order: the VLA loads first and keeps inferring (as a Phase C VLA server would), then the Isaac probe starts through
# phase_b_run_docker.sh as run RUN_ID_isaac. A 1 s nvidia-smi sampler covers the whole window. If either side runs out
# of memory, that is the result and it is recorded, not retried. Set VLA_ALLOC_CONF to pass PYTORCH_CUDA_ALLOC_CONF.
#
# Reads the DualVLN execution copy (model, InternNav, official_env_024) and writes nothing into it.
set -euo pipefail

[[ $# -ge 1 && $# -le 2 ]] || { echo "usage: $0 RUN_ID [ISAAC_CONFIG]" >&2; exit 64; }
RUN_ID=$1
ISAAC_CONFIG=${2:-dual_720}
[[ $RUN_ID =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { echo "bad run id" >&2; exit 64; }

ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
DUALVLN=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
PY=$DUALVLN/official_r2r/official_env_024/bin/python
OUT=$ROOT/runs/$RUN_ID
FRAMES=$ROOT/runs/phase_b_dual720_hz0_v1
READY_TIMEOUT=${VLA_READY_TIMEOUT:-900}

for required in "$PY" "$DUALVLN/models/InternVLA-N1-DualVLN/config.json" "$DUALVLN/work/InternNav/internnav" \
    "$DUALVLN/models/depth_anything_v2_metric_hypersim_vits.pth" \
    "$ROOT/tools/phase_b_vla_resident_probe.py" "$ROOT/phase_b_run_docker.sh" \
    "$FRAMES/frame_d435i_rgb.npy" "$FRAMES/frame_d435i_distance_to_image_plane.npy"; do
  [[ -e $required ]] || { echo "required input missing: $required" >&2; exit 66; }
done
[[ -e $OUT || -e $ROOT/runs/${RUN_ID}_isaac ]] && { echo "run output already exists: $OUT" >&2; exit 73; }
if sudo docker ps --format '{{.Names}}' | grep -qE '^vla-phase-[ab]-'; then
  echo "a vla-phase container is running; refusing" >&2; exit 75
fi
USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
(( USED < 1000 )) || { echo "GPU already has ${USED} MiB in use; a co-residence measurement needs an idle GPU" >&2; exit 75; }
FREE_GB=$(df -Pk "$ROOT" | awk 'NR==2 {printf "%d", $4 / 1048576}')
(( FREE_GB >= 6 )) || { echo "only ${FREE_GB} GB free" >&2; exit 75; }

mkdir -p "$OUT"
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_before.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_before.txt"

(
  echo "unix_s,device_used_mib,util_pct,apps"
  while sleep 1; do
    dev=$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | head -1 | tr -d ' ')
    apps=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | tr -d ' ' | tr '\n' ';')
    echo "$(date +%s),$dev,$apps"
  done
) > "$OUT/gpu_samples.csv" 2>/dev/null &
SAMPLER=$!
VLA_PID=
cleanup() {
  touch "$OUT/stop" 2>/dev/null || true
  [[ -n $VLA_PID ]] && { sleep 5; kill "$VLA_PID" 2>/dev/null || true; }
  kill "$SAMPLER" 2>/dev/null || true
  # Safety net if the probe died before removing its launch-dir link (never follow it into model bytes).
  [[ -L $OUT/checkpoints/depth_anything_v2_metric_hypersim_vits.pth ]] \
    && rm -f "$OUT/checkpoints/depth_anything_v2_metric_hypersim_vits.pth" && rmdir "$OUT/checkpoints" 2>/dev/null
  true
}
trap cleanup EXIT

env ${VLA_ALLOC_CONF:+PYTORCH_CUDA_ALLOC_CONF=$VLA_ALLOC_CONF} \
  timeout --signal=TERM --kill-after=30 $((READY_TIMEOUT + 1800)) \
  "$PY" "$ROOT/tools/phase_b_vla_resident_probe.py" \
    --output-dir "$OUT" \
    --internnav-root "$DUALVLN/work/InternNav" \
    --model-path "$DUALVLN/models/InternVLA-N1-DualVLN" \
    --depth-anything "$DUALVLN/models/depth_anything_v2_metric_hypersim_vits.pth" \
    --rgb "$FRAMES/frame_d435i_rgb.npy" \
    --depth "$FRAMES/frame_d435i_distance_to_image_plane.npy" \
    --hfov 69 \
    --max-seconds 1800 \
  > "$OUT/vla.log" 2>&1 &
VLA_PID=$!

waited=0
until [[ -f $OUT/vla_ready ]]; do
  if ! kill -0 "$VLA_PID" 2>/dev/null; then
    echo "VLA process exited before ready" >&2
    wait "$VLA_PID" || true
    echo "PHASE_B_VLA_RESIDENT_DONE status=vla_failed_before_isaac"
    exit 0
  fi
  (( waited >= READY_TIMEOUT )) && { echo "VLA not ready after ${READY_TIMEOUT} s" >&2; echo "PHASE_B_VLA_RESIDENT_DONE status=vla_not_ready"; exit 0; }
  sleep 2; waited=$((waited + 2))
done
echo "VLA ready after ${waited} s; starting Isaac $ISAAC_CONFIG"

set +e
VLA_ALLOW_GPU_BUSY=1 VLA_WALL_LIMIT=${VLA_ISAAC_WALL_LIMIT:-900} \
  bash "$ROOT/phase_b_run_docker.sh" "${RUN_ID}_isaac" "$ISAAC_CONFIG" 0 200 \
  > "$OUT/isaac_driver.log" 2>&1
ISAAC_RC=$?
set -e
ISAAC_LINE=$(grep PHASE_B_RUN_DONE "$OUT/isaac_driver.log" || echo "no PHASE_B_RUN_DONE (driver rc=$ISAAC_RC)")

touch "$OUT/stop"
for _ in $(seq 1 60); do kill -0 "$VLA_PID" 2>/dev/null || break; sleep 2; done
set +e
wait "$VLA_PID"; VLA_RC=$?
set -e
VLA_PID=
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_after.txt"
echo "PHASE_B_VLA_RESIDENT_DONE vla_rc=$VLA_RC isaac: $ISAAC_LINE"

#!/usr/bin/env bash
# Phase B on the container host: measure what a robot-mounted RTX camera costs.
#
#   phase_b_run_docker.sh RUN_ID CONFIG [CAMERA_HZ] [STEPS]
#     CONFIG     none | single_640 | dual_720
#     CAMERA_HZ  0 renders every policy step (worst case); 5 matches the expected VLA decision rate
#
# Inference only. Builds nothing, pulls nothing, deletes nothing, and never touches the unowned
# `isaac-sim` streaming container.
set -euo pipefail

if [[ $# -lt 2 || $# -gt 4 ]]; then
  echo "usage: $0 RUN_ID CONFIG [CAMERA_HZ] [STEPS]" >&2
  exit 64
fi
RUN_ID=$1
CONFIG=$2
CAMERA_HZ=${3:-0}
STEPS=${4:-200}
PHYSX_BUFFERS=${VLA_PHYSX_BUFFERS:-v12}          # v12 | one_env
RENDERING_MODE=${VLA_RENDERING_MODE:-default}    # default | performance | balanced | quality
case $PHYSX_BUFFERS in v12|one_env) ;; *) echo "unknown VLA_PHYSX_BUFFERS: $PHYSX_BUFFERS" >&2; exit 64 ;; esac
case $RENDERING_MODE in default|performance|balanced|quality) ;; *) echo "unknown VLA_RENDERING_MODE" >&2; exit 64 ;; esac

[[ $RUN_ID =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { echo "run id must be lowercase alphanumeric with - or _" >&2; exit 64; }
case $CONFIG in none|single_640|dual_720) ;; *) echo "unknown config: $CONFIG" >&2; exit 64 ;; esac
if [[ ! $STEPS =~ ^[0-9]+$ ]] || (( STEPS < 20 || STEPS > 2000 )); then
  echo "STEPS must be an integer in [20, 2000]" >&2; exit 64
fi

ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
INPUTS=$ROOT/inputs
OUT=$ROOT/runs/$RUN_ID
IMAGE=${VLA_IMAGE:-e01-walking-isaaclab:20260905}
CONTAINER=vla-phase-b-$RUN_ID
WALL_LIMIT=${VLA_WALL_LIMIT:-1800}
CONTAINER_UID=${VLA_CONTAINER_UID:-1234}
LAB=/isaac-sim/kit/python/lib/python3.11/site-packages/isaaclab/source

for required in \
  "$INPUTS/lite3_sim_bridge/lite3_sim_bridge/run_isaac_v12_fallback.py" \
  "$INPUTS/v12_runtime/source/rsl_rl/rsl_rl/env/vec_env.py" \
  "$INPUTS/checkpoint/model_149999.pt" \
  "$ROOT/tools/phase_b_camera_probe.py"; do
  [[ -e $required ]] || { echo "required input missing: $required" >&2; exit 66; }
done

[[ -e $OUT ]] && { echo "run output already exists; refusing to overwrite evidence: $OUT" >&2; exit 73; }

CK=$(sha256sum "$INPUTS/checkpoint/model_149999.pt" | awk '{print $1}')
[[ $CK == a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450 ]] \
  || { echo "checkpoint sha256 mismatch: $CK" >&2; exit 65; }

sudo docker image inspect "$IMAGE" > /dev/null 2>&1 || { echo "image not present: $IMAGE" >&2; exit 66; }
if sudo docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "a container named $CONTAINER already exists; pick another run id" >&2
  exit 73
fi
# Timings are only comparable on a GPU no other run of this task is using.
if sudo docker ps --format '{{.Names}}' | grep -qE '^vla-phase-[ab]-'; then
  echo "another vla-phase container is still running; refusing to measure alongside it" >&2
  exit 75
fi
# The host is shared with machine-dog work. phase_b_vla_resident.sh sets VLA_ALLOW_GPU_BUSY=1 on purpose.
GPU_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
if (( GPU_USED > 1000 )) && [[ ${VLA_ALLOW_GPU_BUSY:-0} != 1 ]]; then
  echo "GPU already has ${GPU_USED} MiB in use by something else; refusing to measure" >&2
  exit 75
fi

# The root filesystem is shared with other projects' runs and was 96 % full on 2026-09-14. Refuse to
# start below MIN_FREE_GB (checked before mkdir, so a refusal does not burn the run id), and stop this
# run's own container if free space falls below ABORT_FREE_GB while it is running.
MIN_FREE_GB=${VLA_MIN_FREE_GB:-6}
ABORT_FREE_GB=${VLA_ABORT_FREE_GB:-2}
SHUTDOWN_GRACE_S=${VLA_SHUTDOWN_GRACE_S:-180}
free_gb() { df -Pk "$ROOT" | awk 'NR==2 {printf "%d", $4 / 1048576}'; }
FREE_NOW=$(free_gb)
(( FREE_NOW >= MIN_FREE_GB )) || { echo "only ${FREE_NOW} GB free on $ROOT; need ${MIN_FREE_GB} GB" >&2; exit 75; }

mkdir -p "$OUT" "$ROOT/home"
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_before.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_before.txt"
df -Pk "$ROOT" > "$OUT/disk_before.txt"
# Earlier containers left uid-1234 files under home/ that the host user cannot chmod, so use sudo.
sudo chmod -R a+rwX "$OUT" "$ROOT/home"

# Host-side sampler: system RAM (used and available, MiB) and free disk, every 2 s. The page cache is
# excluded from "used", so this is the figure that answers whether host memory is actually short.
(
  echo "unix_s,mem_used_mib,mem_available_mib,disk_free_gb"
  while sleep 2; do
    read -r used avail < <(free -m | awk '/^Mem:/ {print $3, $7}')
    disk=$(free_gb)
    echo "$(date +%s),$used,$avail,$disk"
    if (( disk < ABORT_FREE_GB )); then
      echo "disk free ${disk} GB < ${ABORT_FREE_GB} GB; stopping $CONTAINER" > "$OUT/DISK_ABORT"
      sudo docker kill "$CONTAINER" > /dev/null 2>&1 || true
    fi
    # The measurement is complete once camera_probe.json exists; do not let a hung shutdown hold the
    # GPU for the rest of the wall limit.
    if [[ -f $OUT/camera_probe.json && ! -f $OUT/SHUTDOWN_FORCED ]] \
        && (( $(date +%s) - $(stat -c %Y "$OUT/camera_probe.json") > SHUTDOWN_GRACE_S )); then
      echo "container still running ${SHUTDOWN_GRACE_S} s after camera_probe.json; stopped" > "$OUT/SHUTDOWN_FORCED"
      sudo docker kill "$CONTAINER" > /dev/null 2>&1 || true
    fi
  done
) > "$OUT/host_samples.csv" 2>/dev/null &
SAMPLER=$!
trap 'kill "$SAMPLER" 2>/dev/null || true' EXIT

PYPATH=/workspace/inputs/lite3_sim_bridge:/workspace/inputs/v12_runtime/source/rsl_rl:/workspace/inputs/v12_runtime/source/robot_lab:$LAB/isaaclab:$LAB/isaaclab_tasks:$LAB/isaaclab_rl:$LAB/isaaclab_assets

set +e
sudo timeout --signal=TERM --kill-after=60 "${WALL_LIMIT}s" \
  docker run --rm --name "$CONTAINER" \
    --gpus all --network host \
    -v "$ROOT:/workspace" \
    -e HOME=/workspace/home -e PYTHONPATH="$PYPATH" \
    -e OMNI_KIT_ACCEPT_EULA=YES -e PRIVACY_CONSENT=N -e KMP_DUPLICATE_LIB_OK=TRUE \
    --entrypoint /isaac-sim/python.sh "$IMAGE" \
    /workspace/tools/phase_b_camera_probe.py \
      --config "$CONFIG" \
      --camera-hz "$CAMERA_HZ" \
      --steps "$STEPS" \
      --output-dir "/workspace/runs/$RUN_ID" \
      --checkpoint /workspace/inputs/checkpoint/model_149999.pt \
      --vendored-rsl-rl /workspace/inputs/v12_runtime/source/rsl_rl \
      --device cuda:0 \
      --physx-buffers "$PHYSX_BUFFERS" \
      --rendering-mode "$RENDERING_MODE" \
    > "$OUT/probe.log" 2>&1
RC=$?
set -e
kill "$SAMPLER" 2>/dev/null || true
# timeout kills the docker client, not the container: phase_b_none_v2 kept holding the GPU afterwards.
if sudo docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  sudo docker kill "$CONTAINER" > /dev/null 2>&1 || true
  echo "container still running after docker run returned rc=$RC; killed by driver" > "$OUT/CONTAINER_KILLED_BY_DRIVER"
fi

sudo chown -R "$(id -u):$(id -g)" "$OUT" 2>/dev/null || true
df -Pk "$ROOT" > "$OUT/disk_after.txt"
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_after.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_after.txt"
echo "$RC" > "$OUT/exit_code"

echo "== probe exit $RC =="
tail -40 "$OUT/probe.log"
echo "== unrelated containers unchanged? =="
diff "$OUT/containers_before.txt" "$OUT/containers_after.txt" && echo "  identical"

# Isaac Sim can die during start-up and still exit 0, so trust the artifact, not the code.
STATUS=incomplete
if [[ -f $OUT/camera_probe.json ]]; then
  STATUS=complete
elif [[ $RC -eq 0 ]]; then
  echo "WARNING: exit code 0 but no camera_probe.json - the probe did not finish" >&2
  RC=70
fi
[[ -f $OUT/DISK_ABORT ]] && { STATUS=disk_abort; cat "$OUT/DISK_ABORT" >&2; }
[[ -f $OUT/SHUTDOWN_FORCED ]] && cat "$OUT/SHUTDOWN_FORCED" >&2
PHYSX_WARNINGS=$(grep -ciE 'overflow|exceed(ed|s)? .*(capacity|buffer)|increase .*gpu_' "$OUT/probe.log" || true)
echo "$PHYSX_WARNINGS" > "$OUT/physx_buffer_warning_count"
echo "PHASE_B_RUN_DONE rc=$RC status=$STATUS config=$CONFIG camera_hz=$CAMERA_HZ physx=$PHYSX_BUFFERS render=$RENDERING_MODE physx_buffer_warnings=$PHYSX_WARNINGS"

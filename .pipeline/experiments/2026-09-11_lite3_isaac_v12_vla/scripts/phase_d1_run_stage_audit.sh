#!/usr/bin/env bash
# Phase D.1b on the container host: the single stage-audit Isaac start (InteriorAgent kujiale_0031; no robot, no VLA).
#
#   nohup setsid bash scripts/phase_d1_run_stage_audit.sh RUN_ID > driver_logs/RUN_ID.log 2>&1 < /dev/null &
#
# Authorised by Dr Sun 2026-09-15: 1 download + 1 Isaac start, run beside the vendor isaac-sim container with
# per-process GPU memory. Thresholds: phase_d/stage_audit_thresholds_d1b.json (sha256 pinned below).
# Builds, pulls and deletes nothing. Never touches containers or processes it did not start: the only container it may
# kill is its own, by name. The vendor container is observed, never signalled.
set -euo pipefail

[[ $# -eq 1 ]] || { echo "usage: $0 RUN_ID" >&2; exit 64; }
RUN_ID=$1
[[ $RUN_ID =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { echo "bad run id" >&2; exit 64; }
SELF=$(readlink -f "$0")

ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
SCENES=$ROOT/scenes/interioragent_ac599fe2
SCENE_DIR=$SCENES/kujiale_0031
OUT=$ROOT/runs/$RUN_ID
IMAGE=e01-walking-isaaclab:20260905
CONTAINER=vla-phase-d-$RUN_ID
VENDOR=isaac-sim
LAB=/isaac-sim/kit/python/lib/python3.11/site-packages/isaaclab/source
THRESHOLDS_SHA256=227d54ac4bad306e00bafa581f798c4ea4243ef160c69f1409479f2b25660466
MAX_FOREIGN_MIB=4000
MAX_UNLISTED_MIB=300
# Test hooks for the CPU rehearsal only (fake docker/nvidia-smi); the real run uses the defaults.
CGROUP_ROOT=${VLA_CGROUP_ROOT:-/proc}
AFTER_RECORD_GRACE_S=${VLA_AFTER_RECORD_GRACE_S:-180}
cd "$ROOT"

for required in phase_d/stage_audit.py phase_d/stage_audit_lib.py phase_d/stage_audit_thresholds_d1b.json \
  phase_d/fusion_isaac_c8.json phase_c/episodes/c_red_box_ahead_v1.json tools/phase_b_camera_probe.py \
  setup/phase_d1_interioragent/kujiale_0031_val_unseen_episodes.json scripts/phase_d1b_stage_audit_summary.py \
  "$SCENE_DIR/kujiale_0031.usda" "$SCENE_DIR/SHA256SUMS.txt" "$SCENES/kujiale_0031_download_record.json"; do
  [[ -e $required ]] || { echo "required input missing: $required" >&2; exit 66; }
done
[[ $(sha256sum phase_d/stage_audit_thresholds_d1b.json | awk '{print $1}') == "$THRESHOLDS_SHA256" ]] \
  || { echo "thresholds file is not the frozen one" >&2; exit 65; }
WALL_LIMIT=$(python3 -c 'import json; print(int(json.load(open("phase_d/stage_audit_thresholds_d1b.json"))["host"]["wall_limit_s"]))')
[[ -e $OUT ]] && { echo "run output already exists; refusing to overwrite evidence: $OUT" >&2; exit 73; }
free_gb() { df -Pk "$ROOT" | awk 'NR==2 {printf "%d", $4 / 1048576}'; }
(( $(free_gb) >= 6 )) || { echo "only $(free_gb) GB free" >&2; exit 75; }
sudo docker image inspect "$IMAGE" > /dev/null 2>&1 || { echo "image not present: $IMAGE" >&2; exit 66; }
if sudo docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then echo "container $CONTAINER exists" >&2; exit 73; fi
if sudo docker ps --format '{{.Names}}' | grep -qE '^vla-phase-[a-d]-'; then echo "another vla-phase container is running" >&2; exit 75; fi

echo "== $(date -u +%FT%TZ) verifying the scene copy against SHA256SUMS.txt"
[[ $(wc -l < "$SCENE_DIR/SHA256SUMS.txt") -eq 451 ]] || { echo "SHA256SUMS.txt does not list 451 files" >&2; exit 65; }
( cd "$SCENE_DIR" && sha256sum --check --quiet SHA256SUMS.txt ) || { echo "scene copy failed verification" >&2; exit 65; }

# Which docker container a host pid belongs to (first 12 hex digits of the id), or '-'.
cid_of() { sed -nE 's/.*docker[-/]([0-9a-f]{12})[0-9a-f]{52}.*/\1/p' "$CGROUP_ROOT/$1/cgroup" 2>/dev/null | head -1 || true; }
apps_line() {  # pid:MiB:container12;...
  local pid mem cid out=
  while IFS=, read -r pid mem; do
    pid=${pid// /}; mem=${mem// /}
    [[ -n $pid ]] || continue
    cid=$(cid_of "$pid"); out+="$pid:$mem:${cid:--};"
  done < <(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits)
  echo "$out"
}

VENDOR_ID=$(sudo docker inspect -f '{{.Id}}' "$VENDOR" 2>/dev/null | cut -c1-12 || true)
BEFORE=$(apps_line)
FOREIGN_MIB=0
for entry in ${BEFORE//;/ }; do
  IFS=: read -r pid mem cid <<< "$entry"
  if [[ -z $VENDOR_ID || $cid != "$VENDOR_ID" ]]; then
    echo "GPU process $pid ($mem MiB, container ${cid}) is not inside the vendor container; refusing to start" >&2; exit 75
  fi
  FOREIGN_MIB=$((FOREIGN_MIB + mem))
done
(( FOREIGN_MIB <= MAX_FOREIGN_MIB )) || { echo "vendor processes hold $FOREIGN_MIB MiB > $MAX_FOREIGN_MIB" >&2; exit 75; }
DEVICE_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
[[ $DEVICE_USED =~ ^[0-9]+$ ]] || { echo "cannot read device memory: '$DEVICE_USED'" >&2; exit 75; }
(( DEVICE_USED - FOREIGN_MIB <= MAX_UNLISTED_MIB )) \
  || { echo "device uses $DEVICE_USED MiB but listed processes only $FOREIGN_MIB MiB" >&2; exit 75; }

mkdir -p "$OUT/audit" "$ROOT/home"
sha256sum phase_d/stage_audit.py phase_d/stage_audit_lib.py phase_d/stage_audit_thresholds_d1b.json \
  phase_d/fusion_isaac_c8.json phase_c/episodes/c_red_box_ahead_v1.json tools/phase_b_camera_probe.py \
  setup/phase_d1_interioragent/kujiale_0031_val_unseen_episodes.json scripts/phase_d1b_stage_audit_summary.py \
  "$SCENE_DIR/kujiale_0031.usda" "$SCENE_DIR/SHA256SUMS.txt" "$SCENES/kujiale_0031_download_record.json" "$SELF" \
  > "$OUT/executed_source_sha256.txt"
printf '%q ' "$SELF" "$RUN_ID" > "$OUT/command.txt"; echo >> "$OUT/command.txt"
echo "vendor_container_id12=$VENDOR_ID foreign_mib_before=$FOREIGN_MIB device_used_before=$DEVICE_USED wall_limit_s=$WALL_LIMIT" >> "$OUT/command.txt"
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_before.csv"
echo "$BEFORE" > "$OUT/compute_apps_before.txt"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}} {{.ID}}' > "$OUT/containers_before.txt"
df -Pk "$ROOT" > "$OUT/disk_before.txt"
sudo chmod -R a+rwX "$OUT" "$ROOT/home"

(
  # The subshell inherits set -euo pipefail; one failed nvidia-smi call must cost one sample, not the sampler.
  set +euo pipefail
  echo "unix_s,device_used_mib,util_pct,apps"
  while sleep 1; do
    dev=$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
    [[ $dev =~ ^[0-9]+,[0-9]+$ ]] || dev=","
    echo "$(date +%s.%N | cut -c1-14),$dev,$(apps_line 2>/dev/null)"
  done
) > "$OUT/samples.csv" 2>/dev/null &
SAMPLER=$!
SIM_PID=
cleanup() {
  kill "$SAMPLER" 2>/dev/null || true
  if sudo docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    sudo docker kill "$CONTAINER" > /dev/null 2>&1 || true
    echo "container still running at driver exit; killed" > "$OUT/CONTAINER_KILLED_BY_DRIVER"
  fi
  [[ -n $SIM_PID ]] && kill -TERM -- "-$SIM_PID" 2>/dev/null || true
  true
}
trap cleanup EXIT

echo "== $(date -u +%FT%TZ) starting $CONTAINER (wall limit ${WALL_LIMIT}s)"
setsid sudo timeout --signal=TERM --kill-after=60 "${WALL_LIMIT}s" \
  docker run --rm --name "$CONTAINER" --gpus all --network host -v "$ROOT:/workspace" \
    -e HOME=/workspace/home -e PYTHONPATH="$LAB/isaaclab" \
    -e OMNI_KIT_ACCEPT_EULA=YES -e PRIVACY_CONSENT=N -e KMP_DUPLICATE_LIB_OK=TRUE \
    --entrypoint /isaac-sim/python.sh "$IMAGE" \
    /workspace/phase_d/stage_audit.py \
      --scene-usd /workspace/scenes/interioragent_ac599fe2/kujiale_0031/kujiale_0031.usda \
      --episodes /workspace/setup/phase_d1_interioragent/kujiale_0031_val_unseen_episodes.json \
      --thresholds /workspace/phase_d/stage_audit_thresholds_d1b.json \
      --fusion-config /workspace/phase_d/fusion_isaac_c8.json \
      --chase-episode /workspace/phase_c/episodes/c_red_box_ahead_v1.json \
      --tools-dir /workspace/tools --output-dir "/workspace/runs/$RUN_ID/audit" \
  > "$OUT/sim.log" 2>&1 &
SIM_PID=$!
for _ in $(seq 1 60); do
  sudo docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" && break
  sleep 1
done
sudo docker inspect -f '{{.Id}}' "$CONTAINER" 2>/dev/null | cut -c1-12 > "$OUT/container_id12.txt" || true

# Kit can hang in shutdown after the audit has written its record: give it 180 s after the marker, then stop our own
# container by name (the record is already on disk and hashed in the marker).
MARKER_SEEN=
while kill -0 "$SIM_PID" 2>/dev/null; do
  if [[ -e $OUT/audit/STAGE_AUDIT_COMPLETE || -e $OUT/audit/STAGE_AUDIT_ERROR ]]; then
    MARKER_SEEN=${MARKER_SEEN:-$(date +%s)}
    if (( $(date +%s) - MARKER_SEEN > AFTER_RECORD_GRACE_S )); then
      sudo docker kill "$CONTAINER" > /dev/null 2>&1 || true
      echo "audit record written; Kit still running ${AFTER_RECORD_GRACE_S} s later; container killed" > "$OUT/KILLED_AFTER_RECORD"
      break
    fi
  fi
  sleep 5
done
set +e
wait "$SIM_PID"; SIM_RC=$?; SIM_PID=
set -e
kill "$SAMPLER" 2>/dev/null || true
if sudo docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  sudo docker kill "$CONTAINER" > /dev/null 2>&1 || true
  echo "container still running after docker run returned; killed" > "$OUT/CONTAINER_KILLED_BY_DRIVER"
fi
sudo chown -R "$(id -u):$(id -g)" "$OUT" 2>/dev/null || true
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_after.csv"
apps_line > "$OUT/compute_apps_after.txt"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}} {{.ID}}' > "$OUT/containers_after.txt"
df -Pk "$ROOT" > "$OUT/disk_after.txt"
echo "$SIM_RC" > "$OUT/exit_code"
echo "== unrelated containers unchanged? =="
diff <(grep -v "^$CONTAINER " "$OUT/containers_before.txt" | awk '{print $1, $2, $NF}') \
     <(grep -v "^$CONTAINER " "$OUT/containers_after.txt" | awk '{print $1, $2, $NF}') && echo "  identical"
( cd "$OUT" && find audit -type f -print0 | sort -z | xargs -0 sha256sum > manifest.sha256 ) || true
set +e
python3 scripts/phase_d1b_stage_audit_summary.py --run-dir "$OUT" --thresholds phase_d/stage_audit_thresholds_d1b.json
SUMMARY_RC=$?
set -e
echo "PHASE_D1B_AUDIT_DONE run=$RUN_ID docker_rc=$SIM_RC complete=$([[ -e $OUT/audit/STAGE_AUDIT_COMPLETE ]] && echo yes || echo no) summary_rc=$SUMMARY_RC"

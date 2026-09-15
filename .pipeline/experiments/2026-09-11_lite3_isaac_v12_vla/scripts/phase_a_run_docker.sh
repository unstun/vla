#!/usr/bin/env bash
# Phase A on a container host: stand the V12 locomotion loop up with the SCRIPTED qualification
# schedule on a flat course, inside the existing Isaac Lab image.
#
#   phase_a_run_docker.sh RUN_ID [SIM_SECONDS]
#
# Inference only: no training, no optimiser, no checkpoint write, no camera (enable_cameras stays False
# until Phase B). Uses only images that already exist on the host; builds nothing, pulls nothing,
# deletes nothing, and never touches the unowned `isaac-sim` streaming container.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 RUN_ID [SIM_SECONDS]" >&2
  exit 64
fi
RUN_ID=$1
SIM_SECONDS=${2:-12}

[[ $RUN_ID =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { echo "run id must be lowercase alphanumeric with - or _" >&2; exit 64; }
if [[ ! $SIM_SECONDS =~ ^[0-9]+$ ]] || (( SIM_SECONDS < 9 || SIM_SECONDS > 30 )); then
  echo "SIM_SECONDS must be an integer in [9, 30] (the scripted schedule is 8.75 s)" >&2
  exit 64
fi

ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
INPUTS=$ROOT/inputs
OUT=$ROOT/runs/$RUN_ID
IMAGE=${VLA_IMAGE:-e01-walking-isaaclab:20260905}
CONTAINER=vla-phase-a-$RUN_ID
WALL_LIMIT=${VLA_WALL_LIMIT:-1500}
CONTAINER_UID=${VLA_CONTAINER_UID:-1234}   # the `isaac-sim` user baked into the image
TELEMETRY_PORT=${VLA_TELEMETRY_PORT:-46200}
COMMAND_PORT=${VLA_COMMAND_PORT:-46201}
# Isaac Lab ships inside the PyPI isaaclab wheel as a whole source tree; these four roots put it on sys.path.
LAB=/isaac-sim/kit/python/lib/python3.11/site-packages/isaaclab/source

for required in \
  "$INPUTS/lite3_sim_bridge/lite3_sim_bridge/run_isaac_v12_fallback.py" \
  "$INPUTS/v12_runtime/source/rsl_rl/rsl_rl/env/vec_env.py" \
  "$INPUTS/v12_runtime/source/robot_lab/robot_lab/tasks/lite3/env_cfg.py" \
  "$INPUTS/checkpoint/model_149999.pt"; do
  [[ -e $required ]] || { echo "required input missing: $required" >&2; exit 66; }
done

[[ -e $OUT ]] && { echo "run output already exists; refusing to overwrite evidence: $OUT" >&2; exit 73; }

CK=$(sha256sum "$INPUTS/checkpoint/model_149999.pt" | awk '{print $1}')
[[ $CK == a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450 ]] \
  || { echo "checkpoint sha256 mismatch: $CK" >&2; exit 65; }

sudo docker image inspect "$IMAGE" > /dev/null 2>&1 || { echo "image not present on this host: $IMAGE" >&2; exit 66; }

for port in "$TELEMETRY_PORT" "$COMMAND_PORT"; do
  if ss -ltn 2>/dev/null | grep -q ":$port "; then
    echo "port $port is already in use; refusing to collide with another job" >&2
    exit 69
  fi
done

if sudo docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "a container named $CONTAINER already exists; pick another run id" >&2
  exit 73
fi

mkdir -p "$OUT" "$ROOT/home"

nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_before.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_before.txt"

# The image runs as its own unprivileged user (isaac-sim, uid 1234) and /isaac-sim is executable only
# by it, so --user with the host uid fails on python.sh itself. Keep the image's user and instead open
# the two directories it must write: its HOME (Omniverse caches) and this run's output. chmod rather
# than chown, because the host shell also writes here (adapter.log, the nvidia-smi snapshots) and a
# chown would lock one side or the other out whichever order they ran in.
IMAGE_USER=$(sudo docker image inspect "$IMAGE" --format '{{.Config.User}}')
if [[ $IMAGE_USER != isaac-sim ]]; then
  echo "unexpected image user '$IMAGE_USER'; this script assumes isaac-sim (uid $CONTAINER_UID)" >&2
  exit 70
fi
# sudo: once a container has run, home/ holds uid-1234 files the host user cannot chmod, and under
# set -e a plain chmod aborted the driver before docker started (burned run phase_b_none_v1).
sudo chmod -R a+rwX "$OUT" "$ROOT/home"

PYPATH=/workspace/inputs/lite3_sim_bridge:/workspace/inputs/v12_runtime/source/rsl_rl:/workspace/inputs/v12_runtime/source/robot_lab:$LAB/isaaclab:$LAB/isaaclab_tasks:$LAB/isaaclab_rl:$LAB/isaaclab_assets

# Prove which source the interpreter actually imports, before anything physical happens.
sudo docker run --rm --name "${CONTAINER}-identity" \
  --network host \
  -v "$ROOT:/workspace" \
  -e HOME=/workspace/home -e PYTHONPATH="$PYPATH" \
  -e OMNI_KIT_ACCEPT_EULA=YES -e PRIVACY_CONSENT=N -e KMP_DUPLICATE_LIB_OK=TRUE \
  --entrypoint /isaac-sim/python.sh "$IMAGE" -c '
import hashlib, json, os, sys
record = {"python": sys.version, "pythonpath": os.environ.get("PYTHONPATH"), "modules": {}}
for name in ("lite3_sim_bridge", "robot_lab", "rsl_rl", "isaaclab", "isaaclab_tasks", "isaaclab_rl"):
    try:
        module = __import__(name)
    except Exception as error:
        record["modules"][name] = {"error": f"{type(error).__name__}: {error}"}
        continue
    path = getattr(module, "__file__", None)
    entry = {"file": path, "version": getattr(module, "__version__", None)}
    if path and os.path.isfile(path):
        entry["sha256"] = hashlib.sha256(open(path, "rb").read()).hexdigest()
    record["modules"][name] = entry
adapter = os.path.join(os.path.dirname(record["modules"]["lite3_sim_bridge"].get("file") or ""), "run_isaac_v12_fallback.py")
if os.path.isfile(adapter):
    record["adapter_file"] = adapter
    record["adapter_sha256"] = hashlib.sha256(open(adapter, "rb").read()).hexdigest()
    record["adapter_matches_accepted_run"] = record["adapter_sha256"] == "6104fe686bcd3bc0480c0afc1b41dde84d1a35d45a6dbbe9e51d98e6719ba3e3"
open("/workspace/runs/'"$RUN_ID"'/runtime_import_identity.json", "w").write(json.dumps(record, indent=2))
print(json.dumps(record, indent=2))
' 2>&1 | tee "$OUT/identity.log" | grep -v '^\[' || true

set +e
sudo timeout --signal=TERM --kill-after=60 "${WALL_LIMIT}s" \
  docker run --rm --name "$CONTAINER" \
    --gpus all --network host \
    -v "$ROOT:/workspace" \
    -e HOME=/workspace/home -e PYTHONPATH="$PYPATH" \
    -e OMNI_KIT_ACCEPT_EULA=YES -e PRIVACY_CONSENT=N -e KMP_DUPLICATE_LIB_OK=TRUE \
    --entrypoint /isaac-sim/python.sh "$IMAGE" \
    -m lite3_sim_bridge.run_isaac_v12_fallback \
      --mode qualification \
      --course flat \
      --output-dir "/workspace/runs/$RUN_ID" \
      --checkpoint /workspace/inputs/checkpoint/model_149999.pt \
      --vendored-rsl-rl /workspace/inputs/v12_runtime/source/rsl_rl \
      --duration-seconds "$SIM_SECONDS" \
      --device cuda:0 \
      --telemetry-port "$TELEMETRY_PORT" \
      --command-port "$COMMAND_PORT" \
    > "$OUT/adapter.log" 2>&1
RC=$?
set -e

# The container wrote this directory as uid 1234; hand the evidence back to the invoking user.
sudo chown -R "$(id -u):$(id -g)" "$OUT" 2>/dev/null || true
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_after.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_after.txt"
echo "$RC" > "$OUT/exit_code"

echo "== adapter exit $RC =="
tail -60 "$OUT/adapter.log"
echo "== unrelated containers unchanged? =="
diff "$OUT/containers_before.txt" "$OUT/containers_after.txt" && echo "  identical"
echo "== artifacts =="
ls -la "$OUT"

# Isaac Sim can die during extension startup and still return 0, which reads as success and is not.
# The run is only complete if the adapter wrote its own report; that is the signal we trust.
REPORT=$OUT/qualification_report.json
STATUS=incomplete
if [[ -f $REPORT ]]; then
  STATUS=complete
elif [[ $RC -eq 0 ]]; then
  echo "WARNING: exit code 0 but no qualification_report.json - the adapter did not finish" >&2
  RC=70
fi
echo "PHASE_A_RUN_DONE rc=$RC status=$STATUS"

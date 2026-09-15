#!/usr/bin/env bash
# Phase A: stand the V12 locomotion loop up with the SCRIPTED qualification schedule on a flat course.
# Runs ON the execution host, inside a native conda Isaac Lab environment.
#
#   phase_a_run_native.sh RUN_ID [SIM_SECONDS]
#
# Inference only: no training, no optimiser, no checkpoint is written, no camera is enabled.
# It never kills a process it does not own and never touches another project's files.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 RUN_ID [SIM_SECONDS]" >&2
  exit 64
fi
RUN_ID=$1
SIM_SECONDS=${2:-12}

[[ $RUN_ID =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { echo "run id must be lowercase alphanumeric with - or _" >&2; exit 64; }
# The scripted schedule is 8.75 s; anything past ~20 s is just standing still and burning GPU time.
if [[ ! $SIM_SECONDS =~ ^[0-9]+$ ]] || (( SIM_SECONDS < 9 || SIM_SECONDS > 30 )); then
  echo "SIM_SECONDS must be an integer in [9, 30] (the scripted schedule is 8.75 s)" >&2
  exit 64
fi

ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
INPUTS=$ROOT/inputs
OUT=$ROOT/runs/$RUN_ID
WALL_LIMIT=${VLA_WALL_LIMIT:-900}          # hard ceiling; Isaac start-up dominates a 9 s run
CONDA_SH=${VLA_CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}
CONDA_ENV=${VLA_CONDA_ENV:-isaaclab}
TELEMETRY_PORT=${VLA_TELEMETRY_PORT:-46200}
COMMAND_PORT=${VLA_COMMAND_PORT:-46201}

for required in \
  "$INPUTS/lite3_sim_bridge/lite3_sim_bridge/run_isaac_v12_fallback.py" \
  "$INPUTS/v12_runtime/source/rsl_rl/rsl_rl/env/vec_env.py" \
  "$INPUTS/v12_runtime/source/robot_lab/robot_lab/tasks/lite3/env_cfg.py" \
  "$INPUTS/checkpoint/model_149999.pt" \
  "$CONDA_SH"; do
  [[ -e $required ]] || { echo "required input missing: $required" >&2; exit 66; }
done

[[ -e $OUT ]] && { echo "run output already exists; refusing to overwrite evidence: $OUT" >&2; exit 73; }

CK=$(sha256sum "$INPUTS/checkpoint/model_149999.pt" | awk '{print $1}')
[[ $CK == a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450 ]] \
  || { echo "checkpoint sha256 mismatch: $CK" >&2; exit 65; }

for port in "$TELEMETRY_PORT" "$COMMAND_PORT"; do
  if ss -ltn 2>/dev/null | grep -q ":$port "; then
    echo "port $port is already in use; refusing to collide with another job" >&2
    exit 69
  fi
done

# A leftover runner from an earlier attempt of THIS task would hold the ports. Report it; never kill it,
# and never touch processes belonging to the Isaac container or to another project.
if pgrep -f 'lite3_sim_bridge.run_isaac_v12_fallback' > /dev/null; then
  echo "a previous run_isaac_v12_fallback process is still alive:" >&2
  pgrep -af 'lite3_sim_bridge.run_isaac_v12_fallback' >&2
  echo "stop it yourself before starting a new attempt" >&2
  exit 69
fi

mkdir -p "$OUT"

# shellcheck source=/dev/null
source "$CONDA_SH"
conda activate "$CONDA_ENV"
export OMNI_KIT_ACCEPT_EULA=YES
export PRIVACY_CONSENT=N
export KMP_DUPLICATE_LIB_OK=TRUE
export PYTHONPATH="$INPUTS/lite3_sim_bridge:$INPUTS/v12_runtime/source/rsl_rl:$INPUTS/v12_runtime/source/robot_lab"

# Prove which source this interpreter actually imports. Editable installs register meta-path finders that
# run BEFORE sys.path, so an installed robot_lab or rsl_rl can silently shadow the staged V12 copy.
python - > "$OUT/runtime_import_identity.json" <<'PY'
import hashlib, json, os, sys

record = {"python": sys.version, "pythonpath": os.environ.get("PYTHONPATH"), "modules": {}}
for name in ("lite3_sim_bridge", "robot_lab", "rsl_rl", "isaaclab", "isaaclab_tasks", "isaaclab_rl"):
    try:
        module = __import__(name)
    except Exception as error:  # noqa: BLE001 - the failure itself is the evidence
        record["modules"][name] = {"error": f"{type(error).__name__}: {error}"}
        continue
    path = getattr(module, "__file__", None)
    entry = {"file": path, "version": getattr(module, "__version__", None)}
    if path and os.path.isfile(path):
        entry["sha256"] = hashlib.sha256(open(path, "rb").read()).hexdigest()
    record["modules"][name] = entry

adapter = os.path.join(
    os.path.dirname(record["modules"]["lite3_sim_bridge"].get("file", "")),
    "run_isaac_v12_fallback.py",
)
if os.path.isfile(adapter):
    record["adapter_file"] = adapter
    record["adapter_sha256"] = hashlib.sha256(open(adapter, "rb").read()).hexdigest()
    # The hash the accepted machine-dog-nav run native_full02 actually loaded.
    record["adapter_matches_accepted_run"] = (
        record["adapter_sha256"] == "6104fe686bcd3bc0480c0afc1b41dde84d1a35d45a6dbbe9e51d98e6719ba3e3"
    )
print(json.dumps(record, indent=2))
PY
cat "$OUT/runtime_import_identity.json"

nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_before.csv"

set +e
timeout --signal=TERM --kill-after=60 "${WALL_LIMIT}s" \
  python -m lite3_sim_bridge.run_isaac_v12_fallback \
    --mode qualification \
    --course flat \
    --output-dir "$OUT" \
    --checkpoint "$INPUTS/checkpoint/model_149999.pt" \
    --vendored-rsl-rl "$INPUTS/v12_runtime/source/rsl_rl" \
    --duration-seconds "$SIM_SECONDS" \
    --device cuda:0 \
    --telemetry-port "$TELEMETRY_PORT" \
    --command-port "$COMMAND_PORT" \
    > "$OUT/adapter.log" 2>&1
RC=$?
set -e

nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_after.csv"
echo "$RC" > "$OUT/exit_code"
echo "== adapter exit $RC =="
tail -40 "$OUT/adapter.log"
echo "== artifacts =="
ls -la "$OUT"
echo "PHASE_A_RUN_DONE rc=$RC"

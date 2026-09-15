#!/usr/bin/env bash
# Launch the official InternNav evaluator for one camera condition.
#
# Invoke THROUGH the process-group supervisor from the experiment root:
#   python3 scripts/run_job.py --seconds 1800 <run_id> -- \
#     bash public_scenes/requests/2026-09-10_lite3_camera_ablation/run_cam_eval.sh <condition> <run_id>
#
# Entry point, working directory, and evaluator are upstream's own:
#   cd work/InternNav && python scripts/eval/eval.py --config <eval_config>
# where <eval_config> is the condition's eval_config in conditions.json if set (fused conditions),
# else execution.eval_config (public_scenes/configs/habitat_dual_system_cam_cfg.py),
# with CAM_YAML selecting the generated condition YAML and CAM_RUN_DIR the run directory.
set -euo pipefail

COND="${1:?usage: run_cam_eval.sh <condition> <run_id>}"
RUN_ID="${2:?usage: run_cam_eval.sh <condition> <run_id>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LAUNCH="$ROOT/work/InternNav"
PY="$ROOT/official_r2r/official_env_024/bin/python"
REQ_REL="public_scenes/requests/2026-09-10_lite3_camera_ablation"
RUN_REL="public_scenes/runs/$RUN_ID"
RUN_ABS="$ROOT/$RUN_REL"
# Round 5 (2026-09-11): a condition may name its own eval config (fused conditions import the
# fusion plugin); otherwise the shared camera config is used, exactly as in rounds 1-4.
CFG="$(python3 -c "import json,sys; c=json.load(open('$ROOT/$REQ_REL/conditions.json')); print(c['conditions'].get('$COND',{}).get('eval_config') or c['execution']['eval_config'])")"
YAML="public_scenes/configs/vln_cam_${COND}.yaml"
ANN="public_scenes/data/vln_ce/raw_data/public/val_unseen/val_unseen.json.gz"
PRE="$LAUNCH/$REQ_REL/preflight/${COND}.json"

case "$RUN_ID" in
  cam_${COND}_v[0-9]*) ;;
  *) echo "REFUSING: run id '$RUN_ID' must match cam_${COND}_v<k>" >&2; exit 2 ;;
esac
if [ -e "$RUN_ABS" ]; then
  echo "REFUSING: $RUN_REL already exists; use a fresh run id" >&2
  exit 3
fi
if [ ! -f "$PRE" ]; then
  echo "REFUSING: no preflight report at $PRE" >&2
  exit 4
fi
if ! "$PY" -c "import json,sys; r=json.load(open('$PRE')); sys.exit(0 if r['all_stages_passed'] and r['condition']=='$COND' else 1)"; then
  echo "REFUSING: preflight for $COND did not pass all stages" >&2
  exit 5
fi
cd "$LAUNCH"
for f in "$CFG" "$YAML" "$ANN" "$REQ_REL/conditions.json" checkpoints/InternVLA-N1-DualVLN/config.json \
         checkpoints/depth_anything_v2_metric_hypersim_vits.pth \
         public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.glb; do
  [ -e "$f" ] || { echo "REFUSING: missing $f relative to $LAUNCH" >&2; exit 6; }
done

mkdir -p "$RUN_ABS"

# --- record exactly what is about to execute, including the resolved camera geometry
"$PY" - "$RUN_ABS/inputs.json" "$COND" "$RUN_ID" "$LAUNCH" "$CFG" "$YAML" "$ANN" "$PRE" "$PY" <<'PYEOF'
import datetime, hashlib, json, os, sys
out, cond, run_id, launch, cfg, yaml_rel, ann, pre, py = sys.argv[1:]
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()
files = [cfg, yaml_rel, ann, 'public_scenes/requests/2026-09-10_lite3_camera_ablation/conditions.json',
         'scripts/eval/eval.py', 'internnav/habitat_extensions/vln/habitat_vln_evaluator.py',
         'internnav/model/utils/vln_utils.py',
         'public_scenes/requests/2026-09-10_lite3_camera_ablation/fused_camera.py',
         'public_scenes/requests/2026-09-10_lite3_camera_ablation/fused_camera_plugin.py',
         'public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.glb',
         'public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.navmesh']
report = json.load(open(pre))
stages = {s['stage']: s.get('detail') for s in report['stages']}
geom = stages.get('condition habitat config composes to the specified geometry')
render = next((s.get('detail') for s in report['stages'] if str(s.get('stage', '')).startswith('start frame')), None)
json.dump({
    'run_id': run_id, 'request_id': '2026-09-10_lite3_camera_ablation', 'condition': cond,
    'launch_directory': launch,
    'command': f'CAM_YAML={yaml_rel} CAM_RUN_DIR=public_scenes/runs/{run_id} python scripts/eval/eval.py --config {cfg}',
    'python': py, 'started_utc': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'input_sha256': {f: sha(f) for f in files if os.path.exists(f)},
    'preflight_report': pre,
    'resolved_camera_geometry': geom,
    'preflight_measured_sensor_state': render.get('measured_sensor_state') if render else None,
}, open(out, 'w'), indent=2)
PYEOF

"$PY" -c "
import json, torch, habitat, habitat_sim, transformers, diffusers, sys
json.dump({'python': sys.version.split()[0], 'torch': torch.__version__,
           'habitat_lab': habitat.__version__, 'habitat_sim': habitat_sim.__version__,
           'transformers': transformers.__version__, 'diffusers': diffusers.__version__,
           'gpu': torch.cuda.get_device_name(0), 'bf16_supported': torch.cuda.is_bf16_supported()},
          open('$RUN_ABS/environment.json','w'), indent=2)
" 2>/dev/null

# --- whole-run device memory sampling (shared GPU: an isaac-sim container is also resident)
nvidia-smi --query-gpu=timestamp,memory.total,memory.used,memory.free,utilization.gpu \
  --format=csv -l 5 > "$RUN_ABS/gpu_samples_every_5s.csv" 2>/dev/null &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null || true' EXIT

echo "== launching official evaluator: condition=$COND run=$RUN_ID =="
echo "cwd=$(pwd)"
echo "cmd=CAM_YAML=$YAML CAM_RUN_DIR=$RUN_REL $PY scripts/eval/eval.py --config $CFG"
set +e
CAM_YAML="$YAML" CAM_RUN_DIR="$RUN_REL" MAGNUM_LOG=quiet HABITAT_SIM_LOG=quiet \
  "$PY" scripts/eval/eval.py --config "$CFG"
CODE=$?
set -e
echo "EVAL_EXIT_CODE=$CODE"
echo "{\"exit_code\": $CODE, \"condition\": \"$COND\", \"finished_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$RUN_ABS/exit.json"
exit $CODE

#!/usr/bin/env bash
# Launch the official InternNav Habitat evaluator on the frozen public-scene episodes.
#
# Invoke this THROUGH the task-owned process-group supervisor so the 1,800 s GPU
# deadline is enforced and stdout/stderr are captured raw (lead review O3):
#
#   python3 scripts/run_job.py --seconds 1800 <run_id> -- bash public_scenes/scripts/run_public_eval.sh <run_id>
#
# The entry point, working directory and config are upstream's own:
#   cd work/InternNav && python scripts/eval/eval.py --config <derived cfg>
set -euo pipefail

RUN_ID="${1:?usage: run_public_eval.sh <run_id>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LAUNCH="$ROOT/work/InternNav"
PY="$ROOT/official_r2r/official_env_024/bin/python"
RUN_REL="public_scenes/runs/$RUN_ID"
RUN_ABS="$ROOT/$RUN_REL"
CFG="public_scenes/configs/habitat_dual_system_public_cfg.py"
YAML="public_scenes/configs/vln_public_scenes.yaml"
ANN="public_scenes/data/vln_ce/raw_data/public/val_unseen/val_unseen.json.gz"
REPORT="$LAUNCH/public_scenes/setup/preflight_public_report.json"

# --- refuse to start on an unproven or already-used state ----------------------
if [ -e "$RUN_ABS" ]; then
  echo "REFUSING: $RUN_REL already exists; use a fresh run id" >&2
  exit 3
fi
if [ ! -f "$REPORT" ]; then
  echo "REFUSING: no preflight report at $REPORT" >&2
  exit 4
fi
if ! "$PY" -c "import json,sys; sys.exit(0 if json.load(open('$REPORT'))['all_stages_passed'] else 1)"; then
  echo "REFUSING: preflight did not pass all stages" >&2
  exit 5
fi
cd "$LAUNCH"
for f in "$CFG" "$YAML" "$ANN" checkpoints/InternVLA-N1-DualVLN/config.json \
         checkpoints/depth_anything_v2_metric_hypersim_vits.pth \
         public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.glb; do
  [ -e "$f" ] || { echo "REFUSING: missing $f relative to $LAUNCH" >&2; exit 6; }
done

mkdir -p "$RUN_ABS"

# --- record exactly what is about to execute ----------------------------------
{
  echo "{"
  echo "  \"run_id\": \"$RUN_ID\","
  echo "  \"launch_directory\": \"$LAUNCH\","
  echo "  \"command\": \"python scripts/eval/eval.py --config $CFG\","
  echo "  \"python\": \"$PY\","
  echo "  \"started_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"input_sha256\": {"
  first=1
  for f in "$CFG" "$YAML" "$ANN" scripts/eval/eval.py \
           internnav/habitat_extensions/vln/habitat_vln_evaluator.py \
           internnav/model/utils/vln_utils.py \
           public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.glb \
           public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.navmesh ; do
    [ $first -eq 1 ] || echo ","
    first=0
    printf '    "%s": "%s"' "$f" "$(sha256sum "$f" | awk '{print $1}')"
  done
  echo
  echo "  }"
  echo "}"
} > "$RUN_ABS/inputs.json"

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

echo "== launching official evaluator =="
echo "cwd=$(pwd)"
echo "cmd=$PY scripts/eval/eval.py --config $CFG"
set +e
PUBLIC_RUN_DIR="$RUN_REL" MAGNUM_LOG=quiet HABITAT_SIM_LOG=quiet \
  "$PY" scripts/eval/eval.py --config "$CFG"
CODE=$?
set -e
echo "EVAL_EXIT_CODE=$CODE"
echo "{\"exit_code\": $CODE, \"finished_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$RUN_ABS/exit.json"
exit $CODE

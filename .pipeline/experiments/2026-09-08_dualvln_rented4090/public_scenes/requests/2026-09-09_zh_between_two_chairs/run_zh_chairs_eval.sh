#!/usr/bin/env bash
# Launch the official InternNav evaluator for the zh_between_two_chairs request.
#
# Invoke through the process-group supervisor with a 900-second GPU deadline:
#   python3 scripts/run_job.py --seconds 900 <run_id> -- \
#     bash public_scenes/requests/2026-09-09_zh_between_two_chairs/run_zh_chairs_eval.sh <run_id>
set -euo pipefail

RUN_ID="${1:?usage: run_zh_chairs_eval.sh <run_id>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LAUNCH="$ROOT/work/InternNav"
PY="$ROOT/official_r2r/official_env_024/bin/python"
RUN_REL="public_scenes/runs/$RUN_ID"
RUN_ABS="$ROOT/$RUN_REL"
CFG="public_scenes/configs/habitat_dual_system_zh_chairs_cfg.py"
YAML="public_scenes/configs/vln_zh_between_two_chairs.yaml"
ANN="public_scenes/data/vln_ce/raw_data/public/zh_between_two_chairs/zh_between_two_chairs.json.gz"
REQ_DIR="$ROOT/public_scenes/requests/2026-09-09_zh_between_two_chairs"

if [ -e "$RUN_ABS" ]; then
  echo "REFUSING: $RUN_REL already exists; use a fresh run id" >&2
  exit 3
fi

cd "$LAUNCH"
for f in "$CFG" "$YAML" "$ANN" checkpoints/InternVLA-N1-DualVLN/config.json \
         checkpoints/depth_anything_v2_metric_hypersim_vits.pth \
         public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.glb; do
  [ -e "$f" ] || { echo "REFUSING: missing $f relative to $LAUNCH" >&2; exit 6; }
done

mkdir -p "$RUN_ABS"

{
  echo "{"
  echo "  \"run_id\": \"$RUN_ID\","
  echo "  \"request_id\": \"2026-09-09_zh_between_two_chairs\","
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

nvidia-smi --query-gpu=timestamp,memory.total,memory.used,memory.free,utilization.gpu \
  --format=csv -l 5 > "$RUN_ABS/gpu_samples_every_5s.csv" 2>/dev/null &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null || true' EXIT

echo "== launching official evaluator for zh_between_two_chairs =="
echo "cwd=$(pwd)"
echo "cmd=$PY scripts/eval/eval.py --config $CFG"
set +e
ZH_CHAIRS_RUN_DIR="$RUN_REL" MAGNUM_LOG=quiet HABITAT_SIM_LOG=quiet \
  "$PY" scripts/eval/eval.py --config "$CFG"
CODE=$?
set -e
echo "EVAL_EXIT_CODE=$CODE"
echo "{\"exit_code\": $CODE, \"finished_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$RUN_ABS/exit.json"
exit $CODE

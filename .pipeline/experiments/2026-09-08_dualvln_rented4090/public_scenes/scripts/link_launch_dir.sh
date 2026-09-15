#!/usr/bin/env bash
# Make every relative path in the official eval config resolve from the official
# launch directory (work/InternNav), which is what `scripts/eval/eval.py` requires
# (`sys.path.append('.')`).
#
# Lead review O1: the previous launcher ran `cd work/InternNav` while the derived
# config used paths relative to the experiment root, so the config, the assets and
# the auxiliary Depth-Anything checkpoint were all unreachable. These task-owned
# relative links resolve all of them from one explicit root without touching the
# official entry point, the config field values, or any model code.
#
# Created links (all relative, all inside task-owned paths):
#   <EXP>/checkpoints/InternVLA-N1-DualVLN     -> ../models/InternVLA-N1-DualVLN
#   <EXP>/work/InternNav/checkpoints           -> ../../checkpoints
#   <EXP>/work/InternNav/public_scenes         -> ../../public_scenes
#
# After this, upstream's own `model_path: checkpoints/InternVLA-N1-DualVLN` and
# `MODEL_PATH_TO = "checkpoints"` resolve unchanged from the launch directory.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LAUNCH="$ROOT/work/InternNav"

[ -d "$ROOT/models/InternVLA-N1-DualVLN" ] || { echo "MISSING model dir $ROOT/models/InternVLA-N1-DualVLN" >&2; exit 2; }
[ -e "$ROOT/checkpoints/depth_anything_v2_metric_hypersim_vits.pth" ] || { echo "MISSING encoder checkpoint" >&2; exit 3; }
[ -d "$LAUNCH" ] || { echo "MISSING launch dir $LAUNCH" >&2; exit 4; }

ln -sfn ../models/InternVLA-N1-DualVLN "$ROOT/checkpoints/InternVLA-N1-DualVLN"
ln -sfn ../../checkpoints "$LAUNCH/checkpoints"
ln -sfn ../../public_scenes "$LAUNCH/public_scenes"

echo "== resolved from the launch directory =="
cd "$LAUNCH"
for p in \
  checkpoints/depth_anything_v2_metric_hypersim_vits.pth \
  checkpoints/InternVLA-N1-DualVLN/config.json \
  public_scenes/configs \
  public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.glb \
  public_scenes/data/scene_data/public/skokloster-castle/skokloster-castle.navmesh \
  public_scenes/data/scene_data/public/van-gogh-room/van-gogh-room.glb \
  public_scenes/data/scene_data/public/van-gogh-room/van-gogh-room.navmesh ; do
  if [ -e "$p" ]; then echo "OK      $p -> $(readlink -f "$p")"; else echo "MISSING $p"; fi
done
echo LAUNCH_LINKS_DONE

#!/usr/bin/env bash
# Runs the OFFICIAL InternNav Habitat evaluator entry point on the frozen
# 3-episode R2R val_unseen subset. Blocked until the MP3D scene mesh for
# 2azQ1b91cZZ is present (see official_r2r/setup/data_requirements.json).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

RUN_ID="${1:?usage: run_official_eval.sh <run_id>}"
RUN_DIR="$ROOT/official_r2r/runs/$RUN_ID"
test ! -e "$RUN_DIR" || { echo "run dir already exists: $RUN_DIR"; exit 2; }

# Check the blocking input BEFORE creating a run directory, so a blocked attempt
# never leaves an empty directory that could be mistaken for a started run.
SCENE="official_r2r/data/scene_data/mp3d_ce/mp3d/2azQ1b91cZZ/2azQ1b91cZZ.glb"
if [ ! -f "$SCENE" ]; then
  mkdir -p "$ROOT/official_r2r/blocked_attempts"
  REC="$ROOT/official_r2r/blocked_attempts/${RUN_ID}_$(date -u +%Y%m%dT%H%M%SZ).txt"
  {
    echo "attempted_run_id=$RUN_ID"
    echo "utc=$(date -u +%FT%TZ)"
    echo "result=BLOCKED_MISSING_MP3D_SCENE"
    echo "missing_path=$SCENE"
    echo "official_access_step=official_r2r/setup/data_requirements.json"
    echo "note=No episode was executed. No results, videos or metrics exist for this attempt."
  } > "$REC"
  echo "BLOCKED_MISSING_MP3D_SCENE $SCENE"
  echo "See official_r2r/setup/data_requirements.json for the official access step."
  echo "attempt recorded at $REC"
  exit 3
fi

mkdir -p "$RUN_DIR"

ENV_PY="$ROOT/official_r2r/official_env/bin/python"
export OFFICIAL_RUN_DIR="$RUN_DIR"
export OFFICIAL_CKPT="$ROOT/models/InternVLA-N1-DualVLN"
export PYTHONPATH="$ROOT/work/InternNav:${PYTHONPATH:-}"

# Record exactly what is about to execute.
{
  echo "run_id=$RUN_ID"
  echo "utc=$(date -u +%FT%TZ)"
  echo "git_pristine_commit=7a5c62400ac45b313d9b709c740b64191556a242"
  sha256sum official_r2r/configs/habitat_dual_system_subset3_cfg.py \
            official_r2r/configs/vln_r2r_subset3.yaml \
            official_r2r/data/vln_ce/raw_data/r2r_subset3/val_unseen/val_unseen.json.gz \
            work/InternNav/internnav/habitat_extensions/vln/habitat_vln_evaluator.py \
            work/InternNav/scripts/eval/eval.py \
            "$SCENE"
  echo "command=cd work/InternNav && python scripts/eval/eval.py --config ../../official_r2r/configs/habitat_dual_system_subset3_cfg.py"
} > "$RUN_DIR/execution_identity.txt"
cat "$RUN_DIR/execution_identity.txt"

# The official entry expects to run from the InternNav worktree root.
cd "$ROOT/work/InternNav"
exec "$ENV_PY" scripts/eval/eval.py \
  --config "$ROOT/official_r2r/configs/habitat_dual_system_subset3_cfg.py"

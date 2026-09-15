#!/usr/bin/env bash
# Executor-side driver, round 4 (2026-09-10): runs the package's round-1 step-3
# command block unattended for the conditions given on the command line
# (default: the round-4 head-camera proxy pair c5_head_level c6_head_down15) so
# the executor's short per-command ssh timeout cannot interrupt it. The commands
# are the package's, verbatim; only the condition list is narrowed, per the
# package's round-4 step 3. The round-1, round-2, and round-3 drivers are left
# untouched as evidence.
set -uo pipefail
ROOT=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
REQ_REL=public_scenes/requests/2026-09-10_lite3_camera_ablation
if [ "$#" -gt 0 ]; then CONDS=("$@"); else CONDS=(c5_head_level c6_head_down15); fi
cd "$ROOT" || exit 1
echo "== link_launch_dir =="
bash public_scenes/scripts/link_launch_dir.sh 2>&1 | tee "$REQ_REL/preflight/link_launch_dir_round4.txt"
cd "$ROOT/work/InternNav" || exit 1
mkdir -p "$REQ_REL/preflight"
for c in "${CONDS[@]}"; do
  echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) PREFLIGHT $c =="
  CAM_YAML=public_scenes/configs/vln_cam_$c.yaml \
    ../../official_r2r/official_env_024/bin/python \
    "$REQ_REL/preflight_cam.py" --cond "$c" \
    2>&1 | tee "$REQ_REL/preflight/${c}_stdout.txt"
  echo "== $c preflight python exit=${PIPESTATUS[0]} =="
done
echo PREFLIGHT_DRIVER_DONE

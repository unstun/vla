#!/usr/bin/env bash
# Executor-side driver: runs the package's step-3 command block unattended so the
# executor's short per-command ssh timeout cannot interrupt it. Contents are the
# package's commands verbatim.
set -uo pipefail
ROOT=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
REQ_REL=public_scenes/requests/2026-09-10_lite3_camera_ablation
cd "$ROOT" || exit 1
echo "== link_launch_dir =="
bash public_scenes/scripts/link_launch_dir.sh 2>&1 | tee "$REQ_REL/preflight/link_launch_dir.txt"
cd "$ROOT/work/InternNav" || exit 1
mkdir -p "$REQ_REL/preflight"
for c in c1_lite3_rig c2_height_only c3_fov_only c4_raised_mount; do
  echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) PREFLIGHT $c =="
  CAM_YAML=public_scenes/configs/vln_cam_$c.yaml \
    ../../official_r2r/official_env_024/bin/python \
    "$REQ_REL/preflight_cam.py" --cond "$c" \
    2>&1 | tee "$REQ_REL/preflight/${c}_stdout.txt"
  echo "== $c preflight python exit=${PIPESTATUS[0]} =="
done
echo PREFLIGHT_DRIVER_DONE

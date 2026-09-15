#!/usr/bin/env bash
# Executor-side driver, round 6 (2026-09-11): preflights the pitched fused condition
# (default c9_fused_down9) with preflight_fused.py from the official launch directory,
# unattended, so the executor's short per-command ssh timeout cannot interrupt it.
# Earlier round drivers are left untouched as evidence.
set -uo pipefail
ROOT=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
REQ_REL=public_scenes/requests/2026-09-10_lite3_camera_ablation
if [ "$#" -gt 0 ]; then CONDS=("$@"); else CONDS=(c9_fused_down9); fi
cd "$ROOT" || exit 1
echo "== link_launch_dir =="
bash public_scenes/scripts/link_launch_dir.sh 2>&1 | tee "$REQ_REL/preflight/link_launch_dir_round6.txt"
cd "$ROOT/work/InternNav" || exit 1
mkdir -p "$REQ_REL/preflight"
for c in "${CONDS[@]}"; do
  echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) PREFLIGHT $c =="
  CAM_YAML=public_scenes/configs/vln_cam_$c.yaml MAGNUM_LOG=quiet HABITAT_SIM_LOG=quiet \
    ../../official_r2r/official_env_024/bin/python \
    "$REQ_REL/preflight_fused.py" --cond "$c" \
    2>&1 | tee "$REQ_REL/preflight/${c}_stdout.txt"
  echo "== $c preflight python exit=${PIPESTATUS[0]} =="
done
echo PREFLIGHT_DRIVER_DONE

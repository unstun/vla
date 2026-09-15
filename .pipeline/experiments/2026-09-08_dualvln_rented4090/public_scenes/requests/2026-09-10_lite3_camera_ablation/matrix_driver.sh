#!/usr/bin/env bash
# Executor-side driver: runs the package's step-4 matrix command unattended.
# Conditions are passed on the command line because c1/c2 preflights failed the
# floor z-depth sub-check and are held for a lead decision; run_matrix.sh would
# otherwise burn their run ids on run_cam_eval.sh's exit-5 refusal.
set -uo pipefail
ROOT=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
REQ_REL=public_scenes/requests/2026-09-10_lite3_camera_ablation
cd "$ROOT" || exit 1
bash "$REQ_REL/run_matrix.sh" "$@" 2>&1 | tee -a "$REQ_REL/matrix_stdout.txt"
echo "MATRIX_DRIVER_DONE rc=${PIPESTATUS[0]}"

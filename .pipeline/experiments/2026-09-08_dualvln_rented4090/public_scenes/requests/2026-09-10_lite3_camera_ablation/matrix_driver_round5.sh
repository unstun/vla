#!/usr/bin/env bash
# Executor-side driver, round 5 (2026-09-11): runs the package's round-5 matrix command
# unattended from the remote experiment root for the fused-camera pair. Conditions come
# from the command line (c7_fused_level c8_fused_level_720); run_matrix.sh gates on the
# preflight verdict, skips existing run ids, and preserves failures. Output is appended
# to matrix_stdout.txt so all rounds are kept.
set -uo pipefail
ROOT=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
REQ_REL=public_scenes/requests/2026-09-10_lite3_camera_ablation
cd "$ROOT" || exit 1
echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) ROUND5 MATRIX START: $* =="
bash "$REQ_REL/run_matrix.sh" "$@" 2>&1 | tee -a "$REQ_REL/matrix_stdout.txt"
echo "MATRIX_DRIVER_DONE rc=${PIPESTATUS[0]}"

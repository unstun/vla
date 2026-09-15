#!/usr/bin/env bash
# Executor-side driver, round 2 (2026-09-10): runs the package's round-2 step-4
# matrix command unattended from the remote experiment root. Conditions come
# from the command line exactly as the round-2 step names them
# (c1_lite3_rig c2_height_only); run_matrix.sh itself now gates on the preflight
# verdict, skips existing run ids, and preserves failures. Output is appended to
# the round-1 matrix_stdout.txt so both rounds are kept.
set -uo pipefail
ROOT=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
REQ_REL=public_scenes/requests/2026-09-10_lite3_camera_ablation
cd "$ROOT" || exit 1
echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) ROUND2 MATRIX START: $* =="
bash "$REQ_REL/run_matrix.sh" "$@" 2>&1 | tee -a "$REQ_REL/matrix_stdout.txt"
echo "MATRIX_DRIVER_DONE rc=${PIPESTATUS[0]}"

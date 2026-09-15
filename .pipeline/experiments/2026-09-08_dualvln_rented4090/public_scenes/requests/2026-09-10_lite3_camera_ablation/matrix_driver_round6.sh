#!/usr/bin/env bash
# Executor-side driver, round 6 (2026-09-11): runs the package's round-6 matrix command
# unattended from the remote experiment root for the pitched fused condition. Conditions
# come from the command line (c9_fused_down9); run_matrix.sh gates on the preflight verdict,
# skips existing run ids, and preserves failures. Output is appended to matrix_stdout.txt
# so all rounds are kept.
set -uo pipefail
ROOT=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
REQ_REL=public_scenes/requests/2026-09-10_lite3_camera_ablation
cd "$ROOT" || exit 1
echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) ROUND6 MATRIX START: $* =="
bash "$REQ_REL/run_matrix.sh" "$@" 2>&1 | tee -a "$REQ_REL/matrix_stdout.txt"
echo "MATRIX_DRIVER_DONE rc=${PIPESTATUS[0]}"

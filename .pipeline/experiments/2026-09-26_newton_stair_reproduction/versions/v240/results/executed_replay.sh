#!/usr/bin/env bash
set -eo pipefail
arm=${1:?baseline or candidate required}
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
contracts=OFF
case "$arm" in
  baseline) ;;
  candidate) source /work/install/setup.bash; contracts=ON ;;
  *) exit 64 ;;
esac
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
source_dir=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-17_v237_terminal_approach
run_id=${REPLAY_RUN_ID:-${arm}03}
[[ "$run_id" =~ ^(baseline|candidate)[a-zA-Z0-9_]*$ ]] || exit 64
test ! -e "/work/$run_id/frames.csv"
cmake -S "$source_dir" -B "/work/probe_$run_id" -DV238_CONTRACTS="$contracts" -DV240_CONTRACTS="${V240_CONTRACTS:-OFF}" -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions -DCMAKE_BUILD_TYPE=Release > "/work/configure_$run_id.log" 2>&1
cmake --build "/work/probe_$run_id" -j2 > "/work/build_$run_id.log" 2>&1
export REPLAY_INPUT=${REPLAY_INPUT:-/work/input02} REPLAY_OUTPUT="/work/$run_id" REPLAY_OPTIMIZE=1
"/work/probe_$run_id/replay_probe" --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level "${REPLAY_LOG_LEVEL:-error}" > "/work/$run_id.log" 2>&1

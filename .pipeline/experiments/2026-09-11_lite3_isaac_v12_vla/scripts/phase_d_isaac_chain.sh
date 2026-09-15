#!/usr/bin/env bash
# Phase D.0c: the remaining Isaac scripted tests, one after another, stopping at the first abnormal run.
# Runs 3-6 of the six Dr Sun authorised on 2026-09-14 ("Build relay + scripted GPU tests"): the G1b control on the
# lidar.reset() server, the head-on and corner-graze monitor tests, and the stale-cloud stop.
#
#   nohup setsid bash scripts/phase_d_isaac_chain.sh > driver_logs/phase_d_isaac_chain.log 2>&1 < /dev/null &
set -uo pipefail
ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
cd "$ROOT"
GREEN_TICKS=$ROOT/runs/phase_c_green_box_v1/client/ticks.jsonl

run() {  # RUN_ID DROP_S DRIVER_ARGS...
  local id=$1 drop=$2; shift 2
  echo "== $(date -u +%FT%TZ) start $id"
  VLA_DROP_CLOUD_AFTER_S=$drop bash scripts/phase_d_run_monitor_test.sh "$id" "$@" > "driver_logs/$id.log" 2>&1
  local rc=$?
  cp "driver_logs/$id.log" "runs/$id/driver.log" 2>/dev/null || true
  local done_line
  done_line=$(grep PHASE_D_TEST_DONE "driver_logs/$id.log" || true)
  echo "== $(date -u +%FT%TZ) end $id driver_rc=$rc"
  echo "$done_line"
  if [[ $rc -ne 0 || $done_line != *"rc=0,0,0"* || $done_line != *"leftover=False"* ]]; then
    echo "CHAIN_STOPPED at $id"
    exit 1
  fi
}

run phase_d_isaac_passthrough_green_replay_v2 "" isaac passthrough c_green_box_right_v1.json replay --ticks "$GREEN_TICKS"
run phase_d_isaac_monitor_headon_line0_v1 "" isaac monitor c_red_box_ahead_v1.json line --y-line 0.0 --v 0.3 --seconds 18
run phase_d_isaac_monitor_corner_line045_v1 "" isaac monitor c_red_box_ahead_v1.json line --y-line 0.45 --v 0.3 --seconds 22
run phase_d_isaac_monitor_stale_line0_v1 5.0 isaac monitor c_red_box_ahead_v1.json line --y-line 0.0 --v 0.3 --seconds 12
echo "CHAIN_DONE"

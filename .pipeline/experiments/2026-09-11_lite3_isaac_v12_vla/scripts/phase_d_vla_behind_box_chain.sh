#!/usr/bin/env bash
# Phase D.0e: episodes 2 and 3 of the goal-behind-a-box layout (d_green_behind_grey_box_v1), one after another,
# stopping at the first abnormal run. Episode 1 ran on its own first to check the layout (target visible in decision 1).
# Authorised by Dr Sun 2026-09-14 ("run VLA episodes with a goal behind a box").
#
#   nohup setsid bash scripts/phase_d_vla_behind_box_chain.sh > driver_logs/phase_d_vla_behind_box_chain.log 2>&1 < /dev/null &
set -uo pipefail
ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
cd "$ROOT"

run() {  # RUN_ID EPISODE_FILE
  local id=$1 episode=$2
  echo "== $(date -u +%FT%TZ) start $id"
  bash scripts/phase_d_run_vla_episode.sh "$id" "$episode" > "driver_logs/$id.log" 2>&1
  local rc=$?
  cp "driver_logs/$id.log" "runs/$id/driver.log" 2>/dev/null || true
  local done_line
  done_line=$(grep PHASE_D_VLA_DONE "driver_logs/$id.log" || true)
  echo "== $(date -u +%FT%TZ) end $id driver_rc=$rc"
  echo "$done_line"
  if [[ $rc -ne 0 || $done_line != *"isaac_rc=0 relay_rc=0 client_rc=0"* || $done_line != *"leftover=False"* ]]; then
    echo "CHAIN_STOPPED at $id"
    exit 1
  fi
}

run phase_d_vla_monitor_green_behind_box_v2 d_green_behind_grey_box_v1.json
run phase_d_vla_monitor_green_behind_box_v3 d_green_behind_grey_box_v1.json
echo "CHAIN_DONE"

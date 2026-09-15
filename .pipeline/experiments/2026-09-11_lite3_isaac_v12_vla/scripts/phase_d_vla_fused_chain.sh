#!/usr/bin/env bash
# Phase D.0f: InternVLA-N1 episodes with the two-mount fused camera (VLA_FUSION=c8), one after another, stopping at the
# first abnormal run. Runs only after the scripted preflight phase_d_fused_scripted_preflight_v3 passed its gate and its
# images were checked (v1 and v2 refused on the camera-pose readback and the wrong built-in camera pose). Authorised by Dr Sun 2026-09-14 ("Proceed with Option 1: Run the real camera fusion in Isaac").
#
#   nohup setsid bash scripts/phase_d_vla_fused_chain.sh > driver_logs/phase_d_vla_fused_chain.log 2>&1 < /dev/null &
set -uo pipefail
ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
cd "$ROOT"

# The preflight must have passed its gate on this host (the same standard-library summary that runs locally).
python3 scripts/phase_d0f_fusion_summary.py runs/phase_d_fused_scripted_preflight_v3 \
  --out driver_logs/phase_d_fused_scripted_preflight_v3_gate.json | tee driver_logs/phase_d_fused_scripted_preflight_v3_gate.txt
grep -q "PREFLIGHT_GATE PASSED" driver_logs/phase_d_fused_scripted_preflight_v3_gate.txt || { echo "CHAIN_REFUSED preflight gate"; exit 1; }

run() {  # RUN_ID EPISODE_FILE
  local id=$1 episode=$2
  echo "== $(date -u +%FT%TZ) start $id"
  VLA_FUSION=c8 bash scripts/phase_d_run_vla_episode.sh "$id" "$episode" > "driver_logs/$id.log" 2>&1
  local rc=$?
  cp "driver_logs/$id.log" "runs/$id/driver.log" 2>/dev/null || true
  local done_line
  done_line=$(grep PHASE_D_VLA_DONE "driver_logs/$id.log" || true)
  echo "== $(date -u +%FT%TZ) end $id driver_rc=$rc"
  echo "$done_line"
  # Also stop if any image the model received fell outside the c8 bounds, or the recompute check failed.
  if [[ $rc -ne 0 || $done_line != *"fusion=c8 isaac_rc=0 relay_rc=0 client_rc=0 recompute_rc=0 "* \
        || $done_line != *"fusion_decision_frames_outside_c8=0 "* || $done_line != *"leftover=False"* ]]; then
    echo "CHAIN_STOPPED at $id"
    exit 1
  fi
}

run phase_d_vla_fused_green_box_v1 c_green_box_right_v1.json
run phase_d_vla_fused_red_box_v1 c_red_box_ahead_v1.json
run phase_d_vla_fused_blue_box_v1 c_blue_box_left_v1.json
# Not in this chain: the preflight used starts 1-3 of the 6 authorised (v1 and v2 refused), so the goal-behind-box
# episode phase_d_vla_fused_green_behind_box_v1 needs Dr Sun's approval of a 7th start.
echo "CHAIN_DONE"

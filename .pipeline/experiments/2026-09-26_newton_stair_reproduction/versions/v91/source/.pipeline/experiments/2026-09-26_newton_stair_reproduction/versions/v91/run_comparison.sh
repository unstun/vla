#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/full_workspace/install/setup.bash
set -u
export V91_INPUT=/task/prepared_inputs
for arm in fifo window5 window20 fault20; do
  export V91_MODE=window V91_UPDATE_HZ=20 V91_STALL_MS=0
  case "$arm" in
    fifo) export V91_MODE=fifo V91_UPDATE_HZ=5 ;;
    window5) export V91_UPDATE_HZ=5 ;;
    fault20) export V91_STALL_MS=650 ;;
  esac
  export V91_OUTPUT="/task/mapping01/$arm"
  test ! -e "$V91_OUTPUT"
  mkdir -p /task/mapping01
  /task/mapping-probe-build/mapping_probe --ros-args --params-file \
    /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v81/sync_planner.yaml \
    >"/task/mapping01/$arm.log" 2>&1
done

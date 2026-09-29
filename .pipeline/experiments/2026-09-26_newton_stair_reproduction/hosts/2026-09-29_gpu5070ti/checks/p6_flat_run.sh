#!/bin/bash
# P6 on gpu5070ti: one bounded empty-floor run of v33 through the real launcher (scripts/run_bounded.py around
# scripts/run_local_episode.py), with the v33 trial's flags except the scene, the planner configuration and the goal
# wall budget (PORT.md). The docker shim is first on PATH. Usage: p6_flat_run.sh <attempt>; the run ID is
# port5070_v33_flatNN, never reused. Refuses to reuse a run ID or to start on a busy host.
set -euo pipefail
export PATH=$HOME/vla_exec/bin:$PATH
E=$HOME/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction
PY=$HOME/vla_exec/envs/newton_worker/bin/python
RUN=port5070_v33_flat$(printf %02d "$1")
test ! -e "$E/runs/$RUN"
test -e /proc/sys/fs/binfmt_misc/qemu-aarch64
test -z "$(docker ps --format '{{.Names}}')"
cd "$E"
"$PY" scripts/run_bounded.py --run-id "$RUN" --deadline 900 -- "$PY" "$E/scripts/run_local_episode.py" \
  --backend-executor single --applied-transport zmq --native-build "$E/runtime/scan64_input_refresh_v31" \
  --geometry-obstacles --scene flat_empty_long --goal-wall-budget 600 --startup-mode factory_pd --stance-hold \
  --planner-config "$E/versions/v33/flat_planner.yaml" --integration-version v33

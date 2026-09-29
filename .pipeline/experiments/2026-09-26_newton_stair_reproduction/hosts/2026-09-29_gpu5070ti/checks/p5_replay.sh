#!/bin/bash
# P4 and P5 on gpu5070ti: versions/v32/gc_schedule_check/bench_gc.py (mode none) on v31_historical_full01's commands,
# with the environment run_gc_check.py gives it (plus PYTHONDONTWRITEBYTECODE), the docker shim first on PATH for the
# factory controller's container, and its output in the port directory. Usage: p5_replay.sh <attempt>; each attempt
# writes its own directory and log. Refuses to overwrite or to run on a busy host.
set -euo pipefail
export PATH=$HOME/vla_exec/bin:$PATH
E=$HOME/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction
H=$E/hosts/2026-09-29_gpu5070ti
ATTEMPT=$(printf %02d "$1")
OUT=$H/p5_replay_none_attempt$ATTEMPT
LOG=$H/p5_replay_none_attempt${ATTEMPT}_stdout.log
test ! -e "$OUT"
test ! -e "$LOG"
test -e /proc/sys/fs/binfmt_misc/qemu-aarch64
test -z "$(docker ps --format '{{.Names}}')"
mkdir -p "$H"
BENCH_GC_MODE=none BENCH_OUT=$OUT BENCH_TRIAL=$E/runs/v31_historical_full01 \
  WARP_CACHE_PATH=$E/runtime/warp-cache NEWTON_CACHE_PATH=$E/runtime/assets XDG_CACHE_HOME=$E/runtime/cache \
  PYTHONDONTWRITEBYTECODE=1 \
  "$HOME/vla_exec/envs/newton_worker/bin/python" "$E/versions/v32/gc_schedule_check/bench_gc.py" > "$LOG" 2>&1

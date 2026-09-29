#!/bin/bash
# Round-3 dry tests of the trial runner on gpu5070ti (normal, abort via the runner, abort via the episode group, lock).
D=$HOME/vla_exec/port/runner_dry3
R=$HOME/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/hosts/2026-09-29_gpu5070ti/checks/runner_dry3.sh
runner_pid() { sed -n 's/^runner pid //p' "$D/$1_runner.log" 2>/dev/null; }
echo "=== 1 normal"; DRY_SLEEP=3 bash "$R" runner_dry04; echo "exit=$?"
echo "=== 2 abort via SIGTERM to the runner"
(DRY_SLEEP=60 setsid bash "$R" runner_dry05 > /dev/null 2>&1 &); sleep 8
kill -TERM "$(runner_pid runner_dry05)"; for i in $(seq 30); do grep -q "manifest" "$D/runner_dry05_manifest.log" 2>/dev/null && break; sleep 1; done
echo "=== 3 abort via SIGTERM to the episode's process group"
(DRY_SLEEP=60 setsid bash "$R" runner_dry06 > /dev/null 2>&1 &); sleep 8
standin=$(pgrep -P "$(runner_pid runner_dry06)" -f standin_run_bounded); episode=$(pgrep -P "$standin")
kill -TERM -- "-$episode"; for i in $(seq 30); do grep -q "manifest" "$D/runner_dry06_manifest.log" 2>/dev/null && break; sleep 1; done
echo "=== 4 lock"
(DRY_SLEEP=12 setsid bash "$R" runner_dry07 > /dev/null 2>&1 &); sleep 2
bash "$R" runner_dry08 2>/dev/null; echo "second runner exit=$?"
for i in $(seq 30); do grep -q "manifest" "$D/runner_dry07_manifest.log" 2>/dev/null && break; sleep 1; done
echo "=== results"
for id in runner_dry04 runner_dry05 runner_dry06 runner_dry07; do echo "--- $id"; grep -v "^runner started" "$D/${id}_runner.log"; cat "$D/${id}_manifest.log"; cat "$D/runs/$id/process.json" 2>/dev/null; echo; done
echo "--- refusals"; cat "$D/v33_trial_refusals.txt"
echo "--- leftover sleep episodes:"; pgrep -a -x sleep | grep -E " (3|12|60)$" || echo none

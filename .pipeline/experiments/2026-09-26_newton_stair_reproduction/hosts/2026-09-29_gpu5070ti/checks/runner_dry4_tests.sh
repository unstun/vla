#!/bin/bash
# Round-4 dry tests of the trial runner on gpu5070ti (port review round 4, N27-N29), with checks/runner_dry4.sh and
# checks/runner_dry4_oldlog.sh (both from checks/make_runner_dry4.py) and checks/standin_run_bounded2.py. No physics.
#  1 normal: the stand-in's printed record lands between "launcher started" and "launcher returned"
#  2 abort through the runner's pid: both abort lines survive the stand-in's record (N27)
#  3 abort 0.5 s after the launch, while the stand-in delays its episode by 3 s: the runner still finds it (N28 b)
#  4 abort of an episode that ignores SIGTERM, with a stand-in that then hangs: SIGKILL to the episode's group after
#    GRACE (5 s here), then to the stand-in after GRACE more (N28 d)
#  5 lock: a second runner is refused while one runs; the lock's holders are listed meanwhile (N29)
#  6 control for N27: test 2 with the runner log opened without append mode, as before round 4
# Then: the descriptors each podman process inherited (N29; with a positive control), and leftover processes.
set -u
C=$HOME/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/hosts/2026-09-29_gpu5070ti/checks
D=$HOME/vla_exec/port/runner_dry4
[ ! -e "$D" ] || { echo "$D exists; move it aside first"; exit 1; }
mkdir -p "$D/bin"
install -m 755 "$C/fd_recording_podman.sh" "$D/bin/podman"
runner_pid() { sed -n 's/^runner pid //p' "$D/$1_runner.log" 2>/dev/null; }
wait_line() {
  local i; for i in $(seq 300); do grep -q "$2" "$D/$1_runner.log" 2>/dev/null && return 0; sleep 0.1; done
  echo "$1: no '$2' after 30 s"
}
wait_manifest() {
  local i; for i in $(seq 90); do grep -q "^manifest" "$D/$1_manifest.log" 2>/dev/null && return 0; sleep 1; done
  echo "$1: no manifest after 90 s"
}
start() { local id=$1; shift; (env "$@" setsid bash "$C/runner_dry4.sh" "$id" > /dev/null 2>&1 &); }

echo "=== positive control for the descriptor record: a podman call made while holding descriptor 9"
bash -c 'exec 9>> "$1/control.lock"; "$1/bin/podman" --version > /dev/null' _ "$D"

echo "=== 1 normal"; DRY_SLEEP=3 bash "$C/runner_dry4.sh" runner_dry01; echo "exit=$?"

echo "=== 2 abort through the runner's pid"
start runner_dry02 DRY_SLEEP=60
wait_line runner_dry02 "^launcher started"; sleep 3
kill -TERM "$(runner_pid runner_dry02)"; wait_manifest runner_dry02

echo "=== 3 abort 0.5 s after the launch, before the episode starts"
start runner_dry03 DRY_SLEEP=60 DRY_SPAWN_DELAY=3
wait_line runner_dry03 "^launcher started"; sleep 0.5
kill -TERM "$(runner_pid runner_dry03)"; wait_manifest runner_dry03

echo "=== 4 abort of an episode that ignores SIGTERM, then a hanging stand-in"
start runner_dry04 DRY_SLEEP=120 DRY_IGNORE_TERM=1 DRY_HANG=1
wait_line runner_dry04 "^launcher started"; sleep 3
kill -TERM "$(runner_pid runner_dry04)"; wait_manifest runner_dry04

echo "=== 5 lock"
start runner_dry05 DRY_SLEEP=12
wait_line runner_dry05 "^launcher started"; sleep 1
echo "processes holding the lock file on descriptor 9 (name, script):"
for p in /proc/[0-9]*; do
  [ "$(readlink "$p/fd/9" 2>/dev/null)" = "$D/v33_trial.lock" ] || continue
  echo "  $(cat "$p/comm") $(tr '\0' '\n' < "$p/cmdline" | sed -n 2p | xargs -r basename)"
done
bash "$C/runner_dry4.sh" runner_dry06 2>/dev/null; echo "second runner exit=$?"
wait_manifest runner_dry05

echo "=== 6 control for N27: abort as in test 2, runner log opened without append mode"
(env DRY_SLEEP=60 setsid bash "$C/runner_dry4_oldlog.sh" runner_dry07 > /dev/null 2>&1 &)
wait_line runner_dry07 "^launcher started"; sleep 3
kill -TERM "$(runner_pid runner_dry07)"; wait_manifest runner_dry07

echo "=== results (the stand-in's 2,000-character padding is shown as <2000 x>, only when intact)"
for id in runner_dry01 runner_dry02 runner_dry03 runner_dry04 runner_dry05 runner_dry07; do
  echo "--- $id runner log"
  sed -E 's/"x{2000}"/"<2000 x>"/' "$D/${id}_runner.log"
  echo "--- $id: 'SIGTERM received' lines $(grep -c '^SIGTERM received at' "$D/${id}_runner.log")," \
       "'forwarding SIGTERM' lines $(grep -c '^forwarding SIGTERM' "$D/${id}_runner.log")," \
       "intact records $(grep -cE '"padding": "x{2000}"' "$D/${id}_runner.log")"
  cat "$D/${id}_manifest.log"
  echo "process.json exit_code: $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["exit_code"])' \
       "$D/runs/$id/process.json" 2>/dev/null || echo none)"
done
echo "--- refusals"; cat "$D/v33_trial_refusals.txt"
echo "--- podman calls recorded: $(wc -l < "$D/podman_fds.txt"); with descriptor 9:"
awk -F' :: ' '{ n = split($1, f, " "); for (i = 1; i <= n; i++) if (f[i] == "9") print "  " $0 }' "$D/podman_fds.txt"
echo "--- leftover processes (stand-ins, episodes, containers):"
pgrep -af standin_run_bounded2 || echo "  no stand-in"
pgrep -a -x sleep | grep -E " (3|12|60|120|3600)$" || echo "  no episode sleep"
echo "  containers: [$(podman ps -a --format '{{.Names}}')]"

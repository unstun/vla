#!/bin/bash
# v35's single trial on gpu5070ti (versions/v35/HOST_NOTE_gpu5070ti.md): versions/v35/PHYSICAL_RUN_PLAN.md's run with
# its flags unchanged, on the execution copy, with the docker shim first on PATH and the Linux host sampler. Revised
# after the port's review rounds 1 (B3, N6, N11), 2 (B5, B6, N14-N16), 3 (B7, N21-N24) and 4 (N27-N29).
#
# Start it detached, and only after Dr Sun's go-ahead, so that no ssh or agent session can end it:
#   setsid nohup bash /home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/hosts/2026-09-29_gpu5070ti/v35_trial_run.sh v35_historical_full01 > /dev/null 2>&1 < /dev/null &
# The run ID is v35_historical_full01. Under Dr Sun's rule for infrastructure failures before physics, a retry takes
# the next of v35_historical_full02 to 09. Everything goes to versions/v35/host/<run ID>_*:
#   _runner.log     this runner's own output, complete before the manifest is computed
#   _prerun.txt     the host snapshot; command lines are redacted, and other users' processes show only their name
#   _host.jsonl     the host sampler
#   _docker_calls.txt  the shim's translations
#   _postrun.txt    containers after the launcher returns, and any recovery
#   _SHA256SUMS.txt every run and host file except itself, _manifest.log and the refusals file
#   _manifest.log   the manifest step's own output, including its self-check
# Refusals go to versions/v35/host/v35_trial_refusals.txt and consume nothing. A lock (versions/v35/host/
# v35_trial.lock) stops a second runner from starting while one runs.
# To abort the trial, send SIGTERM to this runner's pid, the first line of the runner log (kill -TERM <pid>), and not
# to its process group: the runner, the sampler and run_bounded share that group, and a group signal would also stop
# run_bounded. The runner forwards SIGTERM to the episode's process group, as run_bounded's own deadline does, and
# waits for run_bounded to record the exit. After 60 s it sends SIGKILL to that group, and after 60 s more to
# run_bounded itself. It then finishes as usual. Only SIGTERM reaches the runner: started with nohup in the
# background, it ignores SIGHUP, SIGINT and SIGQUIT. Do not stop run_bounded.py alone: it has no signal handler and
# would leave the episode running.
set -uo pipefail
SELF=$(readlink -f "$0")
export PATH=$HOME/vla_exec/bin:$PATH
E=$HOME/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction
PY=$HOME/vla_exec/envs/newton_worker/bin/python
SAMPLER_PY=$E/hosts/2026-09-29_gpu5070ti/host_sampler_linux.py
V=$E/versions/v35/host
mkdir -p "$V"
RUN=${1:-}
refuse() { echo "$(date -u +%FT%T.%NZ) ${RUN:-?} refusing: $*" | tee -a "$V/v35_trial_refusals.txt" >&2; exit 1; }
case "$RUN" in
  v35_historical_full0[1-9]) ;;
  *) refuse "the run ID must be v35_historical_full01 to v35_historical_full09" ;;
esac
exec 9>> "$V/v35_trial.lock"
flock -n 9 || refuse "another runner holds $V/v35_trial.lock"
# The runner's own podman calls do not inherit the lock's descriptor, so no podman process they leave behind, such as
# a recreated rootless pause process, can keep the lock (round 4, N29).
podman() { command podman "$@" 9>&-; }
GRACE=60   # seconds an abort waits for run_bounded after each signal
P=$V/$RUN
CONTAINER=vla-newton-${RUN//_/-}
for f in "$E/runs/$RUN" "${P}_runner.log" "${P}_prerun.txt" "${P}_host.jsonl" "${P}_docker_calls.txt" \
         "${P}_postrun.txt" "${P}_SHA256SUMS.txt" "${P}_manifest.log"; do
  [ ! -e "$f" ] || refuse "$f exists"
done

# Quiet host: podman's own failure is not an empty list; qemu-aarch64 must be enabled; the 1-minute load must be at
# most 1.0 (the idle host reads about 0.1-0.4); no GPU compute process, no container and no listener on the run's
# ports 46200-46203.
containers=$(podman ps --format '{{.Names}}') || refuse "podman ps failed"
[ -z "$containers" ] || refuse "running containers: $containers"
[ "$(head -1 /proc/sys/fs/binfmt_misc/qemu-aarch64 2>/dev/null)" = enabled ] || refuse "qemu-aarch64 is not enabled"
load1=$(cut -d' ' -f1 /proc/loadavg)
awk -v l="$load1" 'BEGIN { exit !(l <= 1.0) }' || refuse "1-minute load $load1 is above 1.0"
gpu=$(nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader) || refuse "nvidia-smi failed"
[ -z "$gpu" ] || refuse "GPU compute processes: $gpu"
ports=$(ss -ltnH '( sport >= :46200 and sport <= :46203 )') || refuse "ss failed"
[ -z "$ports" ] || refuse "ports 46200-46203 in use"

# Append mode: run_bounded and the sampler inherit this descriptor, and abort and finish reopen the log, so every
# copy must write at the end of the file (round 4, N27). The log cannot exist yet.
exec >> "${P}_runner.log" 2>&1
echo "runner pid $$"
echo "runner started $(date -u +%FT%T.%NZ) for $RUN, $(sha256sum "$SELF"), 1-minute load $load1"
SAMPLER=
LAUNCHER=
LAUNCHER_STATUS=

record_containers() {
  echo "== podman ps -a at $(date -u +%FT%T.%NZ)"; podman ps -a
}

finish() {
  trap '' TERM
  exec >> "${P}_runner.log" 2>&1
  local how=$1
  echo "finishing ($how) at $(date -u +%FT%T.%NZ)"
  if [ -n "$SAMPLER" ] && kill -0 "$SAMPLER" 2>/dev/null; then
    echo "host sampler alive at the end"; kill -TERM "$SAMPLER"; wait "$SAMPLER"
  else
    echo "host sampler not running at the end"
  fi
  # The launcher has returned (after an abort too, since abort waits for it), or it never started. If a deadline or an
  # abort ended the episode, its own cleanup did not run: recover the container's tmpfs state if the container still
  # exists, then remove it, recording each step.
  {
    record_containers
    if podman container exists "$CONTAINER"; then
      echo "== $CONTAINER still exists: recovering its tmpfs state"
      podman exec "$CONTAINER" tar -C "$E/runs/$RUN/artifacts/external_episode" -cf - . \
        > "$E/runs/$RUN/recovered_external_episode.tar"; echo "tar exit $?"
      podman stop --time 5 "$CONTAINER"; echo "stop exit $?"
      podman rm -f "$CONTAINER"; echo "rm exit $?"
    fi
    for name in $(podman ps -a --format '{{.Names}}' | grep '^vla-factory-algorithm-' || true); do
      echo "== leftover factory container $name"; podman rm -f "$name"; echo "rm exit $?"
    done
  } > "${P}_postrun.txt" 2>&1
  echo "runner finished $(date -u +%FT%T.%NZ) ($how), launcher status ${LAUNCHER_STATUS:-none}"
  exec > "${P}_manifest.log" 2>&1
  find "$E/runs/$RUN" "$V" -type f \( -path "$E/runs/$RUN/*" -o -name "${RUN}_*" \) \
       ! -name "${RUN}_SHA256SUMS.txt" ! -name "${RUN}_manifest.log" -print0 | sort -zu \
    | xargs -0 sha256sum | sed "s#$E/##" > "${P}_SHA256SUMS.txt"
  echo "manifest: $(wc -l < "${P}_SHA256SUMS.txt") files"
  (cd "$E" && sha256sum --quiet -c "${P}_SHA256SUMS.txt") && echo "manifest self-check passed"
  exit "${LAUNCHER_STATUS:-1}"
}

# Waits up to $1 seconds for run_bounded to return. Bash reaps it as soon as it exits, and kill -0 then fails.
launcher_returns_within() {
  local i
  for i in $(seq "$1"); do kill -0 "$LAUNCHER" 2>/dev/null || return 0; sleep 1; done
  ! kill -0 "$LAUNCHER" 2>/dev/null
}

abort() {
  trap '' TERM
  exec >> "${P}_runner.log" 2>&1
  echo "SIGTERM received at $(date -u +%FT%T.%NZ): aborting the trial"
  if [ -n "$LAUNCHER" ] && kill -0 "$LAUNCHER" 2>/dev/null; then
    # run_bounded's only child is the episode, which leads its own session and process group. Just after the launch
    # it may not exist yet, so look for it for up to 10 s while run_bounded runs (round 4, N28).
    local episode= i
    for i in $(seq 20); do
      episode=$(pgrep -P "$LAUNCHER" | head -1)
      if [ -n "$episode" ] || ! kill -0 "$LAUNCHER" 2>/dev/null; then break; fi
      sleep 0.5
    done
    if [ -n "$episode" ]; then
      echo "forwarding SIGTERM to the episode's process group $episode, as run_bounded's own deadline does"
      kill -TERM -- "-$episode"
      if ! launcher_returns_within "$GRACE"; then
        echo "run_bounded still running $GRACE s later: SIGKILL to the process group $episode"
        kill -KILL -- "-$episode"
        if ! launcher_returns_within "$GRACE"; then
          echo "run_bounded still running $GRACE s after that SIGKILL: SIGKILL to run_bounded $LAUNCHER"
          kill -KILL "$LAUNCHER"
        fi
      fi
    else
      echo "no episode process found under run_bounded: waiting for it to return"
    fi
    wait "$LAUNCHER"
    LAUNCHER_STATUS=$?
    echo "launcher returned $LAUNCHER_STATUS after the abort at $(date -u +%FT%T.%NZ)"
  elif [ -n "$LAUNCHER" ]; then
    # The launcher returned just before the signal, before its status was stored; bash remembers it (round 4, N28).
    wait "$LAUNCHER"
    LAUNCHER_STATUS=$?
    echo "the launcher had already returned, status $LAUNCHER_STATUS"
  else
    echo "no launcher was running"
    LAUNCHER_STATUS=${LAUNCHER_STATUS:-1}
  fi
  finish aborted
}
trap abort TERM

{
  echo "== date"; date -u +%FT%T.%NZ
  echo "== uptime"; uptime
  echo "== who"; who
  echo "== login sessions"; loginctl show-user "$(id -un)" -p Linger -p State -p Sessions; loginctl list-sessions --no-legend
  echo "== processes by CPU over one second (second frame of top; names only)"
  env HOME=/nonexistent XDG_CONFIG_HOME=/nonexistent top -b -d 1 -n 2 -w 200 | awk '/^top -/ { frame++ } frame == 2'
  echo "== all processes (redacted command lines for this user's processes; names only for other users')"
  "$PY" "$SAMPLER_PY" --processes
  echo "== podman ps -a"; podman ps -a
  echo "== podman images --digests"; podman images --digests
  echo "== nvidia-smi"; nvidia-smi
  echo "== disk"; df -h "$E"
  echo "== memory"; free -m
  echo "== pressure"; for r in cpu memory io; do echo "$r:"; cat "/proc/pressure/$r"; done
  echo "== qemu-aarch64"; cat /proc/sys/fs/binfmt_misc/qemu-aarch64
  echo "== docker on PATH"; command -v docker
  echo "== tool hashes"; sha256sum "$(command -v docker)" "$SAMPLER_PY" "$SELF"
} > "${P}_prerun.txt" 2>&1

"$PY" "$SAMPLER_PY" "${P}_host.jsonl" &
SAMPLER=$!
sleep 3
if ! kill -0 "$SAMPLER" 2>/dev/null; then
  echo "the host sampler exited at start; stopping before the launcher (status 1)"
  SAMPLER=; LAUNCHER_STATUS=1; finish normal
fi

cd "$E"
echo "launcher started $(date -u +%FT%T.%NZ)"
VLA_SHIM_LOG="${P}_docker_calls.txt" "$PY" scripts/run_bounded.py --run-id "$RUN" --deadline 1800 -- \
  "$PY" "$E/scripts/run_local_episode.py" \
  --backend-executor single --applied-transport zmq --native-build "$E/runtime/scan66_periodic_replan_v35" \
  --geometry-obstacles --scene building_full --building-route historical_full --goal-wall-budget 1500 \
  --startup-mode factory_pd --stance-hold --planner-config "$E/versions/v35/building_planner.yaml" \
  --integration-version v35 < /dev/null &
LAUNCHER=$!
wait "$LAUNCHER"
LAUNCHER_STATUS=$?
echo "launcher returned $LAUNCHER_STATUS at $(date -u +%FT%T.%NZ)"
finish normal

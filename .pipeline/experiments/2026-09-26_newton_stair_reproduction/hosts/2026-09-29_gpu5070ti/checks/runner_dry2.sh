#!/bin/bash
# DRY TEST COPY (stand-in launcher, scratch outputs) of v33's single trial on gpu5070ti (versions/v33/HOST_NOTE_gpu5070ti.md): versions/v33/PHYSICAL_RUN_PLAN.md's run with
# its flags unchanged, on the execution copy, with the docker shim first on PATH and the Linux host sampler. Revised
# after the port's review rounds 1 (B3, N6, N11) and 2 (B5, B6, N14-N16).
#
# Start it detached, and only after Dr Sun's go-ahead, so that no ssh or agent session can end it:
#   setsid nohup bash /home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/hosts/2026-09-29_gpu5070ti/v33_trial_run.sh v33_historical_full01 > /dev/null 2>&1 < /dev/null &
# The run ID is v33_historical_full01. Under Dr Sun's rule for infrastructure failures before physics, a retry takes
# the next of v33_historical_full02 to 09. Everything goes to versions/v33/host/<run ID>_*:
#   _runner.log     this runner's own output, complete before the manifest is computed
#   _prerun.txt     the host snapshot; command lines are redacted, and other users' processes show only their name
#   _host.jsonl     the host sampler
#   _docker_calls.txt  the shim's translations
#   _postrun.txt    containers after the launcher returns, and any recovery
#   _SHA256SUMS.txt every run and host file except itself, _manifest.log and the refusals file
#   _manifest.log   the manifest step's own output, including its self-check
# Refusals go to versions/v33/host/v33_trial_refusals.txt and consume nothing.
# To abort the trial, stop the launcher (scripts/run_bounded.py); the runner then records the end as usual. Killing
# the runner itself leaves the launcher running: the runner then stops the sampler, records the containers without
# touching them, marks its record as signalled and computes the manifest of what exists.
set -uo pipefail
SELF=$(readlink -f "$0")
export PATH=$HOME/vla_exec/bin:$PATH
E=$HOME/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction
PY=$HOME/vla_exec/envs/newton_worker/bin/python
SAMPLER_PY=$E/hosts/2026-09-29_gpu5070ti/host_sampler_linux.py
V=$HOME/vla_exec/port/runner_dry2
mkdir -p "$V"
RUN=${1:-}
refuse() { echo "$(date -u +%FT%T.%NZ) ${RUN:-?} refusing: $*" | tee -a "$V/v33_trial_refusals.txt" >&2; exit 1; }
case "$RUN" in
  runner_dry0[1-9]) ;;
  *) refuse "the run ID must be v33_historical_full01 to v33_historical_full09" ;;
esac
P=$V/$RUN
CONTAINER=vla-newton-${RUN//_/-}
for f in "$V/runs/$RUN" "${P}_runner.log" "${P}_prerun.txt" "${P}_host.jsonl" "${P}_docker_calls.txt" \
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

exec > "${P}_runner.log" 2>&1
echo "runner started $(date -u +%FT%T.%NZ) for $RUN, $(sha256sum "$SELF"), 1-minute load $load1"
SAMPLER=
LAUNCHER=
LAUNCHER_STATUS=

record_containers() {
  echo "== podman ps -a at $(date -u +%FT%T.%NZ)"; podman ps -a
}

finish() {
  trap - TERM INT HUP
  local how=$1
  echo "finishing ($how) at $(date -u +%FT%T.%NZ)"
  if [ -n "$SAMPLER" ] && kill -0 "$SAMPLER" 2>/dev/null; then
    echo "host sampler alive at the end"; kill -TERM "$SAMPLER"; wait "$SAMPLER"
  else
    echo "host sampler not running at the end"
  fi
  if [ "$how" = normal ]; then
    # The launcher has returned. If the wrapper's deadline killed it, its own cleanup did not run: recover the
    # container's tmpfs state if the container still exists, then remove it, recording each step.
    {
      record_containers
      if podman container exists "$CONTAINER"; then
        echo "== $CONTAINER still exists: recovering its tmpfs state"
        podman exec "$CONTAINER" tar -C "$V/runs/$RUN/artifacts/external_episode" -cf - . \
          > "$V/runs/$RUN/recovered_external_episode.tar"; echo "tar exit $?"
        podman stop --time 5 "$CONTAINER"; echo "stop exit $?"
        podman rm -f "$CONTAINER"; echo "rm exit $?"
      fi
      for name in $(podman ps -a --format '{{.Names}}' | grep '^vla-factory-algorithm-' || true); do
        echo "== leftover factory container $name"; podman rm -f "$name"; echo "rm exit $?"
      done
    } > "${P}_postrun.txt" 2>&1
  else
    { echo "== the runner was signalled; the launcher (pid ${LAUNCHER:-none}) may still be running"
      echo "== containers are recorded, not touched"; record_containers; } > "${P}_postrun.txt" 2>&1
  fi
  echo "runner finished $(date -u +%FT%T.%NZ) ($how), launcher status ${LAUNCHER_STATUS:-none}"
  exec > "${P}_manifest.log" 2>&1
  find "$V/runs/$RUN" "$V" -type f \( -path "$V/runs/$RUN/*" -o -name "${RUN}_*" \) \
       ! -name "${RUN}_SHA256SUMS.txt" ! -name "${RUN}_manifest.log" -print0 | sort -zu \
    | xargs -0 sha256sum | sed "s#$E/##" > "${P}_SHA256SUMS.txt"
  echo "manifest: $(wc -l < "${P}_SHA256SUMS.txt") files"
  (cd "$E" && sha256sum --quiet -c "${P}_SHA256SUMS.txt") && echo "manifest self-check passed"
  if [ "$how" = normal ]; then exit "${LAUNCHER_STATUS:-1}"; else exit 143; fi
}
trap 'finish signalled' TERM INT HUP

{
  echo "== date"; date -u +%FT%T.%NZ
  echo "== uptime"; uptime
  echo "== who"; who
  echo "== login sessions"; loginctl show-user "$(id -un)" -p Linger -p State -p Sessions; loginctl list-sessions --no-legend
  echo "== processes by CPU over one second (second frame of top; names only)"
  top -b -d 1 -n 2 -w 200 | awk '/^top -/ { frame++ } frame == 2'
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
( mkdir -p "$V/runs/$RUN"; echo stand-in > "$V/runs/$RUN/stand_in.txt"; VLA_SHIM_LOG="${P}_docker_calls.txt" docker ps > /dev/null; sleep "${DRY_SLEEP:-3}" ) < /dev/null &
LAUNCHER=$!
wait "$LAUNCHER"
LAUNCHER_STATUS=$?
echo "launcher returned $LAUNCHER_STATUS at $(date -u +%FT%T.%NZ)"
finish normal

#!/bin/bash
# DRY TEST COPY (launcher replaced by a stand-in, outputs in a scratch directory) of v33's single trial on gpu5070ti (versions/v33/HOST_NOTE_gpu5070ti.md): versions/v33/PHYSICAL_RUN_PLAN.md's run with
# its flags unchanged, on the execution copy, with the docker shim first on PATH and the Linux host sampler writing to
# the pre-registered path. Revised after port review round 1 (B3, N6, N11).
#
# Start it detached, and only after Dr Sun's go-ahead, so that no ssh or agent session can end it:
#   setsid nohup bash v33_trial_run.sh > /dev/null 2>&1 < /dev/null &
# It writes everything to versions/v33/host/v33_historical_full01_*:
#   _runner.log (its own output), _prerun.txt (host snapshot), _host.jsonl (sampler), _docker_calls.txt (the shim's
#   translations), _postrun.txt (containers after the launcher returns, and any recovery), _SHA256SUMS.txt (the run
#   directory and these files, before any copy-back).
# It refuses to reuse the run ID or any of these files, and refuses a busy host. A refusal is appended to
# _refusals.txt and consumes nothing, so the runner can be started again once the cause is gone.
set -uo pipefail
SELF=$(readlink -f "$0")
export PATH=$HOME/vla_exec/bin:$PATH
E=$HOME/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction
PY=$HOME/vla_exec/envs/newton_worker/bin/python
RUN=runner_dry01
V=$HOME/vla_exec/port/runner_dry
P=$V/$RUN
CONTAINER=vla-newton-${RUN//_/-}
mkdir -p "$V"
refuse() { echo "$(date -u +%FT%T.%NZ) refusing: $*" | tee -a "${P}_refusals.txt" >&2; exit 1; }
for f in "$V/runs/$RUN" "${P}_runner.log" "${P}_prerun.txt" "${P}_host.jsonl" "${P}_docker_calls.txt" \
         "${P}_postrun.txt" "${P}_SHA256SUMS.txt"; do
  [ ! -e "$f" ] || refuse "$f exists"
done

# Quiet host (B3, N11). podman's own failure is not an empty list; qemu-aarch64 must be enabled; the 1-minute load
# must be at most 1.0 (the idle host reads about 0.1-0.4); no GPU compute process and no container may run.
containers=$(podman ps --format '{{.Names}}') || refuse "podman ps failed"
[ -z "$containers" ] || refuse "running containers: $containers"
[ "$(head -1 /proc/sys/fs/binfmt_misc/qemu-aarch64 2>/dev/null)" = enabled ] || refuse "qemu-aarch64 is not enabled"
load1=$(cut -d' ' -f1 /proc/loadavg)
awk -v l="$load1" 'BEGIN { exit !(l <= 1.0) }' || refuse "1-minute load $load1 is above 1.0"
gpu=$(nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader) || refuse "nvidia-smi failed"
[ -z "$gpu" ] || refuse "GPU compute processes: $gpu"

exec > "${P}_runner.log" 2>&1
echo "runner started $(date -u +%FT%T.%NZ), $(sha256sum "$SELF"), 1-minute load $load1"

{
  echo "== date"; date -u +%FT%T.%NZ
  echo "== uptime"; uptime
  echo "== who"; who
  echo "== processes by CPU over one second (second frame of top)"
  top -b -d 1 -n 2 -w 200 | awk '/^top -/ { frame++ } frame == 2'
  echo "== all processes"; ps -eo pid,user,etime,pcpu,rss,args --sort=-pcpu | cut -c1-220
  echo "== podman ps -a"; podman ps -a
  echo "== podman images --digests"; podman images --digests
  echo "== nvidia-smi"; nvidia-smi
  echo "== disk"; df -h "$E"
  echo "== memory"; free -m
  echo "== pressure"; for r in cpu memory io; do echo "$r:"; cat "/proc/pressure/$r"; done
  echo "== qemu-aarch64"; cat /proc/sys/fs/binfmt_misc/qemu-aarch64
  echo "== docker on PATH"; command -v docker
  echo "== tool hashes"; sha256sum "$(command -v docker)" "$E/hosts/2026-09-29_gpu5070ti/host_sampler_linux.py" "$SELF"
} > "${P}_prerun.txt" 2>&1

"$PY" "$E/hosts/2026-09-29_gpu5070ti/host_sampler_linux.py" "${P}_host.jsonl" &
SAMPLER=$!
sleep 3
if ! kill -0 "$SAMPLER" 2>/dev/null; then echo "the host sampler exited at start; stopping before the launcher"; exit 1; fi

cd "$E"
echo "launcher started $(date -u +%FT%T.%NZ)"
mkdir -p "$V/runs/$RUN"; echo stand-in > "$V/runs/$RUN/stand_in.txt"; VLA_SHIM_LOG="${P}_docker_calls.txt" docker ps > /dev/null; sleep 3
STATUS=$?
echo "launcher returned $STATUS at $(date -u +%FT%T.%NZ)"

if kill -0 "$SAMPLER" 2>/dev/null; then
  echo "host sampler alive at the end"
  kill -TERM "$SAMPLER"; wait "$SAMPLER"
else
  echo "host sampler had exited before the end"
fi

# After the launcher (N6): record containers; if the wrapper's deadline killed the launcher, its finally block did not
# copy back the tmpfs state or remove the container, so do both here and record each step.
{
  echo "== podman ps -a after the launcher"; podman ps -a
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

find "$V/runs/$RUN" "$V" -type f ! -name "${RUN}_SHA256SUMS.txt" ! -name "${RUN}_refusals.txt" -print0 | sort -z \
  | xargs -0 sha256sum | sed "s#$E/##" > "${P}_SHA256SUMS.txt"
echo "runner finished $(date -u +%FT%T.%NZ), launcher status $STATUS"
exit "$STATUS"

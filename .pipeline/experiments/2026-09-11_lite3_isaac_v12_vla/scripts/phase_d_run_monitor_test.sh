#!/usr/bin/env bash
# Phase D.0c on the container host: one scripted collision-monitor test (no VLA model).
#
#   phase_d_run_monitor_test.sh RUN_ID SIM RELAY_MODE EPISODE_FILE CLIENT_MODE [CLIENT_ARGS...]
#     SIM          fake (CPU unicycle, phase_c/fake_lockstep_server.py) | isaac (V12 Lite3, GPU)
#     RELAY_MODE   monitor (Nav2 collision_monitor filters every tick) | passthrough (control: relay forwards unchanged)
#     EPISODE_FILE a file name under $ROOT/phase_c/episodes/
#     CLIENT_MODE  replay | straight | line  (phase_d/scripted_command_client.py), followed by its arguments
#   env: VLA_DROP_CLOUD_AFTER_S  fault injection, stop publishing clouds after this simulated time (monitor mode)
#        VLA_WALL_LIMIT          seconds, default 900
#
# Approved by Dr Sun 2026-09-14 ("Build relay + scripted GPU tests"). Builds, pulls and deletes nothing; never touches
# containers or processes it did not start. ROS 2 runs on domain 87, localhost discovery only.
# Run it non-interactively (plain `bash`, no -i or set -m): cleanup kills by process group, which relies on each
# `setsid ... &` child leading its own group.
set -euo pipefail

[[ $# -ge 5 ]] || { echo "usage: $0 RUN_ID SIM RELAY_MODE EPISODE_FILE CLIENT_MODE [CLIENT_ARGS...]" >&2; exit 64; }
RUN_ID=$1; SIM=$2; RELAY_MODE=$3; EPISODE=$4; shift 4
CLIENT_ARGS=("$@")
[[ $RUN_ID =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { echo "bad run id" >&2; exit 64; }
[[ $EPISODE =~ ^[A-Za-z0-9_.-]+\.json$ ]] || { echo "bad episode file name" >&2; exit 64; }
case $SIM in fake|isaac) ;; *) echo "unknown sim: $SIM" >&2; exit 64 ;; esac
case $RELAY_MODE in monitor|passthrough) ;; *) echo "unknown relay mode: $RELAY_MODE" >&2; exit 64 ;; esac

ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
INPUTS=$ROOT/inputs
OUT=$ROOT/runs/$RUN_ID
ENV=$ROOT/ros2_jazzy
MM=$ROOT/tools/micromamba
IMAGE=${VLA_IMAGE:-e01-walking-isaaclab:20260905}
CONTAINER=vla-phase-d-$RUN_ID
WALL_LIMIT=${VLA_WALL_LIMIT:-900}
LAB=/isaac-sim/kit/python/lib/python3.11/site-packages/isaaclab/source
VIDEO_PY=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/official_r2r/official_env_024/bin/python
export ROS_DOMAIN_ID=87 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST

for required in \
  "$INPUTS/lite3_sim_bridge/lite3_sim_bridge/isaac_adapter_core.py" \
  "$ROOT/phase_c/isaac_lockstep_server.py" "$ROOT/phase_c/fake_lockstep_server.py" \
  "$ROOT/phase_c/lockstep_protocol.py" "$ROOT/phase_c/lockstep_common.py" "$ROOT/phase_c/episodes/$EPISODE" \
  "$ROOT/phase_d/collision_monitor_relay.py" "$ROOT/phase_d/scripted_command_client.py" \
  "$ROOT/phase_d/collision_monitor_lite3.yaml" "$ROOT/scripts/phase_d0_footprint_clearance.py" \
  "$ENV/lib/nav2_collision_monitor/collision_monitor" "$MM"; do
  [[ -e $required ]] || { echo "required input missing: $required" >&2; exit 66; }
done
[[ -e $OUT ]] && { echo "run output already exists; refusing to overwrite evidence: $OUT" >&2; exit 73; }
if pgrep -f "$ENV/lib/nav2_collision_monitor/collision_monitor|phase_d/collision_monitor_relay.py" > /dev/null; then
  echo "a collision_monitor or relay from this task is already running" >&2; exit 75
fi
free_gb() { df -Pk "$ROOT" | awk 'NR==2 {printf "%d", $4 / 1048576}'; }
(( $(free_gb) >= 6 )) || { echo "only $(free_gb) GB free" >&2; exit 75; }
if [[ $SIM == isaac ]]; then
  for required in "$INPUTS/lite3_sim_bridge/lite3_sim_bridge/run_isaac_v12_fallback.py" \
    "$INPUTS/v12_runtime/source/rsl_rl/rsl_rl/env/vec_env.py" "$INPUTS/checkpoint/model_149999.pt" \
    "$ROOT/tools/phase_b_camera_probe.py"; do
    [[ -e $required ]] || { echo "required input missing: $required" >&2; exit 66; }
  done
  CK=$(sha256sum "$INPUTS/checkpoint/model_149999.pt" | awk '{print $1}')
  [[ $CK == a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450 ]] || { echo "checkpoint sha256 mismatch" >&2; exit 65; }
  sudo docker image inspect "$IMAGE" > /dev/null 2>&1 || { echo "image not present: $IMAGE" >&2; exit 66; }
  if sudo docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then echo "container $CONTAINER exists" >&2; exit 73; fi
  if sudo docker ps --format '{{.Names}}' | grep -qE '^vla-phase-[a-d]-'; then echo "another vla-phase container is running" >&2; exit 75; fi
  GPU_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
  (( GPU_USED < 1000 )) || { echo "GPU already has ${GPU_USED} MiB in use by something else" >&2; exit 75; }
fi

mkdir -p "$OUT/sim" "$OUT/relay" "$OUT/client" "$OUT/ros_logs" "$ROOT/home"
export ROS_LOG_DIR=$OUT/ros_logs
sha256sum "$ROOT"/phase_c/{isaac_lockstep_server,fake_lockstep_server,lockstep_protocol,lockstep_common}.py \
  "$ROOT"/phase_d/{collision_monitor_relay.py,scripted_command_client.py,collision_monitor_lite3.yaml} \
  "$ROOT/scripts/phase_d0_footprint_clearance.py" "$ROOT/phase_c/episodes/$EPISODE" "$0" > "$OUT/executed_source_sha256.txt"
printf '%q ' "$0" "$RUN_ID" "$SIM" "$RELAY_MODE" "$EPISODE" "${CLIENT_ARGS[@]}" > "$OUT/command.txt"
echo "VLA_DROP_CLOUD_AFTER_S=${VLA_DROP_CLOUD_AFTER_S:-}" >> "$OUT/command.txt"
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_before.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_before.txt"
sudo chmod -R a+rwX "$OUT" "$ROOT/home"
free_port() { python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'; }
SIM_PORT=$(free_port); RELAY_PORT=$(free_port)

SIM_PID=; NODE_PID=; RELAY_PID=; CLIENT_PID=
cleanup() {
  for pid in $CLIENT_PID $RELAY_PID $NODE_PID; do
    [[ -n $pid ]] && kill -TERM -- "-$pid" 2>/dev/null || true
  done
  if [[ $SIM == isaac ]] && sudo docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    sudo docker kill "$CONTAINER" > /dev/null 2>&1 || true
    echo "container still running at driver exit; killed" > "$OUT/CONTAINER_KILLED_BY_DRIVER"
  fi
  [[ -n $SIM_PID ]] && kill -TERM -- "-$SIM_PID" 2>/dev/null || true
  sleep 1
  for pid in $CLIENT_PID $RELAY_PID $NODE_PID $SIM_PID; do
    [[ -n $pid ]] && kill -KILL -- "-$pid" 2>/dev/null || true
  done
  true
}
trap cleanup EXIT

if [[ $SIM == isaac ]]; then
  PYPATH=/workspace/inputs/lite3_sim_bridge:/workspace/inputs/v12_runtime/source/rsl_rl:/workspace/inputs/v12_runtime/source/robot_lab:$LAB/isaaclab:$LAB/isaaclab_tasks:$LAB/isaaclab_rl:$LAB/isaaclab_assets
  setsid sudo timeout --signal=TERM --kill-after=60 "${WALL_LIMIT}s" \
    docker run --rm --name "$CONTAINER" --gpus all --network host -v "$ROOT:/workspace" \
      -e HOME=/workspace/home -e PYTHONPATH="$PYPATH" \
      -e OMNI_KIT_ACCEPT_EULA=YES -e PRIVACY_CONSENT=N -e KMP_DUPLICATE_LIB_OK=TRUE \
      --entrypoint /isaac-sim/python.sh "$IMAGE" \
      /workspace/phase_c/isaac_lockstep_server.py --lidar-cloud \
        --episode "/workspace/phase_c/episodes/$EPISODE" --output-dir "/workspace/runs/$RUN_ID/sim" \
        --checkpoint /workspace/inputs/checkpoint/model_149999.pt \
        --vendored-rsl-rl /workspace/inputs/v12_runtime/source/rsl_rl --tools-dir /workspace/tools --port "$SIM_PORT" \
    > "$OUT/sim.log" 2>&1 &
else
  setsid timeout --signal=TERM "${WALL_LIMIT}s" "$MM" run -p "$ENV" python "$ROOT/phase_c/fake_lockstep_server.py" \
    --lidar-cloud --footprint-contact --episode "$ROOT/phase_c/episodes/$EPISODE" --output-dir "$OUT/sim" \
    --bridge-source "$INPUTS/lite3_sim_bridge" --port "$SIM_PORT" --client-timeout-s 300 > "$OUT/sim.log" 2>&1 &
fi
SIM_PID=$!

RELAY_ARGS=(--listen-port "$RELAY_PORT" --server-port "$SIM_PORT" --output-dir "$OUT/relay" --mode "$RELAY_MODE" --expect-cloud)
if [[ $RELAY_MODE == monitor ]]; then
  setsid timeout --signal=TERM "${WALL_LIMIT}s" "$MM" run -p "$ENV" bash -c \
    'exec "$CONDA_PREFIX/lib/nav2_collision_monitor/collision_monitor" --ros-args --params-file "$1"' _ \
    "$ROOT/phase_d/collision_monitor_lite3.yaml" > "$OUT/collision_monitor.log" 2>&1 &
  NODE_PID=$!
  [[ -n ${VLA_DROP_CLOUD_AFTER_S:-} ]] && RELAY_ARGS+=(--drop-cloud-after-sim-s "$VLA_DROP_CLOUD_AFTER_S")
fi
setsid timeout --signal=TERM "${WALL_LIMIT}s" "$MM" run -p "$ENV" python "$ROOT/phase_d/collision_monitor_relay.py" \
  "${RELAY_ARGS[@]}" > "$OUT/relay.log" 2>&1 &
RELAY_PID=$!
for _ in $(seq 1 120); do
  [[ -e $OUT/relay/RELAY_LISTENING ]] && break
  kill -0 "$RELAY_PID" 2>/dev/null || break
  sleep 2
done
if [[ ! -e $OUT/relay/RELAY_LISTENING ]]; then
  # Stop here rather than let the simulator hold the GPU until the wall limit; the EXIT trap cleans up.
  echo "relay did not start listening" | tee "$OUT/RELAY_NOT_LISTENING" >&2
  exit 70
fi

setsid timeout --signal=TERM "${WALL_LIMIT}s" python3 "$ROOT/phase_d/scripted_command_client.py" \
  --port "$RELAY_PORT" --output-dir "$OUT/client" "${CLIENT_ARGS[@]}" > "$OUT/client.log" 2>&1 &
CLIENT_PID=$!

set +e
wait "$CLIENT_PID"; CLIENT_RC=$?; CLIENT_PID=
for _ in $(seq 1 30); do kill -0 "$RELAY_PID" 2>/dev/null || break; sleep 1; done
kill -0 "$RELAY_PID" 2>/dev/null && { kill -TERM -- "-$RELAY_PID"; echo "relay killed after client exit" > "$OUT/RELAY_KILLED"; }
wait "$RELAY_PID"; RELAY_RC=$?; RELAY_PID=
for _ in $(seq 1 90); do kill -0 "$SIM_PID" 2>/dev/null || break; sleep 2; done
if kill -0 "$SIM_PID" 2>/dev/null; then
  [[ $SIM == isaac ]] && sudo docker kill "$CONTAINER" > /dev/null 2>&1
  kill -TERM -- "-$SIM_PID" 2>/dev/null
  echo "simulator still running 180 s after the client exited; killed" > "$OUT/SIM_KILLED_AFTER_CLIENT"
fi
wait "$SIM_PID"; SIM_RC=$?; SIM_PID=
if [[ -n $NODE_PID ]]; then kill -TERM -- "-$NODE_PID" 2>/dev/null; wait "$NODE_PID"; NODE_PID=; fi
set -e

sudo chown -R "$(id -u):$(id -g)" "$OUT" 2>/dev/null || true
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_after.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_after.txt"
echo "$SIM_RC $RELAY_RC $CLIENT_RC" > "$OUT/exit_codes"
if [[ $SIM == isaac && -x $VIDEO_PY ]]; then
  "$VIDEO_PY" - "$OUT/sim/frames" <<'EOF' > "$OUT/video.log" 2>&1 || true
import sys, glob, cv2
frames = sys.argv[1]
for name in ('chase', 'head'):
    paths = sorted(glob.glob('{}/{}_*.jpg'.format(frames, name)))
    if not paths:
        continue
    first = cv2.imread(paths[0])
    writer = cv2.VideoWriter('{}/../{}.mp4'.format(frames, name), cv2.VideoWriter_fourcc(*'mp4v'), 10.0,
                             (first.shape[1], first.shape[0]))
    for path in paths:
        writer.write(cv2.imread(path))
    writer.release()
    print(name, len(paths), 'frames')
EOF
fi
LEFT=$(pgrep -fa "$ENV/lib/nav2_collision_monitor/collision_monitor|phase_d/collision_monitor_relay.py|scripted_command_client.py --port $RELAY_PORT" | grep -v pgrep || true)
[[ -n $LEFT ]] && echo "$LEFT" > "$OUT/LEFTOVER_PROCESSES"
echo "== unrelated containers unchanged? =="
diff <(grep -v "^$CONTAINER " "$OUT/containers_before.txt") <(grep -v "^$CONTAINER " "$OUT/containers_after.txt") && echo "  identical"
SUMMARY=$(python3 - "$OUT" <<'EOF'
import json, sys, pathlib
out = pathlib.Path(sys.argv[1])
def load(p):
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}
s = load(out / 'sim' / 'isaac_episode.json') or load(out / 'sim' / 'fake_episode.json')
r, c = load(out / 'relay' / 'relay_episode.json'), load(out / 'client' / 'scripted_episode.json')
print('sim_termination={} sim_s={} client_termination={} relay_changed={} relay_changed_after_tick0={} '
      'first_changed_tick={} relay_no_reply={} clouds={} first_cloud_points={} min_cloud_points={} relay_end={!r} '
      'leftover={}'.format(
    s.get('termination'), None if s.get('sim_seconds') is None else round(s['sim_seconds'], 2), c.get('termination'),
    r.get('commands_changed_by_monitor'), r.get('commands_changed_after_tick0'), r.get('first_changed_tick'),
    r.get('monitor_no_reply_ticks'), r.get('clouds_received'), r.get('first_cloud_points'), r.get('min_cloud_points'),
    r.get('end_reason'), (out / 'LEFTOVER_PROCESSES').exists()))
EOF
)
echo "PHASE_D_TEST_DONE sim=$SIM relay=$RELAY_MODE rc=$(cat "$OUT/exit_codes" | tr ' ' ,) $SUMMARY"

#!/usr/bin/env bash
# Phase D.0d on the container host: one InternVLA-N1 lockstep episode with Nav2 collision_monitor in the command path.
#
#   phase_d_run_vla_episode.sh RUN_ID EPISODE_FILE
#     EPISODE_FILE  a file name under $ROOT/phase_c/episodes/
#   env: VLA_WALL_LIMIT  seconds, default 3600
#        VLA_SIM=fake VLA_AGENT=scripted   CPU rehearsal of this driver: the fake simulator (phase_c/fake_lockstep_server.py)
#                                          and the Phase C client's scripted agent, through the same node and relay
#        VLA_SCRIPT=a,b,...,stop           scripted agent only: the client's --script (entries look_down, straight, left,
#                                          stop; must end with stop). Default: the client's own script
#        VLA_FUSION=c8                     Phase D.0f (Dr Sun 2026-09-14): the server sends the two-mount fused image
#                                          (--fusion-config phase_d/fusion_isaac_c8.json); Isaac only. After the episode
#                                          phase_d/fusion_recompute_check.py runs in the same image (CPU, no network)
#
# Phase C's episode driver (scripts/phase_c_run_episode.sh) with three changes and nothing else:
#   1. the Isaac lockstep server runs with --lidar-cloud (SENSOR_FRAME_V1 every reply, server b976284d);
#   2. the unmodified Nav2 collision_monitor node and phase_d/collision_monitor_relay.py (mode monitor) sit between the
#      VLA client and the server; the client connects to the relay's port;
#   3. run outputs gain relay/, ros_logs/ and the node's log.
# The VLA client, its model, controllers and episode files are Phase C's, unchanged.
# Authorised by Dr Sun 2026-09-14 ("run D.0d with 2-3 VLA episodes"). Builds, pulls and deletes nothing; never touches
# containers or processes it did not start. Run non-interactively (plain `bash`): cleanup kills process groups.
set -euo pipefail

[[ $# -eq 2 ]] || { echo "usage: $0 RUN_ID EPISODE_FILE" >&2; exit 64; }
RUN_ID=$1
EPISODE=$2
[[ $RUN_ID =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { echo "bad run id" >&2; exit 64; }
[[ $EPISODE =~ ^[A-Za-z0-9_.-]+\.json$ ]] || { echo "bad episode file name" >&2; exit 64; }
SIM=${VLA_SIM:-isaac}
AGENT=${VLA_AGENT:-internvla}
case $SIM in isaac|fake) ;; *) echo "unknown sim: $SIM" >&2; exit 64 ;; esac
case $AGENT in internvla|scripted) ;; *) echo "unknown agent: $AGENT" >&2; exit 64 ;; esac
SCRIPT_ARGS=()
if [[ -n ${VLA_SCRIPT:-} ]]; then
  [[ $AGENT == scripted ]] || { echo "VLA_SCRIPT needs the scripted agent" >&2; exit 64; }
  [[ $VLA_SCRIPT =~ ^((look_down|straight|left),)*stop$ ]] || { echo "bad script" >&2; exit 64; }
  SCRIPT_ARGS=(--script "$VLA_SCRIPT")
fi
FUSION=${VLA_FUSION:-}
case $FUSION in '') ;; c8) [[ $SIM == isaac ]] || { echo "fusion needs the Isaac simulator" >&2; exit 64; } ;;
  *) echo "unknown fusion: $FUSION" >&2; exit 64 ;; esac

ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
INPUTS=$ROOT/inputs
OUT=$ROOT/runs/$RUN_ID
IMAGE=${VLA_IMAGE:-e01-walking-isaaclab:20260905}
CONTAINER=vla-phase-d-$RUN_ID
WALL_LIMIT=${VLA_WALL_LIMIT:-3600}
LAB=/isaac-sim/kit/python/lib/python3.11/site-packages/isaaclab/source
DUALVLN=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
PY=$DUALVLN/official_r2r/official_env_024/bin/python
INTERNNAV=$DUALVLN/work/InternNav
CONTROLLERS=$INTERNNAV/scripts/realworld
ENV=$ROOT/ros2_jazzy
MM=$ROOT/tools/micromamba
export ROS_DOMAIN_ID=87 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST

for required in \
  "$INPUTS/lite3_sim_bridge/lite3_sim_bridge/run_isaac_v12_fallback.py" \
  "$INPUTS/v12_runtime/source/rsl_rl/rsl_rl/env/vec_env.py" \
  "$INPUTS/checkpoint/model_149999.pt" \
  "$ROOT/tools/phase_b_camera_probe.py" \
  "$ROOT/phase_c/isaac_lockstep_server.py" "$ROOT/phase_c/vla_lockstep_client.py" \
  "$ROOT/phase_c/lockstep_protocol.py" "$ROOT/phase_c/lockstep_common.py" \
  "$ROOT/phase_c/episodes/$EPISODE" "$ROOT/pydeps/casadi/__init__.py" "$PY" "$CONTROLLERS/controllers.py" \
  "$DUALVLN/models/InternVLA-N1-DualVLN/config.json" "$DUALVLN/models/depth_anything_v2_metric_hypersim_vits.pth" \
  "$ROOT/phase_d/collision_monitor_relay.py" "$ROOT/phase_d/collision_monitor_lite3.yaml" \
  "$ENV/lib/nav2_collision_monitor/collision_monitor" "$MM"; do
  [[ -e $required ]] || { echo "required input missing: $required" >&2; exit 66; }
done
FUSION_FILES=()
ISAAC_FUSION_ARGS=()
if [[ $FUSION == c8 ]]; then
  FUSION_FILES=("$ROOT/tools/fused_camera.py" "$ROOT/phase_d/isaac_fusion.py" "$ROOT/phase_d/fusion_isaac_c8.json"
                "$ROOT/phase_d/fusion_recompute_check.py")
  for required in "${FUSION_FILES[@]}"; do
    [[ -e $required ]] || { echo "required input missing: $required" >&2; exit 66; }
  done
  FC=$(sha256sum "$ROOT/tools/fused_camera.py" | awk '{print $1}')
  [[ $FC == 382eee6dfe7cd6928681f5358f59fd8718c8d7cf339d3d60975f83fd19c92676 ]] || { echo "fused_camera.py is not the pinned file" >&2; exit 65; }
  ISAAC_FUSION_ARGS=(--fusion-config /workspace/phase_d/fusion_isaac_c8.json)
fi
[[ -e $OUT ]] && { echo "run output already exists; refusing to overwrite evidence: $OUT" >&2; exit 73; }

CK=$(sha256sum "$INPUTS/checkpoint/model_149999.pt" | awk '{print $1}')
[[ $CK == a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450 ]] || { echo "checkpoint sha256 mismatch" >&2; exit 65; }
CS=$(sha256sum "$CONTROLLERS/controllers.py" | awk '{print $1}')
[[ $CS == 251522af6da05daee5279e07371b5f9ca319326e7097c0c7e5ae68e76217e408 ]] || { echo "controllers.py is not the pinned file" >&2; exit 65; }

# Guards match the real executables only (anchored on argv[0]), so a shell whose command line merely mentions these
# names (for example the ssh command that launched this script) is not mistaken for a running node or relay.
if pgrep -f "^$ENV/lib/nav2_collision_monitor/collision_monitor( |$)" > /dev/null \
    || pgrep -f "^[^ ]*python[0-9.]* [^ ]*phase_d/collision_monitor_relay\.py( |$)" > /dev/null \
    || pgrep -f "^[^ ]*python[0-9.]* [^ ]*phase_c/vla_lockstep_client\.py( |$)" > /dev/null; then
  echo "a collision_monitor, relay or VLA client from this task is already running" >&2; exit 75
fi
if [[ $SIM == isaac ]]; then
  sudo docker image inspect "$IMAGE" > /dev/null 2>&1 || { echo "image not present: $IMAGE" >&2; exit 66; }
  if sudo docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then echo "container $CONTAINER exists" >&2; exit 73; fi
  if sudo docker ps --format '{{.Names}}' | grep -qE '^vla-phase-[a-d]-'; then echo "another vla-phase container is running" >&2; exit 75; fi
fi
if [[ $SIM == isaac || $AGENT == internvla ]]; then
  GPU_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
  (( GPU_USED < 1000 )) || { echo "GPU already has ${GPU_USED} MiB in use by something else" >&2; exit 75; }
fi
free_gb() { df -Pk "$ROOT" | awk 'NR==2 {printf "%d", $4 / 1048576}'; }
(( $(free_gb) >= 6 )) || { echo "only $(free_gb) GB free" >&2; exit 75; }

SIM_DIR=$OUT/isaac
[[ $SIM == fake ]] && SIM_DIR=$OUT/sim
mkdir -p "$SIM_DIR" "$OUT/client" "$OUT/relay" "$OUT/ros_logs" "$ROOT/home"
export ROS_LOG_DIR=$OUT/ros_logs
sha256sum "$ROOT"/phase_c/{isaac_lockstep_server,fake_lockstep_server,vla_lockstep_client,lockstep_protocol,lockstep_common}.py \
  "$ROOT"/phase_d/{collision_monitor_relay.py,collision_monitor_lite3.yaml} "$ROOT/phase_c/episodes/$EPISODE" \
  "$CONTROLLERS/controllers.py" "$ROOT/tools/phase_b_camera_probe.py" "$0" ${FUSION_FILES[@]+"${FUSION_FILES[@]}"} \
  > "$OUT/executed_source_sha256.txt"
printf '%q ' "$0" "$RUN_ID" "$EPISODE" > "$OUT/command.txt"
echo "VLA_SIM=$SIM VLA_AGENT=$AGENT VLA_FUSION=$FUSION VLA_SCRIPT=${VLA_SCRIPT:-}" >> "$OUT/command.txt"
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_before.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_before.txt"
df -Pk "$ROOT" > "$OUT/disk_before.txt"
sudo chmod -R a+rwX "$OUT" "$ROOT/home"
free_port() { "$PY" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'; }
SIM_PORT=$(free_port); RELAY_PORT=$(free_port)

ISAAC_PID=; CLIENT_PID=; NODE_PID=; RELAY_PID=
(
  echo "unix_s,device_used_mib,util_pct,host_mem_used_mib,host_mem_available_mib,disk_free_gb,apps"
  while sleep 2; do
    dev=$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | head -1 | tr -d ' ')
    apps=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | tr -d ' ' | tr '\n' ';')
    read -r used avail < <(free -m | awk '/^Mem:/ {print $3, $7}')
    disk=$(free_gb)
    echo "$(date +%s),$dev,$used,$avail,$disk,$apps"
    if (( disk < 2 )); then
      echo "disk free ${disk} GB < 2 GB; stopping this run" > "$OUT/DISK_ABORT"
      sudo docker kill "$CONTAINER" > /dev/null 2>&1 || true
      pkill -f "^[^ ]*python[0-9.]* [^ ]*phase_c/vla_lockstep_client\.py --episode $ROOT/phase_c/episodes/$EPISODE --output-dir $OUT/client" || true
    fi
  done
) > "$OUT/samples.csv" 2>/dev/null &
SAMPLER=$!
cleanup() {
  kill "$SAMPLER" 2>/dev/null || true
  for pid in $CLIENT_PID $RELAY_PID $NODE_PID; do
    [[ -n $pid ]] && kill -TERM -- "-$pid" 2>/dev/null || true
  done
  [[ $SIM == fake && -n $ISAAC_PID ]] && kill -TERM -- "-$ISAAC_PID" 2>/dev/null || true
  if sudo docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    sudo docker kill "$CONTAINER" > /dev/null 2>&1 || true
    echo "container still running at driver exit; killed" > "$OUT/CONTAINER_KILLED_BY_DRIVER"
  fi
  if sudo docker ps --format '{{.Names}}' | grep -qx "$CONTAINER-recompute"; then
    sudo docker kill "$CONTAINER-recompute" > /dev/null 2>&1 || true
    echo "recompute container still running at driver exit; killed" > "$OUT/RECOMPUTE_CONTAINER_KILLED_BY_DRIVER"
  fi
  sleep 1
  for pid in $CLIENT_PID $RELAY_PID $NODE_PID; do
    [[ -n $pid ]] && kill -KILL -- "-$pid" 2>/dev/null || true
  done
  true
}
trap cleanup EXIT

# Monitor node and relay first: the relay configures and activates the node, then listens.
setsid timeout --signal=TERM "${WALL_LIMIT}s" "$MM" run -p "$ENV" bash -c \
  'exec "$CONDA_PREFIX/lib/nav2_collision_monitor/collision_monitor" --ros-args --params-file "$1"' _ \
  "$ROOT/phase_d/collision_monitor_lite3.yaml" > "$OUT/collision_monitor.log" 2>&1 &
NODE_PID=$!
setsid timeout --signal=TERM "${WALL_LIMIT}s" "$MM" run -p "$ENV" python "$ROOT/phase_d/collision_monitor_relay.py" \
  --listen-port "$RELAY_PORT" --server-port "$SIM_PORT" --output-dir "$OUT/relay" --mode monitor --expect-cloud \
  > "$OUT/relay.log" 2>&1 &
RELAY_PID=$!
for _ in $(seq 1 120); do
  [[ -e $OUT/relay/RELAY_LISTENING ]] && break
  kill -0 "$RELAY_PID" 2>/dev/null || break
  sleep 2
done
if [[ ! -e $OUT/relay/RELAY_LISTENING ]]; then
  echo "relay did not start listening" | tee "$OUT/RELAY_NOT_LISTENING" >&2
  exit 70
fi

if [[ $SIM == isaac ]]; then
  PYPATH=/workspace/inputs/lite3_sim_bridge:/workspace/inputs/v12_runtime/source/rsl_rl:/workspace/inputs/v12_runtime/source/robot_lab:$LAB/isaaclab:$LAB/isaaclab_tasks:$LAB/isaaclab_rl:$LAB/isaaclab_assets
  setsid sudo timeout --signal=TERM --kill-after=60 "${WALL_LIMIT}s" \
    docker run --rm --name "$CONTAINER" \
      --gpus all --network host \
      -v "$ROOT:/workspace" \
      -e HOME=/workspace/home -e PYTHONPATH="$PYPATH" \
      -e OMNI_KIT_ACCEPT_EULA=YES -e PRIVACY_CONSENT=N -e KMP_DUPLICATE_LIB_OK=TRUE \
      --entrypoint /isaac-sim/python.sh "$IMAGE" \
      /workspace/phase_c/isaac_lockstep_server.py --lidar-cloud ${ISAAC_FUSION_ARGS[@]+"${ISAAC_FUSION_ARGS[@]}"} \
        --episode "/workspace/phase_c/episodes/$EPISODE" \
        --output-dir "/workspace/runs/$RUN_ID/isaac" \
        --checkpoint /workspace/inputs/checkpoint/model_149999.pt \
        --vendored-rsl-rl /workspace/inputs/v12_runtime/source/rsl_rl \
        --tools-dir /workspace/tools \
        --port "$SIM_PORT" \
    > "$OUT/isaac.log" 2>&1 &
else
  setsid timeout --signal=TERM "${WALL_LIMIT}s" "$MM" run -p "$ENV" python "$ROOT/phase_c/fake_lockstep_server.py" \
    --lidar-cloud --footprint-contact --episode "$ROOT/phase_c/episodes/$EPISODE" --output-dir "$SIM_DIR" \
    --bridge-source "$INPUTS/lite3_sim_bridge" --port "$SIM_PORT" --client-timeout-s 600 > "$OUT/sim.log" 2>&1 &
fi
ISAAC_PID=$!

# The client loads the model while Isaac starts; its connection to the relay waits until the relay has the server.
setsid env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PYTHONPATH="$ROOT/pydeps" \
  timeout --signal=TERM --kill-after=30 "${WALL_LIMIT}s" \
  "$PY" "$ROOT/phase_c/vla_lockstep_client.py" \
    --episode "$ROOT/phase_c/episodes/$EPISODE" \
    --output-dir "$OUT/client" \
    --port "$RELAY_PORT" \
    --agent "$AGENT" ${SCRIPT_ARGS[@]+"${SCRIPT_ARGS[@]}"} \
    --internnav-root "$INTERNNAV" \
    --model-path "$DUALVLN/models/InternVLA-N1-DualVLN" \
    --depth-anything "$DUALVLN/models/depth_anything_v2_metric_hypersim_vits.pth" \
    --controllers-dir "$CONTROLLERS" \
  > "$OUT/client.log" 2>&1 &
CLIENT_PID=$!

set +e
# If Isaac or the relay dies first, the client would wait on its socket; stop it 60 s later.
gone_since=
while kill -0 "$CLIENT_PID" 2>/dev/null; do
  if ! kill -0 "$ISAAC_PID" 2>/dev/null || ! kill -0 "$RELAY_PID" 2>/dev/null; then
    gone_since=${gone_since:-$(date +%s)}
    if (( $(date +%s) - gone_since > 60 )); then
      echo "isaac or relay exited first; client stopped 60 s later" > "$OUT/CLIENT_KILLED_PEER_EXITED"
      kill -TERM -- "-$CLIENT_PID" 2>/dev/null
    fi
  fi
  sleep 2
done
wait "$CLIENT_PID"; CLIENT_RC=$?
CLIENT_PID=
for _ in $(seq 1 30); do kill -0 "$RELAY_PID" 2>/dev/null || break; sleep 1; done
kill -0 "$RELAY_PID" 2>/dev/null && { kill -TERM -- "-$RELAY_PID"; echo "relay killed after client exit" > "$OUT/RELAY_KILLED"; }
wait "$RELAY_PID"; RELAY_RC=$?
RELAY_PID=
for _ in $(seq 1 90); do kill -0 "$ISAAC_PID" 2>/dev/null || break; sleep 2; done
if kill -0 "$ISAAC_PID" 2>/dev/null; then
  sudo docker kill "$CONTAINER" > /dev/null 2>&1
  echo "isaac still running 180 s after the client exited; killed" > "$OUT/ISAAC_KILLED_AFTER_CLIENT"
fi
wait "$ISAAC_PID"; ISAAC_RC=$?
kill -TERM -- "-$NODE_PID" 2>/dev/null; wait "$NODE_PID"; NODE_PID=
RECOMPUTE_RC=none
if [[ $FUSION == c8 ]]; then
  # Same image as the server (same numpy and cv2), CPU only, no network: re-fuse the saved inputs bit for bit and check
  # that the client's first decision frame is the fused image.
  sudo timeout --kill-after=30 600 docker run --rm --name "$CONTAINER-recompute" --network none \
    -v "$ROOT:/workspace" --entrypoint /isaac-sim/python.sh "$IMAGE" \
    /workspace/phase_d/fusion_recompute_check.py --run-dir "/workspace/runs/$RUN_ID" --tools-dir /workspace/tools \
    > "$OUT/fusion_recompute_check.log" 2>&1
  RECOMPUTE_RC=$?
fi
set -e
kill "$SAMPLER" 2>/dev/null || true

sudo chown -R "$(id -u):$(id -g)" "$OUT" 2>/dev/null || true
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_after.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_after.txt"
df -Pk "$ROOT" > "$OUT/disk_after.txt"
echo "$ISAAC_RC $RELAY_RC $CLIENT_RC $RECOMPUTE_RC" > "$OUT/exit_codes"

"$PY" - "$OUT/isaac/frames" <<'EOF' > "$OUT/video.log" 2>&1 || true
import sys, glob, cv2
frames = sys.argv[1]
for name in ('chase', 'head', 'fused'):
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

LEFT=$( { pgrep -fa "^$ENV/lib/nav2_collision_monitor/collision_monitor( |$)";
          pgrep -fa "^[^ ]*python[0-9.]* [^ ]*phase_d/collision_monitor_relay\.py --listen-port $RELAY_PORT";
          pgrep -fa "^[^ ]*python[0-9.]* [^ ]*phase_c/vla_lockstep_client\.py --episode $ROOT/phase_c/episodes/$EPISODE --output-dir $OUT/client"; } || true)
[[ -n $LEFT ]] && echo "$LEFT" > "$OUT/LEFTOVER_PROCESSES"
echo "== unrelated containers unchanged? =="
diff <(grep -v "^$CONTAINER " "$OUT/containers_before.txt") <(grep -v "^$CONTAINER " "$OUT/containers_after.txt") && echo "  identical"
SUMMARY=$("$PY" - "$OUT" <<'EOF'
import json, sys, pathlib
out = pathlib.Path(sys.argv[1])
def load(p):
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}
i, c, r = (load(out / 'isaac' / 'isaac_episode.json') or load(out / 'sim' / 'fake_episode.json'),
           load(out / 'client' / 'client_episode.json'), load(out / 'relay' / 'relay_episode.json'))
f = (i.get('fusion') or {}).get('summary') or {}
print('isaac_termination={} client_termination={} success={} stopped={} final_distance_m={} min_distance_m={} sim_s={} '
      'decisions={} relay_changed={} relay_no_reply={} relay_end={!r} fusion_frames={} fusion_decision_frames_outside_c8={} '
      'leftover={}'.format(
    i.get('termination'), c.get('termination'), c.get('success'), c.get('stopped_by_model'),
    None if i.get('final_distance_to_target_m') is None else round(i['final_distance_to_target_m'], 3),
    None if i.get('min_distance_to_target_m') is None else round(i['min_distance_to_target_m'], 3),
    None if i.get('sim_seconds') is None else round(i['sim_seconds'], 2), c.get('decisions'),
    r.get('commands_changed_by_monitor'), r.get('monitor_no_reply_ticks'), r.get('end_reason'),
    f.get('frames'), f.get('decision_frames_outside_c8_bounds'), (out / 'LEFTOVER_PROCESSES').exists()))
EOF
)
echo "PHASE_D_VLA_DONE sim=$SIM agent=$AGENT fusion=${FUSION:-none} isaac_rc=$ISAAC_RC relay_rc=$RELAY_RC client_rc=$CLIENT_RC recompute_rc=$RECOMPUTE_RC $SUMMARY"

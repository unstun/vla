#!/usr/bin/env bash
# Phase C on the container host: one lockstep episode.
#
#   phase_c_run_episode.sh RUN_ID EPISODE_FILE [AGENT]
#     EPISODE_FILE  a file name under $ROOT/phase_c/episodes/
#     AGENT         internvla (default) | scripted (no model; exercises the Isaac side and the controllers)
#
# The Isaac lockstep server runs in the e01-walking-isaaclab image; the VLA client runs in the DualVLN
# official_env_024 interpreter with this task's CasADi (pydeps/). Inference only: builds, pulls and deletes nothing, and
# never touches containers it did not start.
set -euo pipefail

[[ $# -ge 2 && $# -le 3 ]] || { echo "usage: $0 RUN_ID EPISODE_FILE [AGENT]" >&2; exit 64; }
RUN_ID=$1
EPISODE=$2
AGENT=${3:-internvla}
[[ $RUN_ID =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { echo "bad run id" >&2; exit 64; }
[[ $EPISODE =~ ^[A-Za-z0-9_.-]+\.json$ ]] || { echo "bad episode file name" >&2; exit 64; }
case $AGENT in internvla|scripted) ;; *) echo "unknown agent: $AGENT" >&2; exit 64 ;; esac

ROOT=${VLA_RUN_ROOT:-$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla}
INPUTS=$ROOT/inputs
OUT=$ROOT/runs/$RUN_ID
IMAGE=${VLA_IMAGE:-e01-walking-isaaclab:20260905}
CONTAINER=vla-phase-c-$RUN_ID
WALL_LIMIT=${VLA_WALL_LIMIT:-3600}
LAB=/isaac-sim/kit/python/lib/python3.11/site-packages/isaaclab/source
DUALVLN=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
PY=$DUALVLN/official_r2r/official_env_024/bin/python
INTERNNAV=$DUALVLN/work/InternNav
CONTROLLERS=$INTERNNAV/scripts/realworld

for required in \
  "$INPUTS/lite3_sim_bridge/lite3_sim_bridge/run_isaac_v12_fallback.py" \
  "$INPUTS/v12_runtime/source/rsl_rl/rsl_rl/env/vec_env.py" \
  "$INPUTS/checkpoint/model_149999.pt" \
  "$ROOT/tools/phase_b_camera_probe.py" \
  "$ROOT/phase_c/isaac_lockstep_server.py" "$ROOT/phase_c/vla_lockstep_client.py" \
  "$ROOT/phase_c/lockstep_protocol.py" "$ROOT/phase_c/lockstep_common.py" \
  "$ROOT/phase_c/episodes/$EPISODE" "$ROOT/pydeps/casadi/__init__.py" "$PY" "$CONTROLLERS/controllers.py" \
  "$DUALVLN/models/InternVLA-N1-DualVLN/config.json" "$DUALVLN/models/depth_anything_v2_metric_hypersim_vits.pth"; do
  [[ -e $required ]] || { echo "required input missing: $required" >&2; exit 66; }
done
[[ -e $OUT ]] && { echo "run output already exists; refusing to overwrite evidence: $OUT" >&2; exit 73; }

CK=$(sha256sum "$INPUTS/checkpoint/model_149999.pt" | awk '{print $1}')
[[ $CK == a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450 ]] || { echo "checkpoint sha256 mismatch" >&2; exit 65; }
CS=$(sha256sum "$CONTROLLERS/controllers.py" | awk '{print $1}')
[[ $CS == 251522af6da05daee5279e07371b5f9ca319326e7097c0c7e5ae68e76217e408 ]] || { echo "controllers.py is not the pinned file" >&2; exit 65; }

sudo docker image inspect "$IMAGE" > /dev/null 2>&1 || { echo "image not present: $IMAGE" >&2; exit 66; }
if sudo docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then echo "container $CONTAINER exists" >&2; exit 73; fi
if sudo docker ps --format '{{.Names}}' | grep -qE '^vla-phase-[abc]-'; then echo "another vla-phase container is running" >&2; exit 75; fi
GPU_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
(( GPU_USED < 1000 )) || { echo "GPU already has ${GPU_USED} MiB in use by something else" >&2; exit 75; }
free_gb() { df -Pk "$ROOT" | awk 'NR==2 {printf "%d", $4 / 1048576}'; }
(( $(free_gb) >= 6 )) || { echo "only $(free_gb) GB free" >&2; exit 75; }

mkdir -p "$OUT/isaac" "$OUT/client" "$ROOT/home"
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_before.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_before.txt"
df -Pk "$ROOT" > "$OUT/disk_before.txt"
sudo chmod -R a+rwX "$OUT" "$ROOT/home"
PORT=$($PY -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')

ISAAC_PID=
CLIENT_PID=
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
      pkill -f "vla_lockstep_client.py --episode $ROOT/phase_c/episodes/$EPISODE --output-dir $OUT/client" || true
    fi
  done
) > "$OUT/samples.csv" 2>/dev/null &
SAMPLER=$!
cleanup() {
  kill "$SAMPLER" 2>/dev/null || true
  if sudo docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    sudo docker kill "$CONTAINER" > /dev/null 2>&1 || true
    echo "container still running at driver exit; killed" > "$OUT/CONTAINER_KILLED_BY_DRIVER"
  fi
  [[ -n $CLIENT_PID ]] && kill "$CLIENT_PID" 2>/dev/null || true
  true
}
trap cleanup EXIT

PYPATH=/workspace/inputs/lite3_sim_bridge:/workspace/inputs/v12_runtime/source/rsl_rl:/workspace/inputs/v12_runtime/source/robot_lab:$LAB/isaaclab:$LAB/isaaclab_tasks:$LAB/isaaclab_rl:$LAB/isaaclab_assets
sudo timeout --signal=TERM --kill-after=60 "${WALL_LIMIT}s" \
  docker run --rm --name "$CONTAINER" \
    --gpus all --network host \
    -v "$ROOT:/workspace" \
    -e HOME=/workspace/home -e PYTHONPATH="$PYPATH" \
    -e OMNI_KIT_ACCEPT_EULA=YES -e PRIVACY_CONSENT=N -e KMP_DUPLICATE_LIB_OK=TRUE \
    --entrypoint /isaac-sim/python.sh "$IMAGE" \
    /workspace/phase_c/isaac_lockstep_server.py \
      --episode "/workspace/phase_c/episodes/$EPISODE" \
      --output-dir "/workspace/runs/$RUN_ID/isaac" \
      --checkpoint /workspace/inputs/checkpoint/model_149999.pt \
      --vendored-rsl-rl /workspace/inputs/v12_runtime/source/rsl_rl \
      --tools-dir /workspace/tools \
      --port "$PORT" \
  > "$OUT/isaac.log" 2>&1 &
ISAAC_PID=$!

# The client loads the model while Isaac starts, then retries the connection until the server listens.
env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PYTHONPATH="$ROOT/pydeps" \
  timeout --signal=TERM --kill-after=30 "${WALL_LIMIT}s" \
  "$PY" "$ROOT/phase_c/vla_lockstep_client.py" \
    --episode "$ROOT/phase_c/episodes/$EPISODE" \
    --output-dir "$OUT/client" \
    --port "$PORT" \
    --agent "$AGENT" \
    --internnav-root "$INTERNNAV" \
    --model-path "$DUALVLN/models/InternVLA-N1-DualVLN" \
    --depth-anything "$DUALVLN/models/depth_anything_v2_metric_hypersim_vits.pth" \
    --controllers-dir "$CONTROLLERS" \
  > "$OUT/client.log" 2>&1 &
CLIENT_PID=$!

set +e
# If Isaac dies first (for example during start-up) the client would keep retrying its connection; stop it.
isaac_gone_since=
while kill -0 "$CLIENT_PID" 2>/dev/null; do
  if ! kill -0 "$ISAAC_PID" 2>/dev/null; then
    isaac_gone_since=${isaac_gone_since:-$(date +%s)}
    if (( $(date +%s) - isaac_gone_since > 60 )); then
      echo "isaac exited first; client stopped 60 s later" > "$OUT/CLIENT_KILLED_ISAAC_EXITED"
      kill "$CLIENT_PID" 2>/dev/null
    fi
  fi
  sleep 2
done
wait "$CLIENT_PID"; CLIENT_RC=$?
CLIENT_PID=
# A client that exits closes the socket, which ends the server's episode (client_end or client_lost); the server writes
# its record and closes the environment. Stop the container if that takes longer than 180 s.
for _ in $(seq 1 90); do
  kill -0 "$ISAAC_PID" 2>/dev/null || break
  sleep 2
done
if kill -0 "$ISAAC_PID" 2>/dev/null; then
  sudo docker kill "$CONTAINER" > /dev/null 2>&1
  echo "isaac still running 180 s after the client exited; killed" > "$OUT/ISAAC_KILLED_AFTER_CLIENT"
fi
wait "$ISAAC_PID"; ISAAC_RC=$?
set -e
kill "$SAMPLER" 2>/dev/null || true

sudo chown -R "$(id -u):$(id -g)" "$OUT" 2>/dev/null || true
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv > "$OUT/gpu_after.csv"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}}' > "$OUT/containers_after.txt"
df -Pk "$ROOT" > "$OUT/disk_after.txt"
echo "$ISAAC_RC $CLIENT_RC" > "$OUT/exit_codes"

# Video from the 10 Hz simulated-time frames: 10 fps plays back at real robot speed.
"$PY" - "$OUT/isaac/frames" <<'EOF' > "$OUT/video.log" 2>&1 || true
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
i, c = load(out / 'isaac' / 'isaac_episode.json'), load(out / 'client' / 'client_episode.json')
print('isaac_termination={} client_termination={} success={} stopped={} final_distance_m={} sim_s={} decisions={}'.format(
    i.get('termination'), c.get('termination'), c.get('success'), c.get('stopped_by_model'),
    None if i.get('final_distance_to_target_m') is None else round(i['final_distance_to_target_m'], 3),
    None if i.get('sim_seconds') is None else round(i['sim_seconds'], 2), c.get('decisions')))
EOF
)
echo "PHASE_C_RUN_DONE isaac_rc=$ISAAC_RC client_rc=$CLIENT_RC agent=$AGENT $SUMMARY"

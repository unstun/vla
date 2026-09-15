#!/usr/bin/env bash
# Bounded v3 service window: model + demo lifetime and rep_04..06 together.
set -u
R=/home/ubuntu/sun/vla_exec/2026-09-09_lightnav0_official_demo_rented4090
C=$R/continuation_v3
W=$R/work/LightNav-0-visual-v3
MODEL_PY=$R/work/LightNav-0/.venv/bin/python
DEMO_PY=$R/work/LightNav-0/mujoco_demo/.venv/bin/python
STAMP=$(date -u +%Y%m%d_%H%M%S)
JOB=$C/runs/model_server_v3_$STAMP
DEMOJOB=$C/runs/demo_server_v3_$STAMP
CAP=$C/runs/capture_v3_$STAMP
mkdir -p "$JOB" "$DEMOJOB" "$CAP"
echo "$STAMP" > $C/runs/CURRENT_STAMP

# Clear unintended task-shell overrides for this service window only.
unset LIGHTNAV_ATTN LIGHTNAV_SKIP_VERSION_GUARD VLLM_QUANT VLN_EVAL_TEMPERATURE \
      VLN_EVAL_TOP_K VLN_EVAL_TOP_P VLN_EVAL_TRAJ_TOP1 VLN_KV_CACHE_GIB \
      VLN_TIMESTAMP_RELATIVE VLN_VIT_CACHE_CPU VLN_VLLM_ENFORCE_EAGER ASPECT_MODE \
      MAX_BATCH_SIZE MAX_WAIT_MS TASK RECORD_FPS RECORD_TIMELINE RECORD_DIR \
      ACTION_TOKENIZER_BUNDLE CAM_HEIGHT CAM_HFOV_DEG WAYPOINT_DT_S HOST PORT
env | sort > $JOB/effective_env.txt

T0=$(date +%s.%N)
echo "service_window_start_utc=$(date -u +%FT%T.%3NZ)"

# Independent GPU/RAM sampler, ~0.2 s target interval.
nohup bash -c 'while true; do
  printf "%s,%s,%s\n" "$(date +%s.%N)" \
    "$(nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader,nounits | tr -d " ")" \
    "$(free -m | awk "/^Mem:/{print \$3\",\"\$2}")"
  sleep 0.2
done' > $C/runs/gpu_sampler_$STAMP.csv 2>/dev/null &
SAMPLER_PID=$!

PYTHONPATH=$W/src CUDA_VISIBLE_DEVICES=0 nohup $MODEL_PY -m lightnav.serving.ws_server \
  --task vln --backend vllm_local --model_path "$R/checkpoints/LightNav-0" \
  --host 127.0.0.1 --port 8050 --gpu_memory_utilization 0.80 --max_batch_size 8 \
  --record_dir "$C/records" --ready_file "$JOB/model.ready" \
  --cam_hfov_deg 112.2 --cam_height 0.198 \
  > $JOB/stdout.log 2> $JOB/stderr.log &
MODEL_PID=$!
echo "{\"pid\":$MODEL_PID,\"pgid\":$(ps -o pgid= -p $MODEL_PID | tr -d ' '),\"started_utc\":\"$(date -u +%FT%TZ)\",\"stamp\":\"$STAMP\"}" > $JOB/process.json
echo "model_pid=$MODEL_PID ready_file=$JOB/model.ready"

for i in $(seq 1 300); do
  [ -f "$JOB/model.ready" ] && { echo "model_ready_after=${i}s"; break; }
  kill -0 $MODEL_PID 2>/dev/null || { echo "MODEL_DIED_EARLY"; tail -25 $JOB/stderr.log; kill $SAMPLER_PID; exit 3; }
  sleep 1
done
[ -f "$JOB/model.ready" ] || { echo "MODEL_NOT_READY"; tail -25 $JOB/stderr.log; kill -TERM -$(ps -o pgid= -p $MODEL_PID|tr -d ' ') 2>/dev/null; kill $SAMPLER_PID; exit 4; }
ss -ltnp 2>/dev/null | grep ':8050' > $JOB/listener.txt

MUJOCO_GL=egl PYTHONPATH=$W/mujoco_demo LIGHTNAV_V3_TRACE_DIR=$CAP nohup $DEMO_PY -m vln_mujoco \
  --robot turtlebot --host 127.0.0.1 --port 8088 --vln-server ws://127.0.0.1:8050 \
  > $DEMOJOB/stdout.log 2> $DEMOJOB/stderr.log &
DEMO_PID=$!
echo "{\"pid\":$DEMO_PID,\"pgid\":$(ps -o pgid= -p $DEMO_PID | tr -d ' '),\"started_utc\":\"$(date -u +%FT%TZ)\",\"capture_dir\":\"$CAP\"}" > $DEMOJOB/process.json
for i in $(seq 1 90); do curl -sf http://127.0.0.1:8088/api/health -o /dev/null && { echo "demo_ready_after=${i}s"; break; }; sleep 1; done
ss -ltnp 2>/dev/null | grep ':8088' > $DEMOJOB/listener.txt
PYTHONPATH=$W/mujoco_demo $DEMO_PY -c "
import json, vln_mujoco.simulation as s, vln_mujoco.server as v, vln_mujoco.vln_client as c, vln_mujoco.v3_capture as p
print(json.dumps({k: m.__file__ for k, m in
  {'simulation': s, 'server': v, 'vln_client': c, 'v3_capture': p}.items()}))" > $DEMOJOB/module_files.json
cat $DEMOJOB/module_files.json

for REP in rep_04 rep_05 rep_06; do
  echo "=== $REP start $(date -u +%FT%T.%3NZ) ==="
  timeout 190 $DEMO_PY $C/scripts/run_episode_v3.py --rep $REP --run-dir $C/runs/$REP \
      --wall-timeout 180 --decision-cap 180 --post-stop 3.0 --reset-settle 2.0 \
      > $C/runs/${REP}_harness_stdout.log 2>&1
  echo "$REP exit=$?"
  python3 -c "import json;d=json.load(open('$C/runs/$REP/episode.json'));print(json.dumps({k:d[k] for k in ('termination','decisions','native_stop_observed','measured_seconds','end_pose')}))" 2>/dev/null
  sleep 2
done

echo "stopping services $(date -u +%FT%T.%3NZ)"
kill -TERM $DEMO_PID 2>/dev/null; sleep 4; kill -0 $DEMO_PID 2>/dev/null && kill -KILL $DEMO_PID
MODEL_PGID=$(ps -o pgid= -p $MODEL_PID 2>/dev/null | tr -d ' ')
kill -TERM $MODEL_PID 2>/dev/null; sleep 6
kill -0 $MODEL_PID 2>/dev/null && { kill -TERM -$MODEL_PGID 2>/dev/null; sleep 4; kill -KILL -$MODEL_PGID 2>/dev/null; }
kill $SAMPLER_PID 2>/dev/null
T1=$(date +%s.%N)
echo "service_window_seconds=$(echo "$T1 - $T0" | bc)"
echo "service_window_end_utc=$(date -u +%FT%T.%3NZ)"
sleep 2
$DEMO_PY $C/scripts/verify_capture.py $CAP $C/setup/capture_verification_$STAMP.json | tail -12
echo "--- remaining listeners ---"; ss -ltnp 2>/dev/null | grep -E ':(8050|8088)' || echo none
echo "--- protected workloads ---"; ps -eo pid,cmd | grep -E "kit/kit|runheadless" | grep -v grep | awk '{print $1}' | tr '\n' ' '; echo
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader

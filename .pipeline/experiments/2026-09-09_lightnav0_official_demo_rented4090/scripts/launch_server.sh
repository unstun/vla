#!/usr/bin/env bash
# Launch the official LightNav-0 model server.
# Run through: python3 scripts/run_job.py --seconds 7200 model_server -- bash scripts/launch_server.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/work/LightNav-0"
PORT=8050
CUDA_VISIBLE_DEVICES=0 .venv/bin/lightnav-serve \
  --task vln \
  --model_path "$ROOT/checkpoints/LightNav-0" \
  --backend vllm_local \
  --host 127.0.0.1 \
  --gpu_memory_utilization 0.80 \
  --ready_file "$ROOT/runs/model_server/model.ready" \
  --record_dir "$ROOT/records" \
  --cam_hfov_deg 112.2 \
  --cam_height 0.198

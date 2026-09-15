#!/usr/bin/env bash
# Launch the official MuJoCo demo server via upstream's own run.sh.
# Run through: python3 scripts/run_job.py --seconds 7200 demo_server -- bash scripts/launch_demo.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$ROOT/env/py311/bin:$PATH"
export UV_PYTHON="$ROOT/env/py311/bin/python"
export UV_PYTHON_DOWNLOADS=never
export UV_DEFAULT_INDEX="${PIP_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"
export UV_CACHE_DIR="$ROOT/env/uv_cache"
export MUJOCO_GL=egl
cd "$ROOT/work/LightNav-0/mujoco_demo"
exec ./run.sh --robot turtlebot --host 127.0.0.1 --port 8088 \
  --vln-server ws://127.0.0.1:8050

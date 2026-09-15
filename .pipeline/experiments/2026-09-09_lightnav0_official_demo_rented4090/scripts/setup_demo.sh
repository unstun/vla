#!/usr/bin/env bash
# The official MuJoCo demo's own uv project (mujoco_demo/), resolved against the same
# Python 3.11 interpreter. Runs the demo's CPU test suite once as an environment check.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export UV_PYTHON="$ROOT/env/py311/bin/python"
export UV_PYTHON_DOWNLOADS=never
export UV_DEFAULT_INDEX="${PIP_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"
export UV_CACHE_DIR="$ROOT/env/uv_cache"
export UV_LINK_MODE=copy
export PATH="$ROOT/env/py311/bin:$PATH"
export MUJOCO_GL=egl
cd "$ROOT/work/LightNav-0/mujoco_demo"
uv sync --extra dev
uv pip freeze --python .venv/bin/python > "$ROOT/setup/pip_freeze_demo.txt"
uv run --no-sync python -c "import mujoco, casadi, aiohttp, numpy; print('mujoco', mujoco.__version__, 'casadi', casadi.__version__, 'aiohttp', aiohttp.__version__, 'numpy', numpy.__version__)"
uv run --no-sync python -m pytest -q tests 2>&1 | tail -15
echo DEMO_SETUP_COMPLETE

#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_PYTHON="$TASK_ROOT/runtime/py311/bin/python"
export PIP_CACHE_DIR="$TASK_ROOT/runtime/pip_cache"
timeout 900 "$TASK_PYTHON" -m pip install \
  --index-url https://pypi.org/simple \
  --extra-index-url https://download.pytorch.org/whl/cu128 \
  'torch==2.7.0+cu128' 'torchvision==0.22.0+cu128' \
  -r "$TASK_ROOT/setup/runtime_requirements.txt"
timeout 180 "$TASK_PYTHON" -m pip install -e "$TASK_ROOT/work/acados/interfaces/acados_template"
"$TASK_PYTHON" -m pip freeze > "$TASK_ROOT/setup/pip_freeze.txt"

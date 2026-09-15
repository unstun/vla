#!/usr/bin/env bash
# Build the isolated Python 3.11 base interpreter (conda-forge via micromamba) and uv.
# The LightNav inference venv and the demo's uv project are created from this interpreter.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MM="$ROOT/tools/bin/micromamba"
export MAMBA_ROOT_PREFIX="$ROOT/env/mamba_root"
mkdir -p "$MAMBA_ROOT_PREFIX"
"$MM" --version
"$MM" create -y -p "$ROOT/env/py311" --override-channels -c conda-forge "python=3.11" pip
"$ROOT/env/py311/bin/python" --version
"$ROOT/env/py311/bin/python" -m pip install --disable-pip-version-check ${PIP_INDEX:+-i "$PIP_INDEX"} "uv==${UV_VERSION:-0.11.21}"
"$ROOT/env/py311/bin/uv" --version
"$MM" list -p "$ROOT/env/py311" > "$ROOT/setup/py311_conda_list.txt"
echo PY311_COMPLETE

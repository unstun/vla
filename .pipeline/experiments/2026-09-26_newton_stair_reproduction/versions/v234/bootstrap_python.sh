#!/usr/bin/env bash
set -eo pipefail
prefix=/home/ubuntu/sun/vla_v234_20261017
uv=$prefix/bootstrap/uv/bin/uv
python=$prefix/python/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12
lock=$prefix/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/hosts/2026-09-29_gpu5070ti/requirements_linux.lock
export UV_CACHE_DIR=$prefix/cache/uv UV_PYTHON_INSTALL_DIR=$prefix/python
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 UV_LINK_MODE=copy
test ! -e "$prefix/env/newton_worker"
"$python" --version
"$uv" venv --python "$python" "$prefix/env/newton_worker"
"$uv" pip install --python "$prefix/env/newton_worker/bin/python" \
  --require-hashes --no-deps --only-binary=:all: \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r "$lock"
"$uv" pip freeze --python "$prefix/env/newton_worker/bin/python" > "$prefix/evidence/python_freeze01.txt"

#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export MUJOCO_GL=egl
export MPLBACKEND=Agg
export ACADOS_SOURCE_DIR="$TASK_ROOT/work/acados"
export LD_LIBRARY_PATH="$ACADOS_SOURCE_DIR/lib:${LD_LIBRARY_PATH:-}"
export TERA_PATH="$TASK_ROOT/tools/t_renderer"
export X_NAVDP_MPC_CODEGEN_DIR="$TASK_ROOT/runtime/mpc_codegen"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=0
cd "$TASK_ROOT"
exec "$TASK_ROOT/runtime/py311/bin/python" "$@"

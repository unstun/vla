#!/usr/bin/env bash
# Task-owned launcher. Upstream installers run only inside the selected copy.
set -euo pipefail
task_root=${1:?usage: bootstrap.sh REMOTE_ROOT}
source_root="$task_root/source/AgentCanvas"
export PATH="/home/sun/miniconda3/bin:$PATH"
export PYTHONNOUSERSITE=1
mkdir -p "$task_root/setup"
exec 9>"$task_root/setup/bootstrap.lock"
flock -n 9 || { echo 'Another bootstrap is active'; exit 73; }
test "$(git -C "$source_root" rev-parse HEAD)" = b2b363af80a010ea9f73a0be9d49bc75555efdef
trap 'rc=$?; printf "%s\n" "$rc" > "$task_root/setup/bootstrap.exit"' EXIT
date -u +%FT%TZ > "$task_root/setup/bootstrap.started"
cd "$source_root"
if [[ ! -e "$task_root/setup/agentcanvas.installed" ]]; then
  bash scripts/install/install_agentcanvas.sh > "$task_root/setup/install_agentcanvas.log" 2>&1
  date -u +%FT%TZ > "$task_root/setup/agentcanvas.installed"
fi
if [[ ! -e "$task_root/setup/ac_vlnce.installed" ]]; then
  bash scripts/install/install_ac_vlnce.sh > "$task_root/setup/install_ac_vlnce.log" 2>&1
  date -u +%FT%TZ > "$task_root/setup/ac_vlnce.installed"
fi
bash scripts/data/materialize_r2r_rand100.sh
# The original installer skips this symlink when datasets are acquired later.
if [[ ! -e third_party/VLN-CE/data/datasets && ! -L third_party/VLN-CE/data/datasets ]]; then
  ln -s ../../../data/habitat/datasets third_party/VLN-CE/data/datasets
fi
/home/sun/miniconda3/envs/agentcanvas/bin/python -m pip install \
  -r "$task_root/configs/runner-compat.txt" > "$task_root/setup/runner_compat.log" 2>&1
/home/sun/miniconda3/envs/agentcanvas/bin/python -c 'from mcp.server.fastmcp import FastMCP, Image'
conda list -n agentcanvas --explicit > "$task_root/setup/agentcanvas_conda_explicit.txt"
conda list -n ac-vlnce --explicit > "$task_root/setup/ac_vlnce_conda_explicit.txt"
/home/sun/miniconda3/envs/agentcanvas/bin/python -m pip freeze > "$task_root/setup/agentcanvas_pip_freeze.txt"
/home/sun/miniconda3/envs/ac-vlnce/bin/python -m pip freeze > "$task_root/setup/ac_vlnce_pip_freeze.txt"
date -u +%FT%TZ > "$task_root/setup/bootstrap.finished"

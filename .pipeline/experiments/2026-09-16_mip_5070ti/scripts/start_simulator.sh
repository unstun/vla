#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
env_root=/home/sun/miniconda3/envs/ac-vlnce
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$env_root/lib:${LD_LIBRARY_PATH:-}"
export VLNCE_PYTHON="$env_root/bin/python"
cd "$root/source/AgentCanvas/agentcanvas/backend"
export PYTHONPATH="$PWD:$PWD/../.."
exec "$env_root/bin/python" -m app.server.auto_host \
  --file "$root/scripts/simulator_nodeset.py" \
  --class Rand100HabitatNodeSet --host 127.0.0.1 --port 19200

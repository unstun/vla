#!/usr/bin/env bash
set -euo pipefail
demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$demo_dir/../configs/remote_env.sh"
"$ISAAC_SIM_PYTHON" "$demo_dir/scripts/run_demo.py" --check
nohup "$ISAAC_SIM_PYTHON" "$demo_dir/scripts/run_demo.py" > "$demo_dir/logs/launcher.log" 2>&1 < /dev/null &
echo "DEMO_LAUNCHER_PID=$!"

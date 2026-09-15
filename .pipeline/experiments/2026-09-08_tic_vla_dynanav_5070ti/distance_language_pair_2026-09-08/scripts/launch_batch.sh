#!/usr/bin/env bash
set -euo pipefail
demo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
run_id="${1:?run id is required}"
camera_view="${2:-third_person}"
[[ "$camera_view" == "third_person" || "$camera_view" == "top_down" ]] || exit 2
[[ "$run_id" =~ ^[A-Za-z0-9_-]{1,64}$ ]] || exit 2
source "$demo_dir/../configs/remote_env.sh"
mkdir -p "$demo_dir/runs" "$demo_dir/logs"
if [[ -e "$demo_dir/runs/$run_id.delivery.json" || -e "$demo_dir/runs/$run_id" ]]; then
  echo "BATCH_ALREADY_DISPATCHED=$run_id"
  exit 0
fi
"$ISAAC_SIM_PYTHON" "$demo_dir/scripts/run_demo.py" --check
nohup "$ISAAC_SIM_PYTHON" "$demo_dir/scripts/batch_worker.py" "$run_id" "$camera_view" > "$demo_dir/logs/$run_id.batch.log" 2>&1 < /dev/null &
echo "BATCH_LAUNCHED=$run_id PID=$!"

set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v129/install/setup.bash
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/stop_contract -B /task/results/recovery_stop_contract/candidate/build
cmake --build /task/results/recovery_stop_contract/candidate/build -j2
set +e
/task/results/recovery_stop_contract/candidate/build/stop_transport /task/recovery_v129/install/lite3_nav2_plugins/lib/liblite3_bind_route_bt_node.so
code=$?
set -e
test "$code" = 0
python3 /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/stop_wait_probe.py --input /task/results/recovery_stop_contract/input.json --output /task/results/recovery_stop_contract/candidate/gateway.json

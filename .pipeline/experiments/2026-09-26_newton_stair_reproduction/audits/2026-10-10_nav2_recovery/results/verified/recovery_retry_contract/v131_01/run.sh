set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v131/install/setup.bash
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/retry_contract -B /task/results/recovery_retry_contract/v131_01/build
cmake --build /task/results/recovery_retry_contract/v131_01/build -j2
/task/results/recovery_retry_contract/v131_01/build/retry_probe /opt/ros/foxy/lib/libnav2_recovery_node_bt_node.so /task/recovery_v131/install/lite3_nav2_plugins/lib/liblite3_bind_route_bt_node.so /task/results/recovery_retry_contract/v131_01/fixture.xml 6

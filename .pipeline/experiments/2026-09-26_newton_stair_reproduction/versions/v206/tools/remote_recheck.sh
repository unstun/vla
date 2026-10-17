#!/usr/bin/env bash
set -eo pipefail
cd /work
mkdir -p evidence
python3 - <<'PY'
import hashlib,json
from pathlib import Path
root=Path('/work');record=json.loads((root/'source_inventory.json').read_text())
for rel,expected in record.items():
    assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==expected,rel
(root/'evidence/source_gate.json').write_text(json.dumps({'verified':len(record),'files':record},indent=2)+'\n')
print('Verified v206 source files:',len(record))
PY
source /opt/ros/foxy/setup.bash
source /task/recovery_v188/install/setup.bash
export CMAKE_PREFIX_PATH=/task/recovery_v168/dependencies/osqp-install:$CMAKE_PREFIX_PATH
export MAKEFLAGS=-j4 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
# Rebuild the exported native dependencies as well: no ARM64 binaries or old
# controller ABI are copied into this Linux x86_64 execution workspace.
colcon build --packages-select scan_nav2_controller --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3 2>&1 | tee evidence/build-final.log
source /work/install/setup.bash

export ROS_DOMAIN_ID=206
export ROUTE_ORACLE=/work/fixtures/route-oracle.yaml
export TERRAIN_TEST_MANIFEST=/work/fixtures/building/terrain.json
export TERRAIN_TEST_DIRECTORY=/work/fixtures/building
export TERRAIN_NATIVE_CONFIG=/work/fixtures/building_planner.yaml
export TERRAIN_NATIVE_PROFILE=/work/fixtures/component.scan.yaml
export TERRAIN_TEST_PROFILE=/work/fixtures/component.yaml
export PCT_TEST_MAP=/work/fixtures/flat.pct
colcon test --packages-select scan_nav2_controller --executor sequential --return-code-on-test-failure --ctest-args -R '^(test_route_policy|test_direct_pct|test_wait_recovery|test_static_terrain|test_terrain_profile|test_map_shell|test_static_support|test_reference_path_utils|test_motion_exchange|test_controller|test_tracking_parity|test_tracking_behavior|test_executor_shutdown|test_terminal_completion|test_command_owner|test_terminal_tree|test_mission_bridge)$' 2>&1 | tee evidence/test-final.log
colcon test-result --verbose 2>&1 | tee evidence/test-result.log

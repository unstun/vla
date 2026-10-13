#!/usr/bin/env bash
# Run inside the task-owned x86_64 Foxy container, with /task and /repo mounted.
set -eo pipefail
test "$(uname -m)" = x86_64
source /opt/ros/foxy/setup.bash
test "$ROS_DISTRO" = foxy
dpkg-query -W > /task/results/packages.tsv
python3 -m pip freeze > /task/results/foxy_python.txt
for variant in baseline candidate; do
  cd "/task/$variant"
  python3 - <<'PY'
from pathlib import Path
import hashlib, json
record = json.loads(Path('source_identity.json').read_text())
for name, expected in record['files'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, name
print('EXPORTED_SOURCE_PASS', record['version'])
PY
  cmake -S third_party/osqp -B dependencies/osqp-build \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
    -DCMAKE_INSTALL_PREFIX="$PWD/dependencies/osqp-install" \
    -DFETCHCONTENT_SOURCE_DIR_QDLDL="$PWD/third_party/qdldl" \
    -DOSQP_BUILD_DEMO_EXE=OFF -DOSQP_BUILD_UNITTESTS=OFF
  cmake --build dependencies/osqp-build -j2
  cmake --install dependencies/osqp-build
  CMAKE_PREFIX_PATH="$PWD/dependencies/osqp-install:$CMAKE_PREFIX_PATH" \
  MAKEFLAGS=-j2 colcon build --base-paths src --executor sequential --cmake-args \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
    -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3 \
    > "/task/results/$variant-build.log" 2>&1
  colcon test --base-paths src --packages-select scan_nav2_controller lite3_nav2_plugins \
    --executor sequential --return-code-on-test-failure \
    > "/task/results/$variant-tests.log" 2>&1
  colcon test-result --verbose >> "/task/results/$variant-tests.log" 2>&1
done
source /task/candidate/install/setup.bash
version=/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v122
cmake -S "$version" -B /task/probes -DCMAKE_BUILD_TYPE=Release
cmake --build /task/probes -j2
/task/probes/native_outcome_probe --ros-args --params-file "$version/building_planner.yaml" \
  > /task/results/native_outcome_probe.log 2>&1
g++ -std=c++17 -O2 -I "$version/src/plan_manage/include" \
  "$version/outcome_contract_test.cpp" -o /task/probes/outcome_contract_assertions
/task/probes/outcome_contract_assertions > /task/results/outcome_contract.log
printf 'V123_NATIVE_BUILD_TESTS_PASS\n'

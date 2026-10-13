#!/usr/bin/env bash
# Build a verified source export. Dependencies must already be installed.
set -eo pipefail
cd "$(dirname "$0")"
test "$(uname -m)" = aarch64
source /opt/ros/foxy/setup.bash
python3 - <<'PY'
from pathlib import Path
import hashlib, json
root = Path.cwd()
record = json.loads((root/'source_identity.json').read_text())
assert record['version'] == 'v107'
for name, expected in record['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
print('Portable source identity verified')
PY
NAV_CMAKE=${LITE3_NAV_CMAKE:-cmake}
"$NAV_CMAKE" -S third_party/osqp -B dependencies/osqp-build \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DCMAKE_INSTALL_PREFIX="$PWD/dependencies/osqp-install" \
  -DFETCHCONTENT_SOURCE_DIR_QDLDL="$PWD/third_party/qdldl" \
  -DOSQP_BUILD_DEMO_EXE=OFF -DOSQP_BUILD_UNITTESTS=OFF
"$NAV_CMAKE" --build dependencies/osqp-build -j2
"$NAV_CMAKE" --install dependencies/osqp-build
export CMAKE_PREFIX_PATH="$PWD/dependencies/osqp-install:${CMAKE_PREFIX_PATH:-}"
colcon build --base-paths src --executor sequential --cmake-args \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3
colcon test --base-paths src --packages-select scan_nav2_controller lite3_nav2_plugins \
  --executor sequential --return-code-on-test-failure
colcon test-result --verbose

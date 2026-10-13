#!/bin/bash
# Run K5 (ros_smoke.py) in the pinned image with the environment native_inside.sh uses. Writes ros_smoke.json and
# ros_smoke_stdout.log into versions/v33 (the only writable mount).
set -euo pipefail
P=/Users/sun/tongbu/study/phdproject/vla
E="${P}/.pipeline/experiments/2026-09-26_newton_stair_reproduction"
docker run --rm --pull=never --platform=linux/amd64 -e ROS_DOMAIN_ID=219 -e ROS_LOCALHOST_ONLY=1 \
  -e PYTHONDONTWRITEBYTECODE=1 -v "${P}:${P}:ro" -v "${E}/versions/v33:${E}/versions/v33:rw" \
  -v "${E}/runtime/scan64_input_refresh_v31:/workspace:ro" --entrypoint /bin/bash \
  sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb -c "
set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
export PYTHONPATH=${E}/runtime/foreground_py310:${E}/runtime_sources/backend_adapter:${E}/runtime_sources/backend_ros:${E}/runtime_sources/bridge:${E}/runtime_sources/pct_runtime/python:\${PYTHONPATH:-}
export LD_LIBRARY_PATH=${E}/runtime_sources/pct_runtime/lib:\${LD_LIBRARY_PATH:-}
python3 ${E}/versions/v33/ros_smoke.py" 2>&1 | tee "${E}/versions/v33/ros_smoke_stdout.log"

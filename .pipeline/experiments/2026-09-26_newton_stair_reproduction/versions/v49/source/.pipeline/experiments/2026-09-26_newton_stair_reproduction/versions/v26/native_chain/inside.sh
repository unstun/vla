#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/base/runtime_sources/backend_adapter:/base/runtime_sources/backend_ros:/base/runtime_sources/bridge:/base/runtime_sources:/base/runtime_sources/pct_runtime/python:${PYTHONPATH:-}
export LD_LIBRARY_PATH=/base/runtime_sources/pct_runtime/lib:${LD_LIBRARY_PATH:-}
export OPENBLAS_NUM_THREADS=1
export ROS_DOMAIN_ID=233
python3 /audit/probe.py

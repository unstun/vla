set -e
source /opt/ros/humble/setup.bash
export PYTHONPATH=/base/runtime_sources/backend_adapter:/base/runtime_sources/pct_runtime/python:"${PYTHONPATH:-}"
export LD_LIBRARY_PATH=/base/runtime_sources/pct_runtime/lib:"${LD_LIBRARY_PATH:-}"
export OPENBLAS_NUM_THREADS=1
python3 /audit/probe.py

set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
export PYTHONPATH=/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v50/backend_ros:/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/foreground_py310:/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime_sources/backend_adapter:/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime_sources/backend_ros:/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime_sources/bridge:/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime_sources/pct_runtime/python:"${PYTHONPATH:-}"
export LD_LIBRARY_PATH=/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime_sources/pct_runtime/lib:"${LD_LIBRARY_PATH:-}"
exec python3 /home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v50/native_graph.py --output /home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runs/v50_realtime_trial01

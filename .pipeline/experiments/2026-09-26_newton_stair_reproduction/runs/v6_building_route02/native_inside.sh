set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
export PYTHONPATH=/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/foreground_py310:/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime_sources/backend_adapter:/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime_sources/backend_ros:/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime_sources/bridge:/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime_sources/pct_runtime/python:"${PYTHONPATH:-}"
export LD_LIBRARY_PATH=/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime_sources/pct_runtime/lib:"${LD_LIBRARY_PATH:-}"
exec python3 /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/scripts/native_graph.py --output /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runs/v6_building_route02

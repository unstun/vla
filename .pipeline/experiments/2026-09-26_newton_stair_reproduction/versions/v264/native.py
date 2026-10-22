"""Read-only installed-native saved-output and endpoint diagnostics."""
from pathlib import Path
import os,subprocess,sys
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'saved_output_audit_v264';OUT.mkdir(exist_ok=True)
V='/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
A='/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v259_equivalent_geometry_repairs'
shell='set -eo pipefail; source /opt/ros/foxy/setup.bash; source /task/recovery_v188/install/setup.bash; source /task/command_continuity_v206_20261015/install/setup.bash; source /task/callback_failure_v232/install/setup.bash; source /task/cooperative_search_v240/install/setup.bash; source /task/physical_traversability_v247/native/install/setup.bash; source /work/install/setup.bash; export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=154 ROS_LOCALHOST_ONLY=1; export REPLAY_INPUT=/work/fixtures/building; source /work/fixtures/probe225.env; '
operation=sys.argv[1]
if operation=='build':shell+=f'cmake -S {V}/v264 -B /evaluation/build -DVERSIONS_ROOT={V} -DAUDIT_ROOT={A} -DCMAKE_BUILD_TYPE=Release; cmake --build /evaluation/build -j2'
elif operation=='witness':shell+='exec /evaluation/build/endpoint_witness /evaluation/endpoints.txt "/evaluation/${1:-endpoints.csv}"'
elif operation=='curve':
    assert len(sys.argv)==5
    shell+='export CASE_INPUT="$1" SAVED_SPLINE="$2" PROBE_OUTPUT="$3"; exec /evaluation/build/runtime_curve_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn'
else:raise ValueError(operation)
command=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--cpus=2','--memory=6g','--network=host','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs',
 '-v',str(BASE)+':/task:ro','-v',str(BASE/'generic_mechanisms_v261/native')+':/work:ro','-v',str(OUT)+':/evaluation:rw',
 '--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4',
 '-c',shell,'v264',*sys.argv[2:]]
raise SystemExit(subprocess.run(command).returncode)

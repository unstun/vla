"""Build changed static libraries and every native consumer; preserve RL/sensors."""
from pathlib import Path
import os,subprocess
BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'generic_mechanisms_v254/native'
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /task/cooperative_search_v240/install/setup.bash'
shell+=' && source /task/physical_traversability_v247/native/install/setup.bash && export CMAKE_PREFIX_PATH=/task/recovery_v168/dependencies/osqp-install:$CMAKE_PREFIX_PATH && export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MAKEFLAGS=-j2 && cd /work && colcon --log-base build_logs build --base-paths src --packages-select plan_env pct_planner path_searching bspline_opt scan_planner scan_nav2_controller lite3_nav2_plugins --executor sequential --cmake-clean-cache --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3'
subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--cpus=2','--memory=6g','-v',str(BASE)+':/task:ro','-v',str(WORK)+':/work:rw',
 '--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],check=True)

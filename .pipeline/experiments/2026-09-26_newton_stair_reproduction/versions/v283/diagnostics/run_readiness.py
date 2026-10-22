from pathlib import Path
import os,subprocess
BASE=Path('/data/sun/vla_mppi_20261009')
ROOT=Path('/home/sun/vla_exec/navigation_geometry_v283')
SOURCE=Path(__file__).resolve().parent/'readiness'
OUT=ROOT/'readiness';OUT.mkdir(exist_ok=True)
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /work/install/setup.bash && export ROS_DOMAIN_ID=155 ROS_LOCALHOST_ONLY=1 && cmake -S /source -B /audit/build -DCMAKE_BUILD_TYPE=Release && cmake --build /audit/build -j2 && /audit/build/readiness_probe'
raise SystemExit(subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=3g','-e','ROS_LOG_DIR=/audit/ros_logs','-v',str(BASE)+':/task:ro','-v',str(ROOT/'native')+':/work:ro','-v',str(SOURCE)+':/source:ro','-v',str(OUT)+':/audit:rw','--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell]).returncode)

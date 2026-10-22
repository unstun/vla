from pathlib import Path
import os,subprocess
BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'generic_mechanisms_v265/native'
subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--network=host','-e','ROS_HOME=/work/ros_home','-e','ROS_LOG_DIR=/work/ros_logs','-e','ROS_DOMAIN_ID=144','-e','ROS_LOCALHOST_ONLY=1','--cpus=2','--memory=6g',
 '-v',str(BASE)+':/task:ro','-v',str(WORK)+':/work:rw',
 '--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4',
 '/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v265/native_regressions.sh'],check=True)

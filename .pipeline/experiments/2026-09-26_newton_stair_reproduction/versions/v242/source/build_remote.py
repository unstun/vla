"""Owned read-only native overlay with private evaluation output."""
from pathlib import Path
import os,subprocess,sys
BASE=Path('/data/sun/vla_mppi_20261009')
OUT=BASE/'generalization_v242'
OUT.mkdir(exist_ok=True)
image='sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4'
cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--memory=6g','--cpus=6','--network=host','-e','ROS_DOMAIN_ID=142',
 '-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs',
 '-v',str(BASE)+':/task:ro','-v',str(BASE/'cooperative_search_v240')+':/work:ro',
 '-v',str(BASE/'callback_failure_v232/fixtures')+':/work/fixtures:ro',
 '-v',str(OUT)+':/evaluation:rw','--entrypoint','/bin/bash',image,
 '/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v242/native.sh']
raise SystemExit(subprocess.run(cmd+sys.argv[1:]).returncode)

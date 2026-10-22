"""Owned read-only native overlay with private evaluation output."""
from pathlib import Path
import os,subprocess,sys
BASE=Path('/data/sun/vla_mppi_20261009')
OUT=BASE/'space_coverage_v257'
OUT.mkdir(parents=True,exist_ok=True)
image='sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4'
cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--memory=6g','--cpus=2','--network=host','-e','ROS_DOMAIN_ID=157',
 '-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs',
 '-v',str(BASE)+':/task:ro','-v',str(BASE/'generic_mechanisms_v256/native')+(':/work:rw' if sys.argv[1:] == ['test'] else ':/work:ro'),
 
 '-v',str(OUT)+':/evaluation:rw','--entrypoint','/bin/bash',image,
 '/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v257/native.sh']
if os.environ.get('V257_CONTAINER_NAME'):cmd[2:2]=['--name',os.environ['V257_CONTAINER_NAME']]
if os.environ.get('GLOBAL_ONLY'):cmd[2:2]=['-e','GLOBAL_ONLY=1']
if os.environ.get('SCREEN_POSES'):cmd[2:2]=['-e','SCREEN_POSES='+os.environ['SCREEN_POSES']]
raise SystemExit(subprocess.run(cmd+sys.argv[1:]).returncode)

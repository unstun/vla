from pathlib import Path
import os,subprocess,sys
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'endpoint_connectivity_v244/evaluation';OUT.mkdir(exist_ok=True)
cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--memory=6g','--cpus=6','--network=host','-e','ROS_DOMAIN_ID=142','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs',
 '-v',str(BASE)+':/task:ro','-v',str(BASE/'endpoint_connectivity_v244/native')+(':/work:rw' if sys.argv[1] in ('build','test') else ':/work:ro'),
 '-v',str(BASE/'callback_failure_v232/fixtures')+':/work/fixtures:ro','-v',str(OUT)+':/evaluation:rw',
 '-v',str(BASE/'generalization_v242/cases')+':/cases:ro','--entrypoint','/bin/bash',
 'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4',
 '/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v244/native.sh']
raise SystemExit(subprocess.run(cmd+sys.argv[1:]).returncode)

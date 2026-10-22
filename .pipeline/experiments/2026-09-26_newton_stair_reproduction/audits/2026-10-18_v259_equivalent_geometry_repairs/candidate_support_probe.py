"""Isolated source-evidence ablation using installed native floor scoring."""
from pathlib import Path
import os,subprocess
BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'generic_mechanisms_v259/native';OUT=BASE/'generic_mechanisms_v260/candidate_export03';OUT.mkdir(parents=True,exist_ok=True)
candidate=BASE/'generic_mechanisms_v260/floor_candidate02'
cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','--network=host','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs','-v',str(BASE)+':/task:ro','-v',str(WORK)+':/work:ro','-v',str(OUT)+':/evaluation:rw','-v',str(BASE/'generic_mechanisms_v259/evaluation/build')+':/evaluation/build:ro']
cmd+=['-v',str(candidate/'floor_candidate.scan.yaml')+':/work/fixtures/environment_candidate228.scan.yaml:ro']
for name in ('surface.f32','physical_floor.f32'):
 cmd+=['-v',str(candidate/name)+':/work/fixtures/building/'+name+':ro']
cmd+=['--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v259/native.sh','support']
with (OUT/'support_export.log').open('x') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)

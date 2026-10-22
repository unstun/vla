from pathlib import Path
import json,subprocess,os,hashlib
R=Path('/home/ubuntu/sun/vla_v288_20261020');V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','--network=host','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs','-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1','-v',str(R)+':/task:ro','-v',str(R/'native')+':/work:rw','-v',str(R/'evaluation03')+':/evaluation:rw','-v',str(V)+':/source:ro','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','-c','source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && /evaluation/build/repair_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn']
log=R/'evidence/repair05.log'
with log.open('x') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
(R/'evidence/repair05.json').write_text(json.dumps(dict(passed=code==0,returncode=code,probe_source_sha256=sha(V/'repair_probe.cpp'),probe_binary_sha256=sha(R/'evaluation03/build/repair_probe'),log_sha256=sha(log),physics_steps=0),indent=2)+'\n');assert code==0
subprocess.run(['python3',str(R/'migration/bind.py')],check=True)
with (R/'evidence/geometry_contract01.log').open('x') as f:subprocess.run(['python3',str(R/'run_native.py'),'contract'],stdout=f,stderr=subprocess.STDOUT,check=True)
subprocess.run(['python3',str(R/'migration/offline.py'),'qualify'],check=True)

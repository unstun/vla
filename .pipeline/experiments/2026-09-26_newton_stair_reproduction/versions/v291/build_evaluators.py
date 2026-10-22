"""Rebuild unchanged native evaluators against v291 install; no physics."""
from pathlib import Path
import hashlib,json,os,subprocess,time
R=Path('/home/ubuntu/sun/vla_v291_20261022');P=Path('/home/ubuntu/sun/vla_v289_20261020')
IMAGE='sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'
report={'physics_steps':0,'checks':[],'passed':False};receipt=R/'evidence/evaluators01.json';assert not receipt.exists()
for label,shell in [
 ('build','cmake -S /source -B /evaluation/build -DCMAKE_BUILD_TYPE=Release -DVERSIONS_ROOT=/parent/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions && cmake --build /evaluation/build -j2'),
 ('geometry','/evaluation/build/geometry_contract_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level error')]:
 cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','--network=host','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs']
 for host,guest in [(R/'native','/work:ro'),(P,'/parent:ro'),(P/'native/fixtures','/work/fixtures:ro'),(R/'source','/source:ro'),(R/'evaluation','/evaluation:rw'),(P/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v224','/task/source_v224:ro')]: cmd+=['-v',str(host)+':'+guest]
 cmd+=['--entrypoint','/bin/bash',IMAGE,'-c','source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && source /work/fixtures/probe271.env && export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=161 ROS_LOCALHOST_ONLY=1 && '+shell]
 log=R/f'evidence/evaluators01_{label}.log';start=time.monotonic()
 with log.open('x') as f: code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 report['checks'].append(dict(name=label,returncode=code,wall_s=time.monotonic()-start,command=cmd,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()));receipt.write_text(json.dumps(report,indent=2)+'\n');print(label,code,flush=True)
 if code: raise SystemExit(code)
report['passed']=True;receipt.write_text(json.dumps(report,indent=2)+'\n')

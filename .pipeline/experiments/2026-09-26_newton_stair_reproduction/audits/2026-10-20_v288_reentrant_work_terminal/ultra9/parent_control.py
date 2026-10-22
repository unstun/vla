from pathlib import Path
import subprocess,os,json,hashlib,time
R=Path('/home/ubuntu/sun/vla_v288_20261020');P=Path('/home/ubuntu/sun/vla_v287_20261020');V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288';E=R/('parent_control'+os.environ.get('V288_PARENT_ID','02'));E.mkdir()
common='source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=155 && '
commands=[('build','cmake -S /source -B /evaluation/build -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS=-DPARENT_WORK_CONTROL && cmake --build /evaluation/build --target work_probe repair_probe field_probe -j2'),('work','/evaluation/build/work_probe'),('repair','/evaluation/build/repair_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn'),('field','/evaluation/build/field_probe')]
results=[]
for label,shell in commands:
 cmd=['docker','run','--rm','--pull=never','--name','v288-parent-'+label,'--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','--network=host','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs','-v',str(R)+':/task:ro','-v',str(P/'native')+':/work:ro','-v',str(E)+':/evaluation:rw','-v',str(V)+':/source:ro','-v',str(R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v224')+':/task/source_v224:ro','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','-c',common+shell]
 log=E/(label+'.log');t=time.monotonic()
 with log.open('x') as out:rc=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT).returncode
 results.append(dict(name=label,returncode=rc,wall_s=time.monotonic()-t,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
 (E/'results.json').write_text(json.dumps(results,indent=2)+'\n')
 if label=='build' and rc:break
print(json.dumps(results))

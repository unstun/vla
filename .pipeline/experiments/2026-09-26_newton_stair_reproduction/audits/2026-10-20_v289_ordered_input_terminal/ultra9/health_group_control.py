from pathlib import Path
import subprocess,os,json,hashlib
R=Path('/home/ubuntu/sun/vla_v289_20261020');P=Path('/home/ubuntu/sun/vla_v288_20261020')
V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v289'
OUT=R/'health_group_control';OUT.mkdir(exist_ok=False)
rows=[]
for name,root in [('parent',P),('candidate',R)]:
 out=OUT/name;out.mkdir();(out/'ros_logs').mkdir();(out/'ros_home').mkdir()
 shell='source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && export PYTHONPATH=/work/src/lite3_nav2_bridge:$PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=156 ROS_LOCALHOST_ONLY=1 && python3 -m pytest -q /source/src/lite3_nav2_bridge/test/test_mission_bridge.py -k liveness_responses_continue --junitxml=/out/result.xml --basetemp=/out/tmp'
 cmd=['docker','run','--rm','--pull=never','--network=host','--cpus=1','--memory=2g','--user',f'{os.getuid()}:{os.getgid()}','-e','ROS_HOME=/out/ros_home','-e','ROS_LOG_DIR=/out/ros_logs','-v',str(root/'native')+':/work:ro','-v',str(V)+':/source:ro','-v',str(out)+':/out:rw','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','-c',shell]
 log=out/'test.log'
 with log.open('x') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 rows.append(dict(name=name,returncode=code,command=cmd,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
result=dict(passed=rows[0]['returncode']==1 and rows[1]['returncode']==0,rows=rows,physics_steps=0)
(R/'evidence/health_group_control01.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));assert result['passed']

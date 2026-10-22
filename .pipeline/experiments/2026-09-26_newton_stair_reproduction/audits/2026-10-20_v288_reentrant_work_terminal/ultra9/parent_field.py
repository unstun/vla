from pathlib import Path
import os,subprocess,json,time
R=Path('/home/ubuntu/sun/vla_v288_20261020');O=Path('/home/ubuntu/sun/vla_v286_20261020');V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288'
D=R/'parent_field02';D.mkdir()
cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','-v',str(O/'native')+':/work:ro','-v',str(V)+':/source:ro','-v',str(D)+':/evaluation:rw','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','-c','source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && c++ -std=c++17 -O2 -I/work/install/plan_env/include -I/usr/include/eigen3 /source/field_probe.cpp -L/work/install/plan_env/lib -lplan_env -Wl,--allow-shlib-undefined -o /evaluation/field_probe && /evaluation/field_probe']
with (R/'evidence/parent_field02.log').open('x') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
(R/'evidence/parent_field02.json').write_text(json.dumps(dict(expected_failure=True,returncode=code,physics_steps=0,scope='Same ENV escape regression linked against immutable v286 installed plan_env'),indent=2)+'\n')
assert code==1

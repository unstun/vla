from pathlib import Path
import subprocess,os,time,json,hashlib
R=Path('/home/ubuntu/sun/vla_v289_20261020');P=Path('/home/ubuntu/sun/vla_v288_20261020')
V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v289'
OUT=R/'body_order_control';OUT.mkdir(exist_ok=False)
rows=[]
for name,include in [('parent',P/'native/src/plan_env/include'),('candidate',V/'src/plan_env/include')]:
 shell='g++ -std=c++17 -pthread -I/include -I/opt/ros/foxy/include /source/src/plan_env/test/test_body_time_buffer.cpp -lgtest_main -lgtest -o /out/'+name+' && /out/'+name+' --gtest_output=xml:/out/'+name+'.xml'
 cmd=['docker','run','--rm','--pull=never','--cpus=1','--memory=1g','--user',f'{os.getuid()}:{os.getgid()}','-v',str(include)+':/include:ro','-v',str(V)+':/source:ro','-v',str(OUT)+':/out:rw','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','-c',shell]
 log=OUT/(name+'.log')
 with log.open('x') as stream:code=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT).returncode
 rows.append(dict(name=name,returncode=code,command=cmd,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
print(json.dumps(rows))
(R/'evidence/body_order_control01.json').write_text(json.dumps(dict(passed=rows[0]['returncode']!=0 and rows[1]['returncode']==0,rows=rows,physics_steps=0),indent=2)+'\n')

assert rows[0]['returncode']!=0 and rows[1]['returncode']==0, rows

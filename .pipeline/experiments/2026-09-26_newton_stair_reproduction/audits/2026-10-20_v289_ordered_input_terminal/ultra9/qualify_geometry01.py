from pathlib import Path
import subprocess,os,json,hashlib
import offline
R=offline.ROOT;V=offline.HERE
assert json.loads((R/'evidence/components03.json').read_text())['stage']=='passed'
offline.qualify()
cmd=['docker','run','--rm','--pull=never','--cpus=2','--memory=3g','--user',f'{os.getuid()}:{os.getgid()}','-v',str(R)+':/task:ro','-v',str(R/'native')+':/work:ro','--entrypoint','/bin/bash',offline.IMAGE,'-c','source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && python3 /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v289/preflight.py']
log=R/'evidence/single_install_preflight01.log'
with log.open('x') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
(R/'evidence/single_install_preflight01.json').write_text(json.dumps(dict(passed=code==0,command=cmd,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),physics_steps=0),indent=2)+'\n')
assert code==0

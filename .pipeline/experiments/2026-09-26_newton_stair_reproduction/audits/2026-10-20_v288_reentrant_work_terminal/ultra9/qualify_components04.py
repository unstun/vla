from pathlib import Path
import subprocess,json,os,hashlib,shutil,time
R=Path('/home/ubuntu/sun/vla_v288_20261020');V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((R/'evidence/build03_closed.json').read_text())['passed']
old=json.loads((R/'evidence/components03.json').read_text());assert all(c['returncode']==0 for c in old['checks'] if c['name']!='regressions')
(R/'native/regressions').rename(R/'native/regressions03_failed')
cmd=['docker','run','--rm','--pull=never','--name','v288-regressions04','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','--network=host','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs','-v',str(R)+':/task:ro','-v',str(R/'native')+':/work:rw','-v',str(R/'evaluation03')+':/evaluation:rw','-v',str(R/'native/fixtures')+':/task/generic_mechanisms_v259/native/fixtures:ro','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','/evaluation/regressions.sh']
log=R/'evidence/components04_regressions.log';t=time.monotonic()
with log.open('x') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
out=dict(old,stage='passed' if rc==0 else 'failed',source_inventory_sha256=sha(V/'source_inventory.json'),previous_failed_receipt_sha256=sha(R/'evidence/components03.json'),fixture_fix='Provide the production GridMap owner in the isolated callback-exception fixture; no null-owner fallback in production')
out['checks']=[c for c in old['checks'] if c['name']!='regressions']+[dict(name='regressions',returncode=rc,wall_s=time.monotonic()-t,log=str(log),sha256=sha(log))]
(R/'evidence/components04.json').write_text(json.dumps(out,indent=2)+'\n');raise SystemExit(rc)

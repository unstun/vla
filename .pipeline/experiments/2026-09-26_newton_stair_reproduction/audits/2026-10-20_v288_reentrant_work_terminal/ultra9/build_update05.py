from pathlib import Path
import json,hashlib,shutil,subprocess,time,os
R=Path('/home/ubuntu/sun/vla_v288_20261020');V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288'
assert json.loads((R/'evidence/build01_closed.json').read_text())['passed']
inv=json.loads((V/'source_inventory.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copytree(V/'src',R/'native/src',dirs_exist_ok=True);shutil.copy2(V/'source_inventory.json',R/'native/source_inventory.json')
for rel,h in inv.items():assert sha(R/'native'/rel)==h,rel
cmd=['docker','run','--rm','--pull=never','--name','v288-build05','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','-v',str(R/'native')+':/work:rw','-v',str(R/'migration')+':/source:ro','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','/source/build_native.sh']
t=time.monotonic()
with (R/'evidence/build05.log').open('x') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
(R/'evidence/build05_closed.json').write_text(json.dumps(dict(passed=code==0,returncode=code,wall_s=time.monotonic()-t,source_files=len(inv),source_inventory_sha256=sha(V/'source_inventory.json'),command=cmd,log_sha256=sha(R/'evidence/build05.log')),indent=2)+'\n')
raise SystemExit(code)

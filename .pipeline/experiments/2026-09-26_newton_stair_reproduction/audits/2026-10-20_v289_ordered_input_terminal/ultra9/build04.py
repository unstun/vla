from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
R=Path('/home/ubuntu/sun/vla_v289_20261020'); V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v289'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((R/'evidence/build03_closed.json').read_text())['passed']
shutil.copy2(R/'native/source_inventory.json',R/'evidence/source_inventory_build03.json')
shutil.copytree(V/'src',R/'native/src',dirs_exist_ok=True);shutil.copy2(V/'source_inventory.json',R/'native/source_inventory.json')
inv=json.loads((R/'native/source_inventory.json').read_text())
for rel,h in inv.items():assert sha(R/'native'/rel)==h,rel
cmd=['docker','run','--rm','--pull=never','--name','v289-build04','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','-v',str(R/'native')+':/work:rw','-v',str(R/'migration')+':/source:ro','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','/source/build_native.sh']
t=time.monotonic()
with (R/'evidence/build04.log').open('x') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
(R/'evidence/build04_closed.json').write_text(json.dumps(dict(passed=code==0,returncode=code,wall_s=time.monotonic()-t,source_files=len(inv),source_inventory_sha256=sha(R/'native/source_inventory.json'),command=cmd,log_sha256=sha(R/'evidence/build04.log')),indent=2)+'\n')
raise SystemExit(code)

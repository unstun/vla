from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
R=Path('/home/ubuntu/sun/vla_v290_20261021');P=Path('/home/ubuntu/sun/vla_v289_20261020')
tag=os.environ.get('V290_BUILD_ID','01')
V=R/'source';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (R/f'evidence/build{tag}_closed.json').exists()
(R/'evidence').mkdir(exist_ok=True);(R/'native').mkdir(exist_ok=True)
for name in ['src','dependencies']:
 if not (R/'native'/name).exists():shutil.copytree(P/'native'/name,R/'native'/name)
shutil.copytree(V/'src',R/'native/src',dirs_exist_ok=True)
inventory=json.loads((V/'source_inventory.json').read_text())
actual={str(p.relative_to(R/'native')):sha(p) for p in (R/'native/src').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert actual==inventory
(R/'native/source_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
cmd=['docker','run','--rm','--pull=never','--name','v290-build'+tag,'--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','-v',str(R/'native')+':/work:rw','-v',str(R/'migration')+':/source:ro','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','/source/build_native.sh']
t=time.monotonic()
with (R/f'evidence/build{tag}.log').open('x') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
(R/f'evidence/build{tag}_closed.json').write_text(json.dumps(dict(passed=code==0,returncode=code,wall_s=time.monotonic()-t,source_files=len(inventory),source_inventory_sha256=sha(V/'source_inventory.json'),command=cmd,log_sha256=sha(R/f'evidence/build{tag}.log')),indent=2)+'\n')
raise SystemExit(code)

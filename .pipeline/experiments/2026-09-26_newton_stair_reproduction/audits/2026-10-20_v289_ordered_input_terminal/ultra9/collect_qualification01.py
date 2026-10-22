from pathlib import Path
import hashlib,json,shutil
R=Path('/home/ubuntu/sun/vla_v289_20261020')
OUT=R/'qualification_return01';OUT.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[]
for p in (R/'native/build').glob('*/test_results/*/*.xml'):files.append(p)
for p in (R/'native/regressions').iterdir():
    if p.is_file() and p.suffix in ('.xml','.log','.txt'):files.append(p)
files.append(R/'migration/native_manifest01.json')
for p in files:
    dest=OUT/p.relative_to(R);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
manifest={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Compact qualification files',len(manifest))

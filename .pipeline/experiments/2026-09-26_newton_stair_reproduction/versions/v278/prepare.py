"""Compose the verified frozen v272 parent; never mutate its execution copy."""
from pathlib import Path
import hashlib,json,shutil,os
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
PARENT=BASE/'source_surface_precompute_v272/native';WORK=BASE/'source_free_index_v278/native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent=json.loads((HERE.parent/'v272/results/source_inventory.json').read_text())
for rel,h in parent.items():assert sha(PARENT/rel)==h,rel
owned={str(p.relative_to(HERE)):sha(p) for p in (HERE/'src').rglob('*') if p.is_file()}
for rel,h in parent.items():
 if rel in owned:continue
 q=WORK/rel
 if not q.exists() or sha(q)!=h:
  q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PARENT/rel,q)
owned={str(p.relative_to(HERE)):sha(p) for p in (HERE/'src').rglob('*') if p.is_file()}
for rel in owned:
 q=WORK/rel
 if not q.exists() or sha(q)!=owned[rel]:
  q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/rel,q);q.touch()
actual={str(p.relative_to(WORK)):sha(p) for p in (WORK/'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert actual==dict(parent,**owned)
(WORK/'source_inventory.json').write_text(json.dumps(actual,indent=2)+'\n')
if not (WORK/'fixtures').exists():shutil.copytree(PARENT/'fixtures',WORK/'fixtures',copy_function=os.link)
# Private copied build/install caches; never hardlink mutable outputs to parent.
for name in ('build','install'):
 if not (WORK/name).exists():shutil.copytree(PARENT/name,WORK/name,symlinks=True)
print(json.dumps(dict(work=str(WORK),source_files=len(actual),owned=len(owned))))

"""Compose the verified frozen v247 parent; never mutate its execution copy."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
PARENT=BASE/'generic_mechanisms_v250/native';WORK=BASE/'generic_mechanisms_v251/native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent=json.loads((HERE.parent/'v250/results/source_inventory.json').read_text())
for rel,h in parent.items():assert sha(PARENT/rel)==h,rel
for rel,h in parent.items():
 q=WORK/rel
 if not q.exists() or sha(q)!=h:
  q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PARENT/rel,q)
owned={str(p.relative_to(HERE)):sha(p) for p in (HERE/'src').rglob('*') if p.is_file()}
for rel in owned:
 q=WORK/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,q)
actual={str(p.relative_to(WORK)):sha(p) for p in (WORK/'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert actual==dict(parent,**owned)
(WORK/'source_inventory.json').write_text(json.dumps(actual,indent=2)+'\n')
if not (WORK/'fixtures').exists():shutil.copytree(PARENT/'fixtures',WORK/'fixtures')
print(json.dumps(dict(work=str(WORK),source_files=len(actual),owned=len(owned))))

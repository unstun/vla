"""Compose v247 locally owned overlay onto the SHA-verified v240 execution copy."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
PARENT=BASE/'cooperative_search_v240';WORK=BASE/'physical_traversability_v247/native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inventory=json.loads((HERE.parent/'v240/results/source_inventory.json').read_text())
for rel,h in inventory.items():assert sha(PARENT/rel)==h,rel
if not (WORK/'src').exists():shutil.copytree(PARENT/'src',WORK/'src')
owned={str(p.relative_to(HERE)):sha(p) for p in (HERE/'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
for rel in owned:
 p=WORK/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,p)
actual={str(p.relative_to(WORK)):sha(p) for p in (WORK/'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert actual==dict(inventory,**owned)
(WORK/'source_inventory.json').write_text(json.dumps(actual,indent=2)+'\n')
(WORK/'composition.json').write_text(json.dumps(dict(parent=str(PARENT),owned=owned,inventory=actual),indent=2)+'\n')
print(json.dumps(dict(work=str(WORK),source_files=len(actual),owned=len(owned))))

if not (WORK/'fixtures').exists():shutil.copytree(BASE/'callback_failure_v232/fixtures',WORK/'fixtures')

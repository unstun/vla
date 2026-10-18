"""Private execution overlay; verifies every frozen parent source before copying."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
TASK=Path('/data/sun/vla_mppi_20261009')
PARENT=TASK/'callback_failure_v232'
WORK=TASK/'terminal_approach_v238'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inventory=json.loads((HERE.parent/'v232/results/source_inventory.json').read_text())
for rel,expected in inventory.items():assert sha(PARENT/rel)==expected,rel
if not (WORK/'src').exists():shutil.copytree(PARENT/'src',WORK/'src')
owned={str(p.relative_to(HERE)):sha(p) for p in (HERE/'src').rglob('*') if p.is_file()}
for rel in owned:
    target=WORK/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,target)
actual={str(p.relative_to(WORK)):sha(p) for p in (WORK/'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert actual==dict(inventory,**owned)
(WORK/'source_inventory.json').write_text(json.dumps(actual,indent=2)+'\n')
(WORK/'composition.json').write_text(json.dumps(dict(parent=str(PARENT),parent_inventory_sha256=sha(HERE.parent/'v232/results/source_inventory.json'),owned=owned,inventory=actual),indent=2)+'\n')
print(json.dumps(dict(files=len(actual),owned=len(owned))))

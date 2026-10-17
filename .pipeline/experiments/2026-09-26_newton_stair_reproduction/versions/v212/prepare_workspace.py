"""Compose a new execution copy from verified v206 sources plus this overlay."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
PARENT = TASK / 'command_continuity_v206_20261015'
WORK = TASK / 'event_replan_v212'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
identity = json.loads((HERE / 'source_identity.json').read_text())
for rel, expected in identity['files'].items():
    assert sha(HERE / rel) == expected, rel
old = json.loads((PARENT / 'source_inventory.json').read_text())
for rel, expected in old.items():
    assert sha(PARENT / rel) == expected, rel
WORK.mkdir(exist_ok=False)
shutil.copytree(PARENT / 'src', WORK / 'src', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copytree(PARENT / 'fixtures', WORK / 'fixtures')
for path in (HERE / 'src').rglob('*'):
    if path.is_file():
        target = WORK / path.relative_to(HERE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
inventory = {str(p.relative_to(WORK)): sha(p) for p in (WORK / 'src').rglob('*') if p.is_file()}
changed = {rel for rel, value in inventory.items() if old.get(rel) != value}
assert changed == {str(p.relative_to(HERE)) for p in (HERE / 'src').rglob('*') if p.is_file()}
(WORK / 'source_inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
(WORK / 'composition.json').write_text(json.dumps({'parent':str(PARENT), 'changed_files':sorted(changed),
    'unchanged_files':len(inventory)-len(changed), 'parent_inventory_sha256':sha(PARENT/'source_inventory.json')},indent=2)+'\n')
print((WORK / 'composition.json').read_text())

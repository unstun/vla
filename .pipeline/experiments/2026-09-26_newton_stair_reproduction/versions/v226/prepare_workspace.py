"""Compose a private v226 build from verified v223 and the local overlay."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
PARENT = TASK / 'environment_lookup_v225'
WORK = TASK / 'environment_interpolation_v226'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

identity = json.loads((HERE / 'source_identity.json').read_text())
for rel, expected in identity['files'].items():
    assert sha(HERE / rel) == expected, rel
parent = json.loads((PARENT / 'source_inventory.json').read_text())
for rel, expected in parent.items():
    assert sha(PARENT / rel) == expected, rel
def source_files(folder):
    return (p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')

owned = {str(p.relative_to(HERE)): sha(p) for p in source_files(HERE / 'src')}
if not WORK.exists():
    WORK.mkdir()
    shutil.copytree(PARENT / 'src', WORK / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(PARENT / 'fixtures', WORK / 'fixtures')
else:
    previous = json.loads((WORK / 'composition.json').read_text())
    assert previous['parent'] == str(PARENT)
    revision = hashlib.sha256(json.dumps(previous['inventory'], sort_keys=True).encode()).hexdigest()
    saved = WORK / 'evidence/source_revisions' / revision
    for rel, expected in previous['inventory'].items():
        actual = sha(WORK / rel)
        # Resume a copy interrupted before its new inventory was committed.
        # The exact old bytes must already be preserved and the current bytes
        # must match this locally authorized overlay; arbitrary drift is refused.
        if actual != expected:
            assert rel in previous['owned'] and actual == owned.get(rel), rel
            assert (saved / rel).is_file() and sha(saved / rel) == expected, rel
    if not saved.exists():
        for rel in previous['owned']:
            path = saved / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(WORK / rel, path)
for rel in owned:
    target = WORK / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or sha(target) != owned[rel]:
        shutil.copyfile(HERE / rel, target)
inventory = {str(p.relative_to(WORK)): sha(p) for p in source_files(WORK / 'src')}
assert set(inventory) == set(parent) | set(owned)
for rel, expected in inventory.items():
    assert expected == owned.get(rel, parent.get(rel)), rel
(WORK / 'source_inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
(WORK / 'composition.json').write_text(json.dumps({
    'parent': str(PARENT), 'owned': sorted(owned), 'inventory': inventory,
    'source_identity_sha256': sha(HERE / 'source_identity.json'),
}, indent=2) + '\n')
print(json.dumps({'work': str(WORK), 'owned': len(owned), 'total': len(inventory)}))

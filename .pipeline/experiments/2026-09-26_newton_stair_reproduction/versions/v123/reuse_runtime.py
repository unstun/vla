"""Copy only hash-identical existing remote inputs into this owned execution root."""
from pathlib import Path
import hashlib
import json
import shutil

TASK = Path('/data/sun/vla_mppi_20261009')
manifest = json.loads((TASK/'results/runtime_sync_manifest.json').read_text())
source = Path(manifest['reuse_root'])
destination = TASK/'repo'
reused, missing = [], []
for name, expected in manifest['files'].items():
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError(name)
    old, target = source/relative, destination/relative
    def matches(path):
        return (path.is_file() and path.stat().st_size == expected['bytes']
                and hashlib.sha256(path.read_bytes()).hexdigest() == expected['sha256'])
    if matches(target):
        continue
    if matches(old):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old, target)
        assert matches(target), name
        reused.append(name)
    else:
        missing.append(name)
(TASK/'results/runtime_missing.txt').write_text('\n'.join(missing)+'\n')
(TASK/'results/runtime_reuse.json').write_text(json.dumps({
    'reused_files': len(reused), 'missing_files': len(missing),
    'missing_bytes': sum(manifest['files'][name]['bytes'] for name in missing),
    'reused_paths': reused}, indent=2)+'\n')
print(json.dumps({'reused': len(reused), 'missing': len(missing),
                 'missing_bytes': sum(manifest['files'][name]['bytes'] for name in missing)}))

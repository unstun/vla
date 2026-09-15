"""Record exactly the task scripts and recorded-image requests sent to the GPU."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
files=[]
for directory in ['scripts','fixtures']:
    for path in sorted((root/directory).rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            files.append({'path':path.relative_to(root).as_posix(),
                          'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(root/'setup/package_manifest.json').write_text(json.dumps({'files':files},indent=2))
print(f'Package contains {len(files)} files')

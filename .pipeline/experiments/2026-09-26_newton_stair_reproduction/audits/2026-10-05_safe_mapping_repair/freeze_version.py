"""Freeze new owned bytes, referring to exact unchanged inherited snapshots."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--version', required=True)
parser.add_argument('--parent', required=True)
parser.add_argument('--native', type=Path)
parser.add_argument('--quality', type=Path, required=True)
args = parser.parse_args()
folder = BASE / 'versions' / args.version
assert not (folder / 'manifest.json').exists()
quality = json.loads(args.quality.read_text())
assert quality['passed']
parent_path = BASE / 'versions' / args.parent / 'manifest.json'
parent = json.loads(parent_path.read_text())
sources = dict(parent['source_files'])
locations = dict(parent['snapshot_locations'])
by_hash = {}
for path, digest in sources.items():
    assert sha(ROOT / path) == digest, path
    assert sha(ROOT / locations[path]) == digest, locations[path]
    by_hash[digest] = locations[path]
owned = [p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts
         and 'source' not in p.relative_to(folder).parts
         and (p.suffix in ('.py', '.cpp', '.h', '.inc', '.sh', '.txt', '.yaml', '.md')
              or p.name in ('navigation_contract.json', 'corner_scenario.json', 'physical_floor_input.json'))
         and p.name not in ('RESULTS.md',)]
native = parent['native_source_sha256']
if args.native:
    args.native = args.native.resolve()
    native = {str(p.relative_to(args.native)): sha(p) for p in (args.native / 'src').rglob('*') if p.is_file()}
    (args.native / 'source_sha256.json').write_text(json.dumps(native, indent=2) + '\n')
    owned += [args.native / path for path in native] + [args.native / 'source_sha256.json']
for path in owned:
    relative = str(path.relative_to(ROOT))
    digest = sha(path)
    sources[relative] = digest
    if digest in by_hash:
        locations[relative] = by_hash[digest]
    else:
        copy = folder / 'source' / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, copy)
        locations[relative] = str(copy.relative_to(ROOT))
        by_hash[digest] = locations[relative]
manifest = {'version': args.version, 'parent': args.parent, 'parent_manifest_sha256': sha(parent_path),
            'status': 'frozen_component_checked_not_physical_accepted', 'source_files': sources,
            'snapshot_locations': locations, 'native_source_sha256': native,
            'quality_sha256': sha(args.quality), 'navigation_validated': False,
            'full_scene_30hz_validated': False, 'v49_mechanics': False}
(folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'version': args.version, 'source_files': len(sources), 'manifest_sha256': sha(folder / 'manifest.json')}))

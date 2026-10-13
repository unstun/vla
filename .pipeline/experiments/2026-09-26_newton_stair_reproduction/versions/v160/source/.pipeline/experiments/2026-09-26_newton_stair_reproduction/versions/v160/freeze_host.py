"""Freeze the Mac host port separately from its unchanged native v147 parent."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    manifest = json.loads((HERE/'manifest.json').read_text())
    for name, expected in manifest['source_files'].items():
        if sha(ROOT/name) != expected or sha(ROOT/manifest['snapshot_locations'][name]) != expected:
            raise ValueError('Source/snapshot changed: '+name)
    if sha(HERE/'quality.json') != manifest['quality_sha256']:
        raise ValueError('Quality identity changed')
    if sha(HERE.parent/'v159/manifest.json') != manifest['parent_manifest_sha256']:
        raise ValueError('Parent identity changed')
    inputs = json.loads((HERE/'runtime_sync_manifest.json').read_text())
    for name, expected in inputs['files'].items():
        if sha(ROOT/name) != expected['sha256']:
            raise ValueError('Runtime input changed: '+name)
    print(json.dumps({'passed': True, 'source_pairs': len(manifest['source_files']),
                      'runtime_inputs': len(inputs['files']), 'platform': manifest['platform']}))


def freeze():
    if (HERE/'manifest.json').exists():
        raise ValueError('Never overwrite a frozen version')
    previous = json.loads((HERE.parent/'v159/manifest.json').read_text())
    files, locations = dict(previous['source_files']), dict(previous['snapshot_locations'])
    selected = [p for p in HERE.iterdir() if p.is_file() and
                (p.suffix in ('.py', '.sh', '.yaml', '.cpp') or p.name in (
                    'CMakeLists.txt', 'Dockerfile', 'Dockerfile.dependencies', 'docker', 'lsof', 'corner_scenario.json',
                    'navigation_contract.json', 'physical_floor_input.json', 'runtime_sync_manifest.json',
                    'native_sources.json', 'source_audit.json', 'support_coverage_input.json', 'global_map_input.json', 'full_route_input.json', 'PLAN.md', 'query_mask.cpp'))]
    selected.append(HERE.parent / 'v156/probe.cpp')
    selected.extend(p for p in (HERE/'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    selected.extend(p for p in (HERE/'contract').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    # Capture inherited runtime code as well as the explicit input hash manifest.
    for name in json.loads((HERE/'runtime_sync_manifest.json').read_text())['files']:
        path = ROOT/name
        if path.suffix in ('.py', '.cpp', '.h', '.hpp', '.yaml', '.sh'):
            selected.append(path)
    for path in sorted(set(selected)):
        name = str(path.relative_to(ROOT))
        digest = sha(path)
        if files.get(name) == digest:
            continue
        snapshot = HERE/'source'/name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, snapshot)
        files[name], locations[name] = digest, str(snapshot.relative_to(ROOT))
    manifest = {'version': 'v160', 'parent': 'v159',
                'parent_manifest_sha256': sha(HERE.parent/'v159/manifest.json'),
                'status': 'frozen_goal_capture_margin_candidate',
                'platform': 'Mac ARM64 / Ubuntu 20.04 ROS 2 Foxy ARM64 container / CPU Newton',
                'native_variants': {'candidate': 'v160'},
                'source_files': files, 'snapshot_locations': locations,
                'quality_sha256': sha(HERE/'quality.json')}
    (HERE/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    verify()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('freeze', 'verify'))
    args = parser.parse_args()
    (freeze if args.action == 'freeze' else verify)()

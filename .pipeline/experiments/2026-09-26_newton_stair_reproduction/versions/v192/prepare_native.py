"""Materialize v191 Option B over the byte-identical, archived Mac v176 source tree."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    parent = args.task_root / 'recovery_v176'
    target = args.task_root / 'recovery_v191'
    prior = json.loads((parent / 'source_identity.json').read_text())
    origins = json.loads((HERE / 'native_sources.json').read_text())
    assert prior['version'] == 'v176'
    assert prior['files'] == origins['parent_files']
    restored = {}
    inherited = {name: digest for name, digest in prior['files'].items()
                 if name.startswith('src/') and name not in origins['deleted_files']
                 and name not in origins['changed_files']}
    for name, digest in inherited.items():
        path = parent / name
        if not path.exists():
            candidates = sorted(args.task_root.glob('recovery_*/' + name))
            path = next((p for p in candidates if p.is_file() and sha(p) == digest), None)
            if path is None:
                raise ValueError('Missing archived source: ' + name)
            restored[name] = str(path.relative_to(args.task_root))
        assert sha(path) == digest, name
    target.mkdir(exist_ok=False)
    files = dict(inherited)
    for name in list(files):
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        origin = args.task_root / restored[name] if name in restored else parent / name
        shutil.copyfile(origin, target / name)
    for name in origins['changed_files']:
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / name, target / name)
        if name.endswith('scripts/mission_bridge'):
            (target / name).chmod(0o755)
        files[name] = sha(target / name)
    assert files == origins['expected_files']
    identity = dict(version='v191', native_parent='v176', mac_binary_underlay='v176',
                    semantic_baseline='v191_option_b_direct_nav2_scan', inventory_scope='src/',
                    parent_source_identity_sha256=sha(parent / 'source_identity.json'),
                    restored_inherited_sources=restored,
                    deleted=origins.get('deleted_files', []),
                    changes=origins['changed_files'], files=files)
    (target / 'source_identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    print(json.dumps({'files': len(files), 'deleted': len(origins.get('deleted_files', [])),
                      'changed': len(origins['changed_files'])}))


if __name__ == '__main__':
    main()

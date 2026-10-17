"""Materialize v189 over the byte-identical, archived Mac v176 source tree."""
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
    target = args.task_root / 'recovery_v189'
    prior = json.loads((parent / 'source_identity.json').read_text())
    origins = json.loads((HERE / 'native_sources.json').read_text())
    assert prior['version'] == 'v176'
    assert prior['files'] == origins['parent_files']
    restored = {}
    for name, digest in prior['files'].items():
        path = parent / name
        if not path.exists():
            # The compact v176 archive omits inherited licenses, third-party
            # source and old identities. Recover only byte-identical members
            # already present in the verified earlier Mac archives.
            candidates = sorted(args.task_root.glob('recovery_*/' + name))
            path = next((p for p in candidates if p.is_file() and sha(p) == digest), None)
            if path is None:
                raise ValueError('Missing archived source: ' + name)
            restored[name] = str(path.relative_to(args.task_root))
        assert sha(path) == digest, name
    target.mkdir(exist_ok=False)
    files = dict(prior['files'])
    for name in files:
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        origin = args.task_root / restored[name] if name in restored else parent / name
        shutil.copyfile(origin, target / name)
    for name in origins['changed_files']:
        shutil.copyfile(HERE / name, target / name)
        files[name] = sha(target / name)
    assert files == origins['expected_files']
    identity = dict(version='v189', native_parent='v176', mac_binary_underlay='v176',
                    semantic_baseline='v177/v188',
                    parent_source_identity_sha256=sha(parent / 'source_identity.json'),
                    restored_inherited_sources=restored,
                    changes=origins['changed_files'], files=files)
    (target / 'source_identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    print(json.dumps({'files': len(files), 'changed': origins['changed_files']}))


if __name__ == '__main__':
    main()

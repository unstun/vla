"""Derive exactly one changed native header from the verified v147 export."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    root = args.task_root.resolve()
    parent = root / 'recovery_v147'
    target = root / 'recovery_v151'
    identity = json.loads((parent / 'source_identity.json').read_text())
    assert identity['version'] == 'v147'
    target.mkdir(exist_ok=False)
    for name, digest in identity['files'].items():
        assert sha(parent / name) == digest, name
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(parent / name, target / name)
    changed = 'src/bspline_opt/include/bspline_opt/full_trajectory_collision.h'
    assert sha(HERE / changed) != identity['files'][changed]
    shutil.copyfile(HERE / changed, target / changed)
    files = dict(identity['files'])
    files[changed] = sha(target / changed)
    output = {'version': 'v151', 'native_parent': 'v147',
              'parent_source_identity_sha256': sha(parent / 'source_identity.json'),
              'changes': [changed], 'files': files}
    (target / 'source_identity.json').write_text(json.dumps(output, indent=2) + '\n')
    assert [n for n, digest in files.items() if digest != identity['files'][n]] == [changed]
    print(json.dumps({'source_files': len(files), 'changed': [changed]}))


if __name__ == '__main__':
    main()

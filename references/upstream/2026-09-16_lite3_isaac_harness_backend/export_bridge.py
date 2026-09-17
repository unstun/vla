"""Export the selected committed bridge without modifying the sibling checkout."""

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
REPO = Path('/Users/sun/tongbu/study/phdproject/machine-dog-nav')
COMMIT = '848b4aecd01237805e0564c88d3ba09146fd2353'
PREFIX = 'integration/lite3_sim_bridge'


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])


def main():
    files = git('ls-tree', '-r', '--name-only', COMMIT, PREFIX).decode().splitlines()
    if not files:
        raise RuntimeError('Selected committed tree is empty')
    hashes = {}
    for relative in files:
        content = git('show', f'{COMMIT}:{relative}')
        target = ROOT / 'source' / 'machine-dog-nav' / relative
        if target.exists() and target.read_bytes() != content:
            raise RuntimeError(f'Refusing to overwrite changed reference: {relative}')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        hashes[relative] = hashlib.sha256(content).hexdigest()
    result = {'commit': COMMIT, 'tree': git('rev-parse', f'{COMMIT}^{{tree}}').decode().strip(),
              'source_repository': str(REPO), 'source_branch': 'codex/scan-foxy-isaac',
              'import_method': 'git show of committed blobs only',
              'working_tree_copied': False, 'file_count': len(hashes), 'sha256': hashes,
              'runtime_status': 'not_run'}
    (ROOT / 'acquisition.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'commit': COMMIT, 'file_count': len(hashes), 'working_tree_copied': False}))


if __name__ == '__main__':
    main()

"""Compare protected bytes against the pre-v192 inventory and one allowed edit."""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = Path('/private/tmp/vla_stop_audit_20261012')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def inventory(root):
    values = {}
    for path in sorted(root.rglob('*')):
        name = str(path.relative_to(root))
        if path.is_symlink():
            values[name] = {'symlink': os.readlink(path)}
        elif path.is_file():
            values[name] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    return values


def main():
    baseline_path = TASK / 'evidence/v192_protected_before.json'
    baseline = json.loads(baseline_path.read_text())
    original = TASK / 'evidence/v191_RESULTS_before_v192.md'
    text = original.read_text()
    marker = '\nThe v192 display package replays'
    assert marker in text
    allowed = (text[:text.index(marker)] + '\n').encode()
    rows = {}
    for root_name, before in baseline.items():
        root = Path(root_name)
        after = inventory(root)
        added, removed = sorted(after.keys() - before.keys()), sorted(before.keys() - after.keys())
        changed = sorted(n for n in before.keys() & after.keys() if before[n] != after[n])
        permitted = []
        if root == HERE.parent / 'v191':
            assert sha(original) == before['RESULTS.md']['sha256']
            if (root / 'RESULTS.md').read_bytes() == allowed and 'RESULTS.md' in changed:
                permitted = ['RESULTS.md']
        rows[root_name] = {'entries': len(after), 'added': added, 'removed': removed,
                           'changed': changed, 'authorized_changes': permitted,
                           'passed': not added and not removed and changed == permitted}
    parent_source = inventory(HERE.parent / 'v191/src')
    copied_source = inventory(HERE / 'src')
    result = {'passed': all(row['passed'] for row in rows.values()) and parent_source == copied_source,
              'baseline_sha256': sha(baseline_path),
              'comparison': 'Every regular file SHA-256/size and symlink target, including additions/removals',
              'native_source_unchanged': parent_source == copied_source,
              'native_source_files': len(parent_source), 'native_build_reused': True, 'paths': rows}
    (TASK / 'evidence/v192_protected_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

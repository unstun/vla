"""Verify all eight protected trees against Step 0, without exceptions."""
import hashlib
import json
import os
import stat
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = Path('/private/tmp/vla_stop_audit_20261012')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def inventory(root):
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Protected root is missing or replaced: ' + str(root))
    values = {}
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(parent) / name
            info = path.lstat()
            row = dict(mode=stat.S_IMODE(info.st_mode), mtime_ns=info.st_mtime_ns)
            if path.is_symlink(): row.update(kind='symlink', target=os.readlink(path))
            elif path.is_file():
                row.update(kind='file', size=info.st_size, sha256=sha(path))
                after = path.stat()
                if (after.st_size, after.st_mtime_ns) != (info.st_size, info.st_mtime_ns):
                    raise ValueError('Changed while hashing: ' + str(path))
            elif path.is_dir(): row.update(kind='directory')
            else: row.update(kind='special')
            values[str(path)] = row
    return values


def main():
    baseline_path = TASK / 'evidence/v196_protected_before.json'
    baseline = json.loads(baseline_path.read_text())
    assert baseline['schema'] == 'v196-protected-snapshot-v1'
    expected = {str(HERE.parent / ('v' + str(v))) for v in range(189, 196)}
    expected.update(str(TASK / name) for name in (
        'recovery_v176', 'recovery_v189', 'recovery_v191', 'recovery_v194',
        'v192_mac_full_attempt01', 'v194_mac_full_attempt01', 'video_v195'))
    assert set(baseline['roots']) == expected
    rows = {}
    for root_name in baseline['roots']:
        before = {n: row for n, row in baseline['entries'].items() if n.startswith(root_name + '/')}
        after = inventory(Path(root_name))
        added = sorted(after.keys() - before.keys())
        removed = sorted(before.keys() - after.keys())
        changed = sorted(n for n in before.keys() & after.keys() if before[n] != after[n])
        rows[root_name] = dict(entries=len(after), added=added, removed=removed,
                               changed=changed, passed=not added and not removed and not changed)
    origins = json.loads((HERE / 'native_sources.json').read_text())
    actual = {'src/' + str(p.relative_to(TASK / 'recovery_v196/src')): sha(p)
              for p in (TASK / 'recovery_v196/src').rglob('*') if p.is_file()}
    local = {str(p.relative_to(HERE)): sha(p) for p in (HERE / 'src').rglob('*') if p.is_file()}
    matched = actual == origins['expected_files'] and all(actual.get(n) == h for n, h in local.items())
    result = dict(passed=all(row['passed'] for row in rows.values()) and matched,
                  baseline_sha256=sha(baseline_path), paths=rows,
                  comparison='All recursive SHA-256/size/mtime/mode, symlinks and entries; no exceptions',
                  native_source_matches_inventory=matched, native_source_files=len(actual),
                  native_build_reused=False)
    (TASK / 'evidence/v196_protected_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if not result['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()

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
    def walk(directory):
        for entry in sorted(os.scandir(directory), key=lambda e: e.name):
            path = Path(entry.path)
            name = path.relative_to(root).as_posix()
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                values[name] = dict(type='symlink', target=os.readlink(path), bytes=info.st_size)
            elif stat.S_ISDIR(info.st_mode):
                values[name] = dict(type='directory')
                walk(path)
            elif stat.S_ISREG(info.st_mode):
                values[name] = dict(type='file', sha256=sha(path), bytes=info.st_size)
                after = path.stat()
                if (after.st_size, after.st_mtime_ns) != (info.st_size, info.st_mtime_ns):
                    raise ValueError('File changed while hashing: ' + str(path))
            else:
                values[name] = dict(type='special', mode=stat.S_IFMT(info.st_mode), bytes=info.st_size)
    walk(root)
    return values


def main():
    baseline_path = TASK / 'evidence/v194_protected_before.json'
    baseline = json.loads(baseline_path.read_text())
    assert baseline['schema'] == 'v194-protected-inventory-v1'
    expected_roots = {str(HERE.parent / ('v' + str(v))) for v in (189, 190, 191, 192, 193)}
    expected_roots.update(str(TASK / ('recovery_v' + str(v))) for v in (176, 189, 191))
    assert set(baseline['roots']) == expected_roots
    rows = {}
    for root_name, before in baseline['roots'].items():
        after = inventory(Path(root_name))
        added, removed = sorted(after.keys() - before.keys()), sorted(before.keys() - after.keys())
        changed = sorted(n for n in before.keys() & after.keys() if before[n] != after[n])
        rows[root_name] = dict(entries=len(after), added=added, removed=removed,
                               changed=changed, passed=not added and not removed and not changed)
    origins = json.loads((HERE / 'native_sources.json').read_text())
    actual = {'src/' + str(p.relative_to(TASK / 'recovery_v194/src')): sha(p)
              for p in (TASK / 'recovery_v194/src').rglob('*') if p.is_file()}
    local = {str(p.relative_to(HERE)): sha(p) for p in (HERE / 'src').rglob('*') if p.is_file()}
    matched = actual == origins['expected_files'] and all(actual.get(n) == h for n, h in local.items())
    result = dict(passed=all(row['passed'] for row in rows.values()) and matched,
                  baseline_sha256=sha(baseline_path), paths=rows,
                  comparison='Every recursive file SHA-256/bytes, symlink target/bytes, directory and special entry; no exceptions',
                  native_source_matches_inventory=matched, native_source_files=len(actual),
                  native_build_reused=False)
    (TASK / 'evidence/v194_protected_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

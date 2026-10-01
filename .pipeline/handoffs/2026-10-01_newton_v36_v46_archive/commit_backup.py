#!/usr/bin/env python3
"""Commit the isolated archive and reconcile only its paths into the real index."""
from pathlib import Path
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[3]
H = Path(__file__).resolve().parent

def main():
    os.chdir(ROOT)
    plan = json.loads((H / 'backup_plan.json').read_text())
    env = dict(os.environ, GIT_INDEX_FILE=plan['alternate_index'])
    def git(*args, data=None, isolated=False):
        return subprocess.check_output(['git', *args], input=data, cwd=ROOT,
                                       env=env if isolated else None)
    assert git('rev-parse', 'HEAD').decode().strip() == plan['head_before'], 'HEAD changed'
    expected = json.loads((H / 'original_staged_entries.json').read_text())
    excluded = set(json.loads((H / 'preflight.json').read_text())['staged_paths'])
    def excluded_entries():
        return [e.decode() for e in git('ls-files', '--stage', '-z').split(b'\0')
                if e and e.split(b'\t', 1)[1].decode() in excluded]
    assert excluded_entries() == expected, 'Preexisting staged files changed'
    review = json.loads((H / 'staging_review.json').read_text())
    assert review['scope_audit'] == 'PASS' and review['archive_metadata_diff_check'] == 'PASS'
    # This receipt script is the only addition since the staged scope review.
    own_script = str(Path(__file__).relative_to(ROOT))
    git('add', '--', own_script, isolated=True)
    names = {s.decode() for s in git('diff', '--cached', '--name-only', '-z', isolated=True).split(b'\0') if s}
    scope = {s.decode() for s in (Path(plan['temp_dir']) / 'reconcile_paths.nul').read_bytes().split(b'\0') if s}
    scope.add(own_script)
    assert names <= scope and not names.intersection(excluded)
    assert not any(n.startswith('.trellis/') or n.startswith('.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/') for n in names)
    # Quiet output avoids listing tens of thousands of immutable snapshot files.
    git('-c', 'gc.auto=0', 'commit', '--quiet', '-m',
        '备份：Newton v36-v46 实测节拍、视频与归档', isolated=True)
    head = git('rev-parse', 'HEAD').decode().strip()
    assert git('rev-parse', head + '^').decode().strip() == plan['head_before']
    rows = git('ls-files', '--stage', '-z', isolated=True).split(b'\0')
    owned_rows = [r for r in rows if r and r.split(b'\t', 1)[1].decode() in scope]
    assert len(owned_rows) == len(scope), 'Some owned index paths are missing'
    # Direct index entries avoid pathspec traversal and preserve all other entries.
    git('update-index', '-z', '--index-info', data=b'\0'.join(owned_rows) + b'\0')
    assert excluded_entries() == expected, 'Existing staged blobs were not preserved'
    remaining = git('diff', '--cached', '--name-only', '-z').split(b'\0')
    remaining = [s.decode() for s in remaining if s]
    assert not set(remaining).intersection(scope), 'Archive still staged after commit'
    assert set(remaining) == excluded, 'Unexpected remaining staged paths'
    changed = git('diff-tree', '--no-commit-id', '--name-only', '-r', '-z', head).split(b'\0')
    changed = {s.decode() for s in changed if s}
    assert changed == names
    print(json.dumps({'commit': head, 'parent': plan['head_before'],
                      'committed_files': len(changed), 'backup': 'local_only',
                      'existing_staged_files_preserved': remaining,
                      'scope_verified_after_commit': True}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

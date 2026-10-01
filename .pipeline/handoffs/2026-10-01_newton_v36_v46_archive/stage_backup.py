#!/usr/bin/env python3
"""Stage the reviewed archive in a separate index, keeping unrelated edits out."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[3]
H = Path(__file__).resolve().parent

def main():
    os.chdir(ROOT)
    plan = json.loads((H / 'backup_plan.json').read_text())
    env = dict(os.environ, GIT_INDEX_FILE=plan['alternate_index'], GIT_LITERAL_PATHSPECS='1')
    def git(*args, data=None):
        return subprocess.check_output(['git', *args], input=data, env=env, cwd=ROOT)
    assert git('rev-parse', 'HEAD').decode().strip() == plan['head_before'], 'Concurrent HEAD update'
    original_index = Path('.git/index').read_bytes()
    git('read-tree', plan['head_before'])
    shared = json.loads((H / 'backup_scope.json').read_text())['shared_delta_only']
    paths = set(s.decode() for s in Path(plan['explicit_paths']).read_bytes().split(b'\0') if s)
    paths.update(str(f.relative_to(ROOT)) for f in H.rglob('*') if f.is_file())
    paths.difference_update(shared)
    excluded = json.loads((H / 'preflight.json').read_text())['staged_paths']
    assert not paths.intersection(excluded)
    assert not any(p.startswith('.trellis/') or p.startswith('.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/') for p in paths)
    pathfile = Path(plan['temp_dir']) / 'archive_exact_paths.nul'
    pathfile.write_bytes(b'\0'.join(p.encode() for p in sorted(paths)) + b'\0')
    # Direct per-file indexing avoids quadratic matching of 67,000 pathspecs.
    git('update-index', '--add', '-z', '--stdin', data=pathfile.read_bytes())
    content = {'.gitignore': git('show', plan['head_before'] + ':.gitignore').decode()
               + (H / 'gitignore_owned_block.txt').read_text()}
    for name, header, snippet in [
        ('.pipeline/literature/index.md', '# Literature And Upstream Index\n', 'literature_new_entry.md'),
        ('.pipeline/experiments/README.md', '# Experiment Records\n', 'experiments_README_new_entry.md')]:
        before = git('show', plan['head_before'] + ':' + name).decode()
        assert before.count(header) == 1
        content[name] = before.replace(header, header + '\n' + (H / 'pipeline_drafts' / snippet).read_text(), 1)
    name = 'bigmemory/冷区/.degradation-state.json'
    before = json.loads(git('show', plan['head_before'] + ':' + name))
    after = json.loads(Path(name).read_text())
    for field in ('last_run', 'last_check'):
        if field in after:
            before[field] = after[field]
    content[name] = json.dumps(before, ensure_ascii=False, indent=2) + '\n'
    receipt = {}
    for name, text in content.items():
        blob = git('hash-object', '-w', '--stdin', data=text.encode()).decode().strip()
        git('update-index', '--add', '--cacheinfo', '100644,' + blob + ',' + name)
        receipt[name] = {'staged_blob': blob, 'staged_content_sha256': hashlib.sha256(text.encode()).hexdigest(),
                         'working_tree_sha256': hashlib.sha256(Path(name).read_bytes()).hexdigest(),
                         'preserved_prior_dirty_hunks': True}
    assert Path('.git/index').read_bytes() == original_index, 'Real index changed during isolated staging'
    changed = git('diff', '--cached', '--name-only', '-z').split(b'\0')
    changed = {p.decode() for p in changed if p}
    assert changed <= paths | set(shared)
    assert not changed.intersection(excluded)
    stats = git('diff', '--cached', '--numstat', '-z')
    rows = [r.split(b'\t', 2) for r in stats.split(b'\0') if r]
    format_paths = ['.gitignore', '.pipeline/literature/index.md', '.pipeline/experiments/README.md',
                    '.pipeline/experiments/2026-10-01_newton_nav2_timing_archive.md',
                    '.pipeline/survey/2026-10-01_scan_planner_frequency.md',
                    str(H.relative_to(ROOT)), 'bigmemory/热区',
                    *['bigmemory/冷区/' + c + '/2026-10-01.md' for c in
                      ('改动记录', '踩坑记录', '调研记录', '心路历程')]]
    git('diff', '--cached', '--check', '--', *format_paths)
    counts = Counter()
    for name in changed:
        counts['files'] += 1
        if '/versions/v' in name:
            group = name.split('/versions/')[1].split('/')[0]
        elif '/runs/' in name:
            group = name.split('/runs/')[1].split('/')[0]
        elif '/runtime/' in name:
            group = name.split('/runtime/')[1].split('/')[0]
        elif name.startswith('bigmemory/'):
            group = 'bigmemory'
        else:
            group = 'indexes_surveys_audits_and_archive'
        counts[group] += 1
    result = {'staged_file_counts': dict(counts), 'numstat_rows': len(rows),
              'shared_delta_receipt': receipt, 'real_index_unchanged': True,
              'original_two_staged_paths_excluded': True, 'archive_metadata_diff_check': 'PASS',
              'frozen_snapshot_whitespace': 'Unchanged upstream and historical snapshot whitespace is retained; broad added-file diff --check is not an archive acceptance gate.',
              'scope_audit': 'PASS', 'head_before': plan['head_before']}
    (H / 'staging_review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    git('add', '--', str((H / 'staging_review.json').relative_to(ROOT)))
    final_paths = paths | set(shared) | {str((H / 'staging_review.json').relative_to(ROOT))}
    reconcile = Path(plan['temp_dir']) / 'reconcile_paths.nul'
    reconcile.write_bytes(b'\0'.join(p.encode() for p in sorted(final_paths)) + b'\0')
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

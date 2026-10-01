#!/usr/bin/env python3
"""Prepare an explicit archive scope without changing Git's real index."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
H = Path(__file__).resolve().parent
B = Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction')
VERSIONS = [B / 'versions' / f'v{i}' for i in range(36, 47)]
NATIVE = [B / 'runtime' / n for n in (
    'scan67_nav2_contract_v36', 'scan68_raw_contributor_cache_v39',
    'scan69_shared_attempt_cache_v44')]
AUDITS = [B / 'audits' / ('2026-09-30_' + n) for n in (
    'gpu_device_compare', 'native_local_profile', 'realtime_recording',
    'realtime_budget', 'local_30hz_opportunities')]
RUNS = [B / 'runs' / n for n in (
    'v42_realtime_preview01', 'v45_realtime_preview01',
    'v42_inspection_render01', 'v42_inspection_render02',
    'v42_inspection_render03', 'v42_inspection_view01',
    'v45_wall_render01', 'v45_wall_view01')]
OUTPUT = Path('output/2026-09-30_lite3_realtime')
EXTRA = [
    Path('.pipeline/survey/2026-09-30_continuous_local_planning_upstream_survey.md'),
    Path('.pipeline/survey/2026-09-30_realtime_clock_upstream_survey.md'),
    Path('.pipeline/survey/2026-10-01_scan_planner_frequency.md'),
    Path('.pipeline/experiments/2026-10-01_newton_nav2_timing_archive.md'),
    B / 'versions/README.md', B / 'versions/current.json',
    *[Path('bigmemory/冷区') / c / '2026-10-01.md' for c in
      ('改动记录', '踩坑记录', '调研记录', '心路历程')],
    *[Path('bigmemory/热区') / (n + '.md') for n in
      ('状态简报', '未关闭决策', '近期改动')],
]
SHARED = ['.gitignore', '.pipeline/literature/index.md',
          '.pipeline/experiments/README.md', 'bigmemory/冷区/.degradation-state.json']

def files_at(p):
    return [p] if p.is_file() else [f for f in p.rglob('*') if f.is_file() or f.is_symlink()]

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def main():
    os.chdir(ROOT)
    preflight = json.loads((H / 'preflight.json').read_text())
    assert git('rev-parse', 'HEAD').decode().strip() == preflight['head'], 'HEAD changed'
    staged = git('ls-files', '--stage', '-z')
    original = [e for e in staged.split(b'\0') if e and
                e.split(b'\t', 1)[1].decode() in preflight['staged_paths']]
    assert len(original) == 2
    (H / 'original_staged_entries.json').write_text(json.dumps(
        [e.decode() for e in original], ensure_ascii=False, indent=2) + '\n')

    local_dirs = [n / 'install' for n in NATIVE]
    for run in RUNS:
        for name in ('frames', 'clouds', 'inputs', 'artifacts'):
            p = run / name
            if p.exists():
                local_dirs.append(p)
    owned = set()
    for root in VERSIONS + NATIVE + AUDITS + RUNS + [OUTPUT] + EXTRA:
        assert root.exists(), root
        owned.update(str(p) for p in files_at(root))
    local = {}
    sha_cache = {}
    for name in sorted(owned):
        p = Path(name)
        n = p.stat().st_size
        in_local_dir = next((d for d in local_dirs if p == d or d in p.parents), None)
        raw_large = n > 5_000_000 and any(run in p.parents for run in RUNS)
        generated = '__pycache__' in p.parts
        if not (in_local_dir or raw_large or generated):
            continue
        reason = ('Rebuildable installed native products' if any(nat in p.parents for nat in NATIVE)
                  else 'Regenerable display frames' if 'frames' in p.parts
                  else 'Generated Python bytecode' if generated
                  else 'Original or derived raw run records; preserve exact local bytes')
        st = p.stat(); key = (st.st_dev, st.st_ino, n, st.st_mtime_ns)
        if key not in sha_cache:
            digest = hashlib.sha256()
            with p.open('rb') as stream:
                for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                    digest.update(block)
            sha_cache[key] = digest.hexdigest()
        local[name] = {'bytes': n, 'sha256': sha_cache[key], 'reason': reason,
                       'storage': str(ROOT / p)}
        if p.is_symlink():
            local[name]['symlink_target'] = os.readlink(p)
    rules = ['/' + str(d) + '/' for d in local_dirs]
    rules += ['/' + p for p in local if not any(Path(p) == d or d in Path(p).parents for d in local_dirs)]
    rules = sorted(set(rules))
    (H / 'ignore_rules.txt').write_text('\n'.join(rules) + '\n')
    preignore = (H / 'backup_preimages/gitignore_before_archive').read_text()
    own_block = ('\n# 2026-10-01 v36-v46 archive: exact local raw records, native installs and render frames.\n'
                 '# SHA-256, sizes, storage and recovery: .pipeline/handoffs/2026-10-01_newton_v36_v46_archive/LOCAL_ONLY_BYTES.json\n'
                 + '\n'.join(rules) + '\n')
    assert Path('.gitignore').read_text() == preignore or Path('.gitignore').read_text() == preignore + own_block
    Path('.gitignore').write_text(preignore + own_block)
    (H / 'gitignore_owned_block.txt').write_text(own_block)
    inventory = {
        'archive_date': '2026-10-01', 'project_source_of_truth': str(ROOT),
        'no_bytes_deleted': True, 'files': local,
        'recovery': {
            'raw_physics_sensor_logs': 'Original observations cannot be recreated bit-for-bit by rerunning physics. Keep these exact local paths; copyback source manifests and verified-file receipts remain tracked in the run. A remote execution copy is not the sole archive.',
            'native_install': 'Rebuild the pinned source using runtime/*/build_inside.sh and its build_request.json, pinned ROS Docker image and source/install SHA records. Regenerated binary bytes can differ; do not silently replace a frozen install identity.',
            'display_frames': 'Re-render preserved actual physical states using the tracked executed_render scripts, original request/view_provenance and versions/v43 or v46. No new physics; delivered MP4 remains a tracked ordinary file.',
            'bytecode': 'Import the corresponding preserved Python source with the pinned interpreter; bytecode itself is not physical evidence.',
        },
        'counts': {'files': len(local), 'bytes': sum(v['bytes'] for v in local.values())},
    }
    (H / 'LOCAL_ONLY_BYTES.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    owned.difference_update(local)
    owned.update(str(p.relative_to(ROOT)) for p in files_at(H))
    owned.update(SHARED)
    record = {'roots': [str(p) for p in VERSIONS + NATIVE + AUDITS + RUNS + [OUTPUT]],
              'extra': [str(p) for p in EXTRA], 'shared_delta_only': SHARED,
              'owned_file_count': len(owned), 'tracked_source_and_evidence_bytes':
              sum(Path(p).stat().st_size for p in owned),
              'local_only': inventory['counts'], 'existing_staged_entries_preserved': True}
    (H / 'backup_scope.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    owned.add(str((H / 'backup_scope.json').relative_to(ROOT)))
    temp = Path(tempfile.mkdtemp(prefix='vla-archive-index-'))
    paths = temp / 'owned_paths.nul'
    paths.write_bytes(b'\0'.join(p.encode() for p in sorted(owned)) + b'\0')
    plan = {'temp_dir': str(temp), 'alternate_index': str(temp / 'index'),
            'explicit_paths': str(paths), 'head_before': preflight['head'],
            'path_count': len(owned)}
    (H / 'backup_plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    paths.write_bytes(paths.read_bytes() + str((H / 'backup_plan.json').relative_to(ROOT)).encode() + b'\0')
    print(json.dumps({'plan': plan, 'summary': record}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

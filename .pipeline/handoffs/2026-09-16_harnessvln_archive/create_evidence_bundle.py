#!/usr/bin/env python3
"""Create a local evidence bundle; Git retains its manifest and regeneration code."""
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXP = ROOT / '.pipeline/experiments/2026-09-16_pi_cortex_harnessvln'
OUT = HERE / 'evidence.tar.gz'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


if OUT.exists():
    raise SystemExit('Existing evidence bundle is immutable; use a new archive directory.')
paths = set()
run_roots = [
    'isaac_runner/two_goal_runs/two_goal_20260916T162236Z_p2b_actual4',
    'pointcloud_display/runs/pointcloud_20260916T171400Z_off',
    'pointcloud_display/runs/pointcloud_20260916T172100Z_rviz',
    'pointcloud_display/runs/pointcloud_20260916T173400Z_rviz_gpu',
    'pointcloud_display/qualification/pointcloud_window_20260916T174100Z',
]
for name in run_roots:
    run = EXP / name
    paths.update(p for p in (run / 'returned_artifacts').rglob('*') if p.is_file())
    for folder in ['config', 'observer']:
        paths.update(p for p in (run / folder).rglob('*') if p.is_file())
    for name in ['run_request.json', 'source_env_hashes.json', 'return_verdict.json',
                 'inputs/pilot.json', 'inputs/input_manifest.json', 'inputs/package_manifest.json']:
        if (run / name).is_file():
            paths.add(run / name)
paths.update(p for p in (EXP / 'scan_replan_diagnosis').rglob('*') if p.is_file())
paths.update(p for p in (EXP / 'pointcloud_display').iterdir() if p.is_file())
paths.update(p for p in (EXP / 'pointcloud_display/observer').rglob('*') if p.is_file())
paths.update(p for p in (EXP / 'p2b_execution/qualification/actual4_lead_review').rglob('*') if p.is_file())
for name in ['README.md', 'RESULT.md', 'P2B_RESULT.md']:
    paths.add(EXP / name)
paths = sorted(p for p in paths if '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name != '.DS_Store')
assert all(not p.is_symlink() and p.resolve().is_relative_to(ROOT) for p in paths)
records = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in paths]
with tarfile.open(OUT, 'w:gz', compresslevel=1) as archive:
    for row in records:
        archive.add(ROOT / row['path'], arcname=row['path'], recursive=False)
manifest = {
    'scope': 'Selected native diagnosis, accepted spatial pilot and point-cloud runtime evidence; not a complete simulator dependency distribution.',
    'archive': str(OUT.relative_to(ROOT)), 'archive_sha256': digest(OUT),
    'archive_bytes': OUT.stat().st_size, 'source_bytes': sum(r['bytes'] for r in records),
    'files': records,
    'regeneration': 'Retain source paths from this manifest. In a fresh dated archive directory, copy this script and run it from the VLA checkout; it refuses to replace an existing bundle.',
}
(HERE / 'evidence_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}, indent=2))
print('Bundled files:', len(records))

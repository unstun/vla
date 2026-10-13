"""Analyze closed same-host trials and retain compact, hash-bound comparison data."""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import sys

TASK = Path('/data/sun/vla_mppi_20261009')
VERSION = TASK/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v125'
OUTPUT = TASK/'results/comparison'
OUTPUT.mkdir(exist_ok=True)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


selected = {'baseline': 'v125_baseline_attempt01', 'candidate': 'v125_candidate_attempt02'}
rows, artifacts = {}, {}
for variant in ('baseline', 'candidate'):
    tag = selected[variant]
    trial = TASK/'trials'/tag
    root = trial/'runs'/tag
    execution = json.loads((trial/'evidence/execution.json').read_text())
    if not execution['passed']:
        raise ValueError('Execution incomplete: '+variant)
    if json.loads((root/'retention_result.json').read_text())['status'] != 'completed':
        raise ValueError('Retention incomplete: '+variant)
    output = OUTPUT/variant
    subprocess.run([sys.executable, str(VERSION/'analyze_remote.py'), '--run-root', str(root),
                    '--output', str(output), '--metrics-only'], check=True)
    rows[variant] = json.loads((output/'metrics.json').read_text())
    with (output/'latency.csv').open() as stream:
        slow = [row for row in csv.DictReader(stream) if float(row['solve_ms']) > 60]
    rows[variant]['planning']['over_60ms'] = {
        'rounds': len(slow), 'successful': sum(int(row['success']) for row in slow),
        'failed': sum(not int(row['success']) for row in slow)}
    artifacts[variant] = {'root': str(trial), 'files': {
        str(path.relative_to(trial)): {'bytes': path.stat().st_size, 'sha256': sha(path)}
        for parent in (root, trial/'evidence')
        for path in sorted(parent.rglob('*')) if path.is_file()}}
    artifacts[variant]['total_bytes'] = sum(x['bytes'] for x in artifacts[variant]['files'].values())
candidate = TASK/'trials'/selected['candidate']/'runs'/selected['candidate']
subprocess.run([sys.executable, str(VERSION/'classify_rounds.py'), '--run-root', str(candidate),
                '--output', str(OUTPUT/'candidate/classification.json')], check=True)
classification = json.loads((OUTPUT/'candidate/classification.json').read_text())
overhead = next(json.loads(line.split('V122_OVERHEAD ', 1)[1])
                for line in (TASK/'results/native_outcome_probe.log').read_text().splitlines()
                if 'V122_OVERHEAD ' in line)
summary = {
    'host': 'gpu5070ti', 'host_version': 'v125',
    'native_versions': {'baseline': 'v114', 'candidate': 'v122'},
    'independent_trials_per_variant': 1, 'physics_device': 'cpu',
    'selected_trials': selected,
    'excluded_startup': 'v125_candidate_attempt01: preflight bind failed before container/physics; ports later verified free.',
    'results': rows, 'diagnostic_coverage': {
        'classified': classification['classified'], 'rounds': classification['rounds'],
        'failed_rounds': len(classification['failed_rounds']), 'passed': classification['passed']},
    'synthetic_structured_emission_overhead_us': overhead,
    'limits': ['One independently initialized trial per variant does not estimate a reliable success rate.',
               'Mac/Linux timing differences are not attributed to the diagnostic code.',
               'No Jetson or hardware-actuation validation.',
               'Branch rejection counts are not failed planning-round counts.'],
    'analysis_source_sha256': sha(Path(__file__)),
    'version_manifest_sha256': sha(VERSION/'manifest.json')}
(OUTPUT/'comparison.json').write_text(json.dumps(summary, indent=2)+'\n')
(OUTPUT/'remote_artifacts.json').write_text(json.dumps(artifacts, indent=2)+'\n')
print(json.dumps({'coverage': summary['diagnostic_coverage'],
                  'terminal': {k: v['terminal'] for k, v in rows.items()},
                  'compact_output': str(OUTPUT)}))

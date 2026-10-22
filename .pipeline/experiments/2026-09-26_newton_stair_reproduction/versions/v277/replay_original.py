"""Diagnostic replay of the unchanged v257 ledger on this source revision.

These are development measurements, not a frozen clean-benchmark acceptance.
Every case receives one cold native request with its original paired scans.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, sys, time

HERE = Path(__file__).resolve().parent
BASE = Path('/data/sun/vla_mppi_20261009')
TAG = sys.argv[1] if len(sys.argv)>1 else 'final'
assert TAG.replace('_','').isalnum()
OUT = BASE / ('gpmp_fixed_boundary_v277/evaluation/original52_'+TAG)
assert not OUT.exists()
OUT.mkdir()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inventory = json.loads((BASE / 'gpmp_fixed_boundary_v277/native/source_inventory.json').read_text())
for rel, expected in inventory.items():
    assert sha(BASE / 'gpmp_fixed_boundary_v277/native' / rel) == expected, rel
(OUT / 'source_inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('old_metrics', HERE.parent / 'v257/run_matrix.py')
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)
cases = json.loads((HERE.parent / 'v257/cases_manifest.json').read_text())['cases']
rows = []
for case in cases:
    target = OUT / case['case_id']
    target.mkdir()
    began = time.monotonic()
    with (target / 'stdout.log').open('x') as log:
        result = subprocess.run([sys.executable, str(HERE / 'probe.py'),
            '/task/space_coverage_v257/cases/' + case['case_id'],
            '/evaluation/original52_'+TAG+'/' + case['case_id']],
            stdout=log, stderr=subprocess.STDOUT, timeout=180)
    code = result.returncode
    if (target / 'route_margins.csv').exists():
        with (target / 'independent_audit.log').open('x') as log:
            result = subprocess.run(['/home/sun/vla_exec/envs/newton_worker/bin/python',
                str(HERE.parent / 'v257/independent_solid_audit.py'), 'route', str(target)],
                stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            code = 125
    row = metrics.summarize(target, case, code, time.monotonic() - began)
    (target / 'summary.json').write_text(json.dumps(row, indent=2) + '\n')
    rows.append(row)
    (OUT / 'progress.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps({k: row[k] for k in ('case_id', 'global_admitted',
        'first_gpmp_static_pass', 'scan_published', 'end_to_end_pass')}), flush=True)
(OUT / 'complete.json').write_text(json.dumps(dict(calls=len(rows),
    source_inventory_sha256=sha(OUT / 'source_inventory.json'),
    original_cases_sha256=sha(HERE.parent / 'v257/cases_manifest.json'),
    status='development; not clean-benchmark acceptance'), indent=2) + '\n')

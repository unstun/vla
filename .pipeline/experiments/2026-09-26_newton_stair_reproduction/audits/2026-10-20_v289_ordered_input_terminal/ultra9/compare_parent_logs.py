"""Recount unchanged v288 logs using exactly the v289 literal-code extractor."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

R = Path('/home/ubuntu/sun/vla_v289_20261020')
P = Path('/home/ubuntu/sun/vla_v288_20261020')
E = R / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
sys.path.insert(0, str(E / 'versions/v196'))
from analyze_remote import Capture

assert json.loads((R / 'evidence/physical_batch_complete.json').read_text())['all_closed']
source = E / 'audits/2026-10-20_v289_ordered_input_terminal/failure_bill.py'
spec = importlib.util.spec_from_file_location('same_error_extractor', source)
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)
reference = json.loads((R / 'migration/parent_reference_summary.json').read_text())
rows = []
for row in reference['cases']:
    cid = row['case_id']
    capture = Capture(P / f'physical_runs/v288_{cid}_attempt01/runs/v288_{cid}_attempt01')
    text = capture.read('nav2.log')
    assert hashlib.sha256(text.encode()).hexdigest() == row['nav2_log']['sha256'], cid
    rows.append(dict(case_id=cid, duration_s=row['duration_s'], local_completed=row['local_completed'],
        target_errors=extractor.error_counts(text), sources=capture.sources))
out = R / 'physical_return/parent_log_comparison.json'
assert out.parent.is_dir() and not out.exists()
out.write_text(json.dumps(dict(version='v288', physics_steps=0, parent_source_unchanged=True,
    extractor_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), cases=rows,
    claim='Read-only retrospective recount of the exact original v288 log SHA; excludes dashed replan counter1008 in both versions.'), indent=2) + '\n')
print('Recounted ten unchanged v288 logs; no physical steps')

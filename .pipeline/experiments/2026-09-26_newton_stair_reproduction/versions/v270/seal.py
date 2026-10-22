"""Seal only the completed independent component checks, never native admission."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;OUT=Path('/data/sun/vla_mppi_20261009/source_surface_native_v270')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
u=json.loads((OUT/'unit.json').read_text());p=json.loads((OUT/'source_parity.json').read_text())
assert u['failed']==0 and len(u['cases'])==14
assert p['queries']==512 and p['binary_mismatches']==p['margin_mismatches_1e8']==0
assert p['source_sha256']==u['source_sha256']==sha(HERE/'source_surface.cpp')
assert p['binary_sha256']==u['binary_sha256']==sha(OUT/'build/surface_probe')
R=HERE/'results';R.mkdir(exist_ok=True)
for name in ('unit.json','unit01.log','build01.log','source_parity.json','source_queries.txt','source_answers.txt','source_query.log','source_compare01.log','source_compare02.log','source_compare03.log','reference_progress03.jsonl','source_compare04.log','reference_progress04.jsonl','reference452_diagnosis.log'):
    shutil.copy2(OUT/name,R/name)
parents={str(p.relative_to(HERE.parent)):sha(p) for p in (HERE.parent/'v267/direct_reference.py',HERE.parent/'v268/manifest.json',HERE.parent/'v266/manifest.json')}
receipt=dict(version='v270',scope='Independent finite source component only',scene_queries=512,physical_counterexamples=14,
    binary_mismatches=0,margin_mismatches=0,max_margin_error=p['max_absolute_margin_error'],
    reference_recall='Bounding-box candidates followed by unchanged finite 3-D material clipping',
    reference_z_recall='Reject only source fragments wholly above a cap maximum; no physical query change',
    reference_duplicate_removal='Exact identical convex vertex sets only; no rounding or tolerance changes',
    interrupted_attempt02='Duplicate-heavy Python reference stopped after >20 CPU minutes; log retained; not a pass',
    parent_files=parents,native_planning_calls=0,physics_steps=0)
(R/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('manifest.json','RESULTS.md')}
assert not (HERE/'manifest.json').exists()
(HERE/'manifest.json').write_text(json.dumps(dict(version='v270',files=files,parent_files=parents),indent=2)+'\n')
print(json.dumps(dict(receipt,manifest_sha256=sha(HERE/'manifest.json'))),flush=True)

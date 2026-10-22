"""Freeze independent closed/open source semantics and compact evidence."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;WORK=Path('/data/sun/vla_mppi_20261009/source_topology_v268')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((WORK/'validation.json').read_text());e=json.loads((WORK/'geometry_export.json').read_text())
assert m['filled_fcl_queries']==4000 and not m['mismatches']
assert len(m['physical_controls'])==14 and len(m['new_counterexamples'])==6 and len(m['strict_step_controls'])==3
assert m['source_topology']['vertices_unchanged'] and m['source_topology']['source_face_connectivity_unchanged']
assert m['source_topology']['certified_closed_volumes']==344 and m['source_topology']['winding_changed_faces']==6
assert not m['new_counterexamples'][0]['old_assessment']['free'] and m['new_counterexamples'][0]['assessment']['free']
assert m['new_counterexamples'][4]['old_assessment']['free'] and not m['new_counterexamples'][4]['assessment']['free']
assert all(r['assessment']['free'] for r in m['endpoints'] if r['case_id']!='B08')
assert not next(r for r in m['endpoints'] if r['case_id']=='B08')['assessment']['free']
for k in ('normalized_triangles','closed_volumes'):
    assert sha(Path(e[k]['remote_path']))==e[k]['sha256']
R=HERE/'results';R.mkdir(exist_ok=True)
for name in ('validation.json','geometry_export.json','validate01.log'):shutil.copy2(WORK/name,R/name)
receipt=dict(version='v268',scope='Independent source physical model; no native planner integration',
    closed_volumes=344,surface_only_faces=3444,face_windings_changed=6,coordinates_changed=0,holes_filled=0,
    physical_controls=14,open_inverted_counterexamples=6,strict_step_controls=3,filled_fcl_queries=4000,mismatches=0,
    fixed_source_endpoints_free=7,b08_refused=True,planning_calls=0,physics_steps=0,selected_baseline_unchanged='v232/v233')
(R/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('manifest.json','RESULTS.md')}
(HERE/'manifest.json').write_text(json.dumps(dict(version='v268',scope='independent_source_physics_only',files=files),indent=2)+'\n')
print(json.dumps(dict(receipt,manifest_sha256=sha(HERE/'manifest.json'))),flush=True)

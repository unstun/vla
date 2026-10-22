"""Freeze the independent audit treatment and every saved input before replay."""
from pathlib import Path
import hashlib,json,shutil
import numpy,scipy,shapely,trimesh
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_point_volume_audit_v276';R=HERE/'results'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
p=json.loads((OUT/'precision_controls.json').read_text());w=json.loads((OUT/'witness_controls.json').read_text())
assert p['samples']==5000 and not p['failures'] and 'controls=15 failures=0' in (OUT/'unit02.log').read_text()
assert w['registration_code_sha256']==sha(HERE/'source_material_association.py')
assert 'finite_cap_controls=3 failures=0' in (OUT/'unit02.log').read_text()
assert len(w['queries'])==14 and all(r['registered_margin']>0 for r in w['queries'] if r['case_id']!='B08')
b08=next(r for r in w['queries'] if r['case_id']=='B08');assert b08['registered_margin']==b08['old_margin'] and b08['registered_margin']<-.13
R.mkdir(exist_ok=True)
for name in ['raw_source_diagnosis.json','unit02.log','witness_controls.json','witness01.log','precision_controls.json','precision01.log']:shutil.copy2(OUT/name,R/name)
inputs={}
for cohort in ['original52','clean50']:
    m=json.loads((BASE/'source_benchmark_v273'/cohort/'matrix_summary.json').read_text())
    for row in m['calls']:
        if not row['global_admitted']:continue
        for name in ['route_margins.csv','local_samples_checked.csv']:
            f=BASE/'source_benchmark_v273'/cohort/row['case_id']/name
            if f.exists():inputs[str(f.relative_to(BASE/'source_benchmark_v273'))]=dict(sha256=sha(f),bytes=f.stat().st_size,remote_path=str(f))
assert len(inputs)==172
binding=dict(saved_inputs=inputs,external_files={str(p.relative_to(HERE.parent)):sha(p) for p in [HERE.parent/'v272/raw_source_oracle.py',HERE.parent/'v267/finite_floor_material.py',HERE.parent/'v273/manifest.json',HERE.parent/'v266/surface_model.py']},software=dict(numpy=numpy.__version__,scipy=scipy.__version__,shapely=shapely.__version__,trimesh=trimesh.__version__))
(R/'input_binding.json').write_text(json.dumps(binding,indent=2)+'\n')
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('manifest.json','RESULTS.md')}
(HERE/'manifest.json').write_text(json.dumps(dict(version='v276',scope='Derived independent material audit only; native geometry and scored ledger unchanged',files=files,planning_calls=0,physics_steps=0),indent=2)+'\n')
print(json.dumps(dict(manifest_sha256=sha(HERE/'manifest.json'),saved_tables=len(inputs),source_controls=15,precision_samples=5000,fixed_witnesses=14)),flush=True)

"""Diagnose all refused clean endpoints without changing queries or requests."""
from pathlib import Path
import csv,hashlib,json,math,subprocess,sys
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'saved_output_audit_v264'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary=json.loads((BASE/'mesh_benchmark_v262/matrix_summary.json').read_text())
cases={c['case_id']:c for c in json.loads((BASE/'mesh_benchmark_v262/cases_manifest.json').read_text())['cases']}
failed=[r for r in summary['calls'] if r['expected']=='admit' and not r['global_admitted']]
assert len(failed)==7
with (OUT/'endpoints.txt').open('x') as f:
    for row in failed:
        cid=row['case_id'];values=list(map(float,(BASE/'mesh_benchmark_v262/cases'/cid/'endpoints.txt').read_text().split()));assert len(values)==8
        for which,p,yaw in [('start',values[:3],values[6]),('goal',values[3:6],values[7])]:f.write(' '.join([cid,which,*map(lambda x:format(x,'.17g'),[*p,yaw])])+'\n')
with (OUT/'endpoint_native.log').open('x') as log:subprocess.run([sys.executable,str(HERE/'native.py'),'witness'],stdout=log,stderr=subprocess.STDOUT,check=True)
source=HERE.parent/'v257/independent_solid_audit.py';m=json.loads((source.parent/'manifest.json').read_text());assert sha(source)==m['source_files']['independent_solid_audit.py']
code=source.read_text().split('\nmode=sys.argv[1];')[0];namespace=dict(__file__=str(source),__name__='frozen_point_oracle');exec(compile(code,str(source),'exec'),namespace)
sys.path.insert(0,str(EXP/'audits/2026-10-18_v259_equivalent_geometry_repairs'))
from mesh_geometry import MeshGeometry
tri=BASE/'support_coverage_v134/triangles.f64';assert sha(tri)=='f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc'
mesh=MeshGeometry(namespace['np'].fromfile(tri,dtype='float64').reshape(-1,3,3));half=namespace['half'];rows=[]
for item in csv.DictReader((OUT/'endpoints.csv').open()):
    p=namespace['np'].array([float(item[k]) for k in ('x','y','z')]);yaw=float(item['yaw']);native=float(item['solid_margin'])
    namespace['half']=half;padded=namespace['oracle'](p,yaw);namespace['half']=0.;unpad=namespace['oracle'](p,yaw);namespace['half']=half
    assert abs(native-padded)<1e-6
    free,edge,solid,reason=mesh.pose(p[0],p[1],p[2]-.3,yaw)
    negative=native<0.
    witness=namespace['np'].array([float(item[k]) for k in ('witness_x','witness_y','witness_z')])
    distance,idx=namespace['tree'].query(witness)
    row=dict(item,independent_padded_margin=padded,independent_point_margin_without_padding=unpad,
        original_mesh_free=bool(free),original_mesh_edge_margin=edge,original_mesh_solid_margin=solid,mesh_reason=reason,
        source_witness_matches_record=bool(distance<1e-9) if negative else None,
        witness_source_record=namespace['data'][int(idx)].tolist() if negative else None,
        collision_sign_changed_only_by_voxel_padding=bool(negative and unpad>0. and abs(unpad-(native+math.sqrt(3)*half))<1e-6))
    rows.append(row)
negative=[r for r in rows if float(r['solid_margin'])<0.]
receipt=dict(native='v261',benchmark='v262',queries=len(rows),refused_cases=len(failed),negative_endpoints=len(negative),
    all_refused_endpoints_mesh_free=all(r['original_mesh_free'] for r in negative),
    all_negative_endpoints_padding_only=all(r['collision_sign_changed_only_by_voxel_padding'] for r in negative),
    unchanged_radius_m=.35,source_voxel_half_m=half,source_voxel_padding_m=math.sqrt(3)*half,
    source_solid_sha256=sha(namespace['FIELD']),original_mesh_sha256=sha(tri),
    source_evaluator_sha256=sha(source),native_queries_changed=False,physics_steps=0,planning_calls=0,rows=rows)
(OUT/'endpoint_diagnosis.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='rows'}),flush=True)

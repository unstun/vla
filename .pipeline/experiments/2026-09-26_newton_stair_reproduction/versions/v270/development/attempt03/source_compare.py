"""512 predeclared scene geometry queries, not new planning benchmark cases."""
from pathlib import Path
import ast,hashlib,json,math,os,subprocess,sys,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from shapely.geometry import Point,box
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_surface_native_v270'
sys.path.insert(0,str(HERE.parent/'v268'))
from source_model import SurfaceModel,geometry as legacy
parent=HERE.parent/'v267/direct_reference.py'
node=next(n for n in ast.parse(parent.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='DirectReference')
context=dict(np=np,math=math,Point=Point,box=box,SurfaceModel=SurfaceModel,clip=legacy.clip,
             projected=legacy.projected,remove_cap=legacy.remove_cap,cap_halfspaces=legacy.cap_halfspaces,EPS=legacy.EPS)
code=ast.unparse(node).replace('projected(before).intersects(q)','box(*projected(before).bounds).intersects(box(*q.bounds))')
# Exact duplicate convex pieces represent the same set. Keep one without any
# coordinate rounding, simplification, tolerance or changed clipping predicate.
code=code.replace('if not parts:', 'parts=list({tuple(sorted(set(map(tuple,part)))):part for part in parts}.values())\n                    if not parts:')
exec(compile(code,str(parent),'exec'),context)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
data=json.loads((BASE/'source_topology_v268/geometry_export.json').read_text())
for name in ('normalized_triangles','closed_volumes'):assert sha(Path(data[name]['remote_path']))==data[name]['sha256']
tp=BASE/'support_coverage_v134/triangles.f64';assert sha(tp)==data['original_triangles_sha256']
reference=context['DirectReference'](np.fromfile(tp,dtype='<f8').reshape(-1,3,3))
rows=json.loads((BASE/'source_surface_v266/source_inspection.json').read_text())['rows']
queries=[[*r['body'][:2],r['ground'],r['yaw']] for r in rows]
rng=np.random.default_rng(269)
for g in (rows[0]['ground'],rows[3]['ground'],rows[6]['ground'],2.80303049):
    for _ in range(126):queries.append([*rng.uniform([-7.5,-9.5],[10.5,8.5]),g,float(rng.uniform(-math.pi,math.pi))])
assert len(queries)==512
q=OUT/'source_queries.txt';q.write_text(''.join(' '.join(format(x,'.17g') for x in p)+'\n' for p in queries))
with (OUT/'source_query.log').open('w') as log:
    subprocess.run([sys.executable,str(HERE/'native.py'),'query',
      '/task/source_topology_v268/triangles_oriented.f64','/task/source_topology_v268/closed_volumes.txt',
      '/work/source_queries.txt','/work/source_answers.txt'],stdout=log,stderr=subprocess.STDOUT,check=True)
actual=np.loadtxt(OUT/'source_answers.txt');assert len(actual)==512
expected=[];started=time.monotonic()
for i,p in enumerate(queries):
    value=reference.assess(*p,check_support=False)['solid'];expected.append(value)
    with (OUT/'reference_progress03.jsonl').open('a') as progress:
        progress.write(json.dumps(dict(index=i,margin=value,wall_s=time.monotonic()-started))+'\n')
    if i%16==0:print(json.dumps(dict(reference_queries=i+1,wall_s=time.monotonic()-started)),flush=True)
expected=np.array(expected);error=abs(expected-actual);bad=np.flatnonzero(error>1e-8);binary=np.flatnonzero((expected<=0)!=(actual<=0))
receipt=dict(queries=512,binary_mismatches=len(binary),margin_mismatches_1e8=len(bad),max_absolute_margin_error=float(error.max()),
    first_differences=[dict(index=int(i),pose=queries[int(i)],cpp=float(actual[i]),reference=float(expected[i])) for i in bad[:20]],
    cpp_timing_log=(OUT/'source_query.log').read_text(),query_sha256=sha(q),binary_sha256=sha(OUT/'build/surface_probe'),
    source_sha256=sha(HERE/'source_surface.cpp'),oracle_source_sha256=sha(HERE/'source_model.py'),model_manifest_sha256=sha(HERE.parent/'v268/manifest.json'),
    source_geometry=data,planning_calls=0,physics_steps=0,planner_install_modified=False)
(OUT/'source_parity.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='source_geometry'}),flush=True)
assert not len(bad) and not len(binary)

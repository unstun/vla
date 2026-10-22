"""Original-source exact C++/Python margin parity and CPU2 query timing."""
from pathlib import Path
import hashlib,json,math,os,subprocess,sys,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_surface_native_v267'
sys.path.insert(0,str(HERE.parent/'v266'))
from surface_model import SurfaceModel
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tp=BASE/'support_coverage_v134/triangles.f64'
assert sha(tp)=='f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc'
tri=np.fromfile(tp,dtype='<f8').reshape(-1,3,3);model=SurfaceModel(tri)
original=json.loads((BASE/'source_surface_v266/source_inspection.json').read_text())['rows']
queries=[[*r['body'][:2],r['ground'],r['yaw']] for r in original]
rng=np.random.default_rng(267)
for g in (original[0]['ground'],original[3]['ground'],original[6]['ground'],2.80303049):
    for _ in range(1000):queries.append([*rng.uniform([-7.5,-9.5],[10.5,8.5]),g,float(rng.uniform(-math.pi,math.pi))])
qpath=OUT/'queries.txt';qpath.write_text(''.join(' '.join(format(v,'.17g') for v in q)+'\n' for q in queries))
with (OUT/'query01.log').open('w') as log:
    subprocess.run([sys.executable,str(HERE/'native.py'),'query','/task/support_coverage_v134/triangles.f64'],stdout=log,stderr=subprocess.STDOUT,check=True)
actual=np.loadtxt(OUT/'answers.txt');assert len(actual)==len(queries)
reference=[];started=time.monotonic()
for i,q in enumerate(queries):
    a=model.assess(*q,check_support=False);reference.append(min(.15,a['solid']))
    if i<8:print(json.dumps(dict(case_id=original[i]['case_id'],cpp=float(actual[i]),python=reference[-1])),flush=True)
reference=np.asarray(reference);delta=abs(actual-reference);bad=np.flatnonzero(delta>1e-8);binary=np.flatnonzero((actual<=0)!=(reference<=0))
np.savetxt(OUT/'python_answers.txt',reference,fmt='%.17g')
receipt=dict(queries=len(queries),binary_mismatches=len(binary),margin_mismatches_1e8=len(bad),max_absolute_margin_error=float(delta.max()),
    first_differences=[dict(index=int(i),pose=queries[int(i)],cpp=float(actual[i]),python=float(reference[i])) for i in bad[:20]],
    query_stream_sha256=sha(qpath),native_binary_sha256=sha(OUT/'build/surface_probe'),native_source_sha256=sha(HERE/'source_surface.cpp'),
    python_source_sha256=sha(HERE.parent/'v266/surface_model.py'),source_triangles_sha256=sha(tp),
    cpp_timing_log=(OUT/'query01.log').read_text(),python_reference_wall_s=time.monotonic()-started,
    planning_calls=0,physics_steps=0,planner_install_modified=False)
(OUT/'parity.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
assert not len(bad) and not len(binary)

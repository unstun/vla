"""Find exact source faces behind every failed independent comparison."""
from pathlib import Path
import ast,json,math,os,subprocess,sys
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from shapely.geometry import Point,box
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_surface_native_v269'
sys.path.insert(0,str(HERE.parent/'v268'))
from surface_model import SurfaceModel,module as legacy
tp=BASE/'support_coverage_v134/triangles.f64';tri=np.fromfile(tp,dtype='<f8').reshape(-1,3,3)
source=(HERE.parent/'v267/direct_reference.py').read_text()
source=source[source.index('class DirectReference:'):]
source=source.replace("s=self.source;zlo=ground+.3-.55;zhi=ground+.3+.35;answer=.15","s=self.source;zlo=ground+.3-.55;zhi=ground+.3+.35;answer=.15;nearest=None")
source=source.replace("for part in parts:answer=min(answer,projected(part).distance(c)-.35)",'''for part in parts:
                    value=projected(part).distance(c)-.35
                    if value<answer:
                        answer=value
                        gid=int(s.solid_ids[i]);bounds=s.topology['objects_detail'][gid]['bounds'] if gid>=0 else None
                        nearest=dict(triangle=int(i),solid_id=gid,normal=s.normal[i].tolist(),vertices=s.tri[i].tolist(),source_xy_area=projected(list(s.tri[i])).area,closed_bounds=bounds,part=[v.tolist() for v in part])''')
source=source.replace("return dict(solid=-.35)","return dict(solid=-.35,witness=nearest)").replace("return dict(solid=answer)","return dict(solid=answer,witness=nearest)")
ctx=dict(np=np,math=math,Point=Point,box=box,SurfaceModel=SurfaceModel,clip=legacy.clip,projected=legacy.projected,remove_cap=legacy.remove_cap,cap_halfspaces=legacy.cap_halfspaces,EPS=legacy.EPS)
exec(compile(source,'diagnostic_direct_reference','exec'),ctx);model=ctx['DirectReference'](tri)
failed=json.loads((OUT/'source_parity.json').read_text())['first_differences'];rows=[]
for r in failed:rows.append(dict(r,diagnostic=model.assess(*r['pose'],check_support=False)))
n=len(tri);meta=OUT/'diagnostic_surface_only.meta';meta.write_text(f'SURFACE268C {n} 0\nF\n'+'-1\n'*n)
q=OUT/'diagnostic_queries.txt';q.write_text(''.join(' '.join(format(v,'.17g') for v in r['pose'])+'\n' for r in failed))
with (OUT/'diagnostic_surface_only.log').open('w') as log:
    subprocess.run([sys.executable,str(HERE/'native.py'),'query','/task/source_topology_v268/triangles_oriented.f64','/work/diagnostic_surface_only.meta','/work/diagnostic_queries.txt','/work/diagnostic_surface_only_answers.txt'],stdout=log,stderr=subprocess.STDOUT,check=True)
answers=np.loadtxt(OUT/'diagnostic_surface_only_answers.txt')
for row,a in zip(rows,answers):row['cpp_with_all_volume_labels_disabled']=float(a)
receipt=dict(rows=rows,diagnostic_only=True,production_model_changed=False,planning_calls=0,physics_steps=0)
(OUT/'difference_diagnosis.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)

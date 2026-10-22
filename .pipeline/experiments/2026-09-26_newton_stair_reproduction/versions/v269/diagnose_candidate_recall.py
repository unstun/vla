"""Isolate only the reference's projected-cap candidate predicate."""
from pathlib import Path
import json,math,os,sys
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from shapely.geometry import Point,box
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_surface_native_v269'
sys.path.insert(0,str(HERE.parent/'v268'))
from surface_model import SurfaceModel,module as legacy
source=(HERE.parent/'v267/direct_reference.py').read_text();source=source[source.index('class DirectReference:'):]
original='projected(before).intersects(q)'
replacement='box(*projected(before).bounds).intersects(box(*q.bounds))'
assert source.count(original)==1;source=source.replace(original,replacement)
ctx=dict(np=np,math=math,Point=Point,box=box,SurfaceModel=SurfaceModel,clip=legacy.clip,
         projected=legacy.projected,remove_cap=legacy.remove_cap,cap_halfspaces=legacy.cap_halfspaces,EPS=legacy.EPS)
exec(compile(source,'bbox_candidate_only_reference','exec'),ctx)
tri=np.fromfile(BASE/'support_coverage_v134/triangles.f64',dtype='<f8').reshape(-1,3,3)
reference=ctx['DirectReference'](tri);rows=[]
for r in json.loads((OUT/'source_parity.json').read_text())['first_differences']:
    value=reference.assess(*r['pose'],check_support=False)['solid']
    rows.append(dict(r,bbox_candidate_reference=value,only_broad_phase_predicate_changed=True))
receipt=dict(rows=rows,geometry_and_radius_unchanged=True,narrow_phase_unchanged=True,planning_calls=0,physics_steps=0)
(OUT/'candidate_recall_diagnosis.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)

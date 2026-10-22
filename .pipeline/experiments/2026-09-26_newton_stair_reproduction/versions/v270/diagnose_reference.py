"""Inspect retained reference query452 without changing its result."""
from pathlib import Path
import ast,math,sys,time,signal
import numpy as np
from shapely.geometry import Point,box
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
from source_model import SurfaceModel,geometry
parent=HERE.parent/'v267/direct_reference.py'
c=ast.unparse(next(n for n in ast.parse(parent.read_text()).body if isinstance(n,ast.ClassDef)))
c=c.replace('projected(before).intersects(q)','box(*projected(before).bounds).intersects(box(*q.bounds))')
c=c.replace('if not parts:',"parts=list({tuple(sorted(set(map(tuple,part)))):part for part in parts}.values())\n                    if len(parts)>100: print(dict(face=int(i),parts=len(parts)),flush=True)\n                    if not parts:")
context=dict(np=np,math=math,Point=Point,box=box,SurfaceModel=SurfaceModel,clip=geometry.clip,projected=geometry.projected,remove_cap=geometry.remove_cap,cap_halfspaces=geometry.cap_halfspaces,EPS=geometry.EPS)
exec(compile(c,str(parent),'exec'),context)
ref=context['DirectReference'](np.fromfile(BASE/'support_coverage_v134/triangles.f64',dtype='<f8').reshape(-1,3,3))
p=np.loadtxt(BASE/'source_surface_native_v270/source_queries.txt')[452];print(dict(index=452,pose=p.tolist()),flush=True)
import faulthandler
faulthandler.dump_traceback_later(20,repeat=False)
signal.alarm(30)
print(ref.assess(*p),flush=True)

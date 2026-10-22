"""Independent *filled* CAD primitives; no shared terrain clipping oracle.

The triangle model receives complete closed source boxes. The oracle receives
FCL convex Box objects with explicitly specified material identities, without
calling the model's clipping, cap selection, projected distance or ray filling.
"""
from pathlib import Path
import ast,hashlib,json,math,os,sys
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_surface_v266'
sys.path.insert(0,str(BASE/'floor_reason_v223/analysis_deps'))
import fcl
from surface_model import SurfaceModel
HERE=Path(__file__).resolve().parent
source=HERE/'validate_surface.py'
function=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='box')
context=dict(np=np,math=math);exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),context)
box=context['box'];floor=box([0,0,-.1],[5,5,.1])
cases={
    'wall':([1.,0,.75],[.1,3,.75],False),
    'column':([.75,0,1],[.1,.1,1],False),
    'finite_wall':([1.,0,.75],[.1,.1,.75],False),
    'low_ceiling':([0,0,.55],[2,2,.1],False),
    'high_ceiling':([0,0,1.1],[2,2,.1],False),
    'tall_step':([1,0,.175],[1,2,.175],False),
    'short_step_terrain':([1,0,.1],[1,2,.1],True),
    'contained_in_wall':([0,0,1],[1,1,1],False),
}
def raw_oracle(x,y,yaw,obstacle):
    if obstacle is None:return False
    for side in (-1,1):
        c=np.array([x+side*.18*math.cos(yaw),y+side*.18*math.sin(yaw),.2])
        body=fcl.CollisionObject(fcl.Cylinder(.35,.9),fcl.Transform(c))
        if fcl.collide(body,obstacle,fcl.CollisionRequest(),fcl.CollisionResult()):return True
    return False

rng=np.random.default_rng(26601);mismatches=[];queries=0
for name,(center,half,terrain) in cases.items():
    model=SurfaceModel(np.concatenate([floor,box(center,half)]))
    obstacle=None if terrain else fcl.CollisionObject(fcl.Box(*(2*np.array(half))),fcl.Transform(np.array(center,float)))
    poses=[(*rng.uniform(-1.8,1.8,2),rng.uniform(-math.pi,math.pi)) for _ in range(500)]
    # Explicit tangencies and closed-solid containment are separate from random coverage.
    if name=='wall':poses.extend([(1.-.1-.35-.18+delta,0.,0.) for delta in (-1e-6,1e-6)])
    if name=='contained_in_wall':poses.extend([(0.,0.,0.),(0.,0.,math.pi/2)])
    for x,y,yaw in poses:
        value=model.assess(x,y,0.,yaw,check_support=False)['solid']
        actual=value<=0;expected=raw_oracle(x,y,yaw,obstacle)
        if actual!=expected:mismatches.append(dict(fixture=name,pose=[float(x),float(y),float(yaw)],source_surface_margin=value,filled_fcl_collision=expected))
        queries+=1
receipt=dict(oracle='python-fcl 0.7.0.8 filled convex Box versus Cylinder',queries=queries,mismatches=mismatches,
    shared_clipping_or_filling=False,radius_m=.35,offset_m=.18,finite_vertical_interval=[-.25,.65],
    model_sha256=hashlib.sha256((HERE/'surface_model.py').read_bytes()).hexdigest(),
    oracle_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),physics_steps=0,planning_calls=0)
(OUT/'primitive_oracle.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
assert not mismatches

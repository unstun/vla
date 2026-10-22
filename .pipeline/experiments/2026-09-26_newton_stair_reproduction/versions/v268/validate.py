"""Independent source semantics, literal open faces and filled CAD controls."""
from pathlib import Path
import hashlib,json,math,os,sys,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_topology_v268';OUT.mkdir(exist_ok=True)
HERE=Path(__file__).resolve().parent
from surface_model import SurfaceModel,module as legacy
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=HERE.parent/'v266';manifest=json.loads((old/'manifest.json').read_text())
for name in ('surface_model.py','validate_surface.py','validate_primitive_oracle.py'):
    assert sha(old/name)==manifest['files'][name]
scope=dict(__file__=str(old/'validate_surface.py'),__name__='frozen_cad_controls')
code=(old/'validate_surface.py').read_text().split('models={k:SurfaceModel')[0]
exec(compile(code,str(old/'validate_surface.py'),'exec'),scope)
box=scope['box'];fixtures=scope['fixtures'];controls=scope['controls'];fcl_collision=scope['fcl_collision']
models={k:SurfaceModel(v) for k,v in fixtures.items()};results=[]
for name,x,y,g,yaw,expected in controls:
    actual=models[name].assess(x,y,g,yaw)
    results.append(dict(fixture=name,pose=[x,y,g,yaw],expected=expected,assessment=actual))
    assert actual['free']==expected,results[-1]

floor=fixtures['floor'];open_roof=np.array([[[-2,-2,2],[2,-2,2],[2,2,2]],[[-2,-2,2],[2,2,2],[-2,2,2]]],float)
open_wall=np.array([[[.75,-2,0],[.75,2,0],[.75,2,2]],[[.75,-2,0],[.75,2,2],[.75,-2,2]]],float)
new=[('open_roof',np.concatenate([floor,open_roof]),[0,0,0,0],True),
     ('open_roof_reversed',np.concatenate([floor,open_roof[:,::-1]]),[0,0,0,0],True),
     ('open_wall_front',np.concatenate([floor,open_wall]),[.3,0,0,0],False),
     ('open_wall_back',np.concatenate([floor,open_wall]),[1.2,0,0,0],False),
     ('inverted_closed_wall',np.concatenate([floor,box([0,0,1],[1,1,1])[:,::-1]]),[0,0,0,0],False),
     ('inverted_closed_floor',floor[:,::-1],[0,0,0,0],True)]
counterexamples=[]
for name,tri,pose,expected in new:
    model=SurfaceModel(tri);a=model.assess(*pose);old_a=legacy.SurfaceModel(tri).assess(*pose)
    counterexamples.append(dict(case_id=name,expected=expected,assessment=a,old_assessment=old_a,topology=model.topology))
    assert a['free']==expected,counterexamples[-1]
assert not counterexamples[0]['old_assessment']['free']
assert counterexamples[4]['old_assessment']['free']

context=dict(__file__=str(old/'validate_primitive_oracle.py'),__name__='frozen_filled_cad_oracle')
prefix=(old/'validate_primitive_oracle.py').read_text().split('rng=np.random.default_rng')[0]
exec(compile(prefix,str(old/'validate_primitive_oracle.py'),'exec'),context)
rng=np.random.default_rng(268);differential=[];count=0
for name,(center,half,terrain) in context['cases'].items():
    model=SurfaceModel(np.concatenate([floor,box(center,half)]))
    fcl=context['fcl'];obj=None if terrain else fcl.CollisionObject(fcl.Box(*(2*np.array(half))),fcl.Transform(np.array(center,float)))
    for i in range(500):
        x,y=rng.uniform(-1.8,1.8,2);yaw=rng.uniform(-math.pi,math.pi)
        a=model.assess(float(x),float(y),0.,float(yaw),check_support=False)['solid']<=0
        b=context['raw_oracle'](x,y,yaw,obj)
        if a!=b:differential.append(dict(fixture=name,pose=[float(x),float(y),0.,float(yaw)],model=a,filled_fcl=b))
        count+=1
assert not differential,differential[:10]
critical=[]
for h,expected in ((.26-1e-7,True),(.26,False),(.26+1e-7,False)):
    a=SurfaceModel(np.concatenate([floor,box([1,0,h*.5],[1,2,h*.5])])).assess(-.2,0.,0.,math.pi/2)
    critical.append(dict(height=h,expected_free=expected,assessment=a));assert a['free']==expected,critical[-1]

tp=BASE/'support_coverage_v134/triangles.f64';assert sha(tp)=='f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc'
original=SurfaceModel(np.fromfile(tp,dtype='<f8').reshape(-1,3,3));endpoints=[]
for r in json.loads((BASE/'source_surface_v266/source_inspection.json').read_text())['rows']:
    x,y,z=r['body'];g=z-.3;a=original.assess(x,y,g,r['yaw'])
    endpoints.append(dict(case_id=r['case_id'],body=r['body'],yaw=r['yaw'],assessment=a))
    print(json.dumps(endpoints[-1]),flush=True)
receipt=dict(version='v268',geometry_coordinates_unchanged=True,old_global_winding_model_adopted=False,
    physical_controls=results,new_counterexamples=counterexamples,filled_fcl_queries=count,mismatches=differential,
    strict_step_controls=critical,source_topology=original.topology,endpoints=endpoints,planning_calls=0,physics_steps=0,
    source_triangles_sha256=sha(tp),trimesh_version=original.topology['version'])
def strict(v):
    if isinstance(v,float) and not math.isfinite(v):return None
    if isinstance(v,list):return [strict(x) for x in v]
    if isinstance(v,dict):return {k:strict(x) for k,x in v.items()}
    return v
(OUT/'validation.json').write_text(json.dumps(strict(receipt),indent=2,allow_nan=False)+'\n')
assert all(r['assessment']['free'] for r in endpoints if r['case_id']!='B08')
assert not next(r for r in endpoints if r['case_id']=='B08')['assessment']['free']
print(json.dumps(dict(controls=len(results),new_counterexamples=len(counterexamples),filled_fcl_queries=count,mismatches=0,source_topology={k:v for k,v in original.topology.items() if k!='objects_detail'})),flush=True)

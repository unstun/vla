"""Independent finite-cylinder/FCL controls and fixed source endpoint replay."""
from pathlib import Path
import hashlib,json,math,os,sys,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_surface_v266'
sys.path.insert(0,str(BASE/'floor_reason_v223/analysis_deps'))
import fcl
from surface_model import SurfaceModel

def box(center,half):
    c=np.asarray(center,float);h=np.asarray(half,float)
    corners=np.array([[x,y,z] for x in (-1,1) for y in (-1,1) for z in (-1,1)],float)*h+c
    triangles=[]
    for axis in range(3):
        for sign in (-1,1):
            ids=[i for i,p in enumerate(corners) if abs(p[axis]-c[axis]-sign*h[axis])<1e-9]
            axis1,axis2=[i for i in range(3) if i!=axis]
            ids.sort(key=lambda i:math.atan2((corners[i]-c)[axis2],(corners[i]-c)[axis1]))
            for abc in ((ids[0],ids[1],ids[2]),(ids[0],ids[2],ids[3])):
                t=corners[list(abc)];n=np.cross(t[1]-t[0],t[2]-t[0])
                if n[axis]*sign<0:t=t[[0,2,1]]
                triangles.append(t)
    return np.array(triangles)

def fcl_model(view):
    ts=[]
    for p in view['pieces']:
        for i in range(1,len(p)-1):
            t=np.array([p[0],p[i],p[i+1]])
            if np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>1e-13:ts.append(t)
    if not ts:return None
    vertices=np.array(ts).reshape(-1,3);faces=np.arange(len(vertices)).reshape(-1,3)
    model=fcl.BVHModel();model.beginModel(len(vertices),len(faces));model.addSubModel(vertices,faces);model.endModel()
    return fcl.CollisionObject(model)

def fcl_collision(model,x,y,g,yaw):
    view=model.view(g);mesh=fcl_model(view)
    for side in (-1,1):
        cx=x+side*model.offset*math.cos(yaw);cy=y+side*model.offset*math.sin(yaw)
        if model.occupied_axis_interval(cx,cy,g,view):return True
        if mesh is None:continue
        c=fcl.CollisionObject(fcl.Cylinder(model.radius,view['zhi']-view['zlo']),fcl.Transform(np.array([cx,cy,(view['zlo']+view['zhi'])*.5])))
        if fcl.collide(c,mesh,fcl.CollisionRequest(),fcl.CollisionResult()):return True
    return False

floor=box([0,0,-.1],[5,5,.1])
fixtures={
 'floor':floor,
 'wall':np.concatenate([floor,box([1.,0,.75],[.1,3,.75])]),
 'column':np.concatenate([floor,box([.75,0,1],[.1,.1,1])]),
 'low_ceiling':np.concatenate([floor,box([0,0,.55],[2,2,.1])]),
 'high_ceiling':np.concatenate([floor,box([0,0,1.1],[2,2,.1])]),
 'step':np.concatenate([floor,box([1,0,.1],[1,2,.1])]),
 'tall_step':np.concatenate([floor,box([1,0,.175],[1,2,.175])]),
 'thick_wall':np.concatenate([floor,box([0,0,1],[1,1,1])]),
 'stacked_floor':np.concatenate([floor,box([0,0,2.9],[4,4,.1])]),
 'finite_wall':np.concatenate([floor,box([1.,0,.75],[.1,.1,.75])]),
}
# A finite ramp is an actual affine upward cap, not a constant-height waiver.
ramp=box([0,0,-.1],[3,2,.1]);ramp[:,:,2]+=.08*ramp[:,:,0]
fixtures['ramp']=ramp
controls=[('floor',0,0,0,0,True),('wall',.5,0,0,0,False),
 ('wall',0,0,0,0,True),('column',.25,0,0,0,False),
 ('low_ceiling',0,0,0,0,False),('high_ceiling',0,0,0,0,True),
 ('step',.25,0,0,0,True),('tall_step',-.1,0,0,0,False),
 ('thick_wall',0,0,0,0,False),('stacked_floor',0,0,3,0,True),
 ('stacked_floor',0,0,0,0,True),('finite_wall',.5,1,0,0,True),
 ('ramp',0,0,0,0,True),('floor',4.6,0,0,0,False)]
models={k:SurfaceModel(v) for k,v in fixtures.items()};results=[]
for name,x,y,g,yaw,expected in controls:
    actual=models[name].assess(x,y,g,yaw)
    results.append(dict(fixture=name,pose=[x,y,g,yaw],expected=expected,assessment=actual))
    assert actual['free']==expected,results[-1]
rng=np.random.default_rng(266);diff=[];count=0
for name,model in models.items():
    for i in range(300):
        x,y=rng.uniform(-1.8,1.8,2);yaw=rng.uniform(-math.pi,math.pi);g=3. if name=='stacked_floor' and i%2 else 0.
        actual=model.assess(x,y,g,yaw,check_support=False)['solid']<=0
        independent=fcl_collision(model,x,y,g,yaw)
        if actual!=independent:diff.append(dict(fixture=name,pose=[float(x),float(y),g,float(yaw)],model_collision=actual,fcl_collision=independent))
        count+=1
assert not diff,diff[:10]
invalid=False
try:models['floor'].assess(math.nan,0,0,0)
except ValueError:invalid=True
assert invalid
tp=BASE/'support_coverage_v134/triangles.f64';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(tp)=='f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc'
original=SurfaceModel(np.fromfile(tp,dtype='<f8').reshape(-1,3,3));inspected=json.loads((OUT/'source_inspection.json').read_text());endpoints=[]
for r in inspected['rows']:
    x,y,z=r['body'];g=z-.3;started=time.monotonic();a=original.assess(x,y,g,r['yaw'])
    oracle=fcl_collision(original,x,y,g,r['yaw'])
    assert (a['solid']<=0)==oracle,(r['case_id'],a,oracle)
    endpoints.append(dict(case_id=r['case_id'],endpoint=r['endpoint'],requested_body=r['body'],yaw=r['yaw'],assessment=a,fcl_solid_collision=oracle,wall_s=time.monotonic()-started))
assert not next(r for r in endpoints if r['case_id']=='B08')['assessment']['free']
receipt=dict(model='v266-independent-finite-source-surface',radius=.35,offset=.18,source_triangles_sha256=sha(tp),synthetic_controls=results,random_fcl_queries=count,fcl_mismatches=diff,endpoints=endpoints,invalid_query_rejected=invalid,planning_calls=0,physics_steps=0,adopted_by_planner=False,
 caveat='FCL independently checks clipped finite surfaces; the oriented-ray containment check is shared and separately covered by explicit closed-box containment controls. Support cap union is a local source-presence diagnostic, not a connected support or dynamic contact certificate.')
(OUT/'surface_validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('synthetic_controls','endpoints')}),flush=True)
print(json.dumps(endpoints),flush=True)

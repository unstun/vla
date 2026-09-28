"""Synthetic mapped-object negatives with measured Newton first-hit clouds.
PCT and scanner receive geometry only. Object names serve scoring only.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib,importlib.util,json,os,sys
import numpy as np
from scipy import ndimage
from scipy.spatial.transform import Rotation
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
sys.path.insert(0,str(BASE/'scripts'))
import warp as wp
wp.config.kernel_cache_dir=str(BASE/'runtime/warp-cache');wp.init();wp.set_device('cpu')
import newton
from scene_assets import load_mid360_pattern
from robot_scene import fixed_frame_transform

def mod(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
ref=ROOT/'references/upstream/2026-09-27_pct_ground_cost_reference'
generator=mod('pct_ground_generator',ref/'source/scripts/generate_pct_tomogram.py')
publisher=mod('pct_ground_publisher',BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py')
config=generator.make_config(SimpleNamespace(**json.loads((ref/'historical_generation.json').read_text())['config']))
mount=fixed_frame_transform(BASE/'inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface.urdf','mid360_scan_frame')
origin=mount[:3,3]+[0,0,.3];rotation=mount[:3,:3];quat=Rotation.from_matrix(rotation).as_quat()
pattern=load_mid360_pattern(BASE/'inputs/livox_mid360/mid360.csv')
room=[(0,0,-.1,5.5,5.5,.1),(4.5,0,1.5,.1,5,1.5),(-4.5,0,1.5,.1,5,1.5),(0,4.5,1.5,4.5,.1,1.5),(0,-4.5,1.5,4.5,.1,1.5)]
cases={'mapped_low_box':[(1.6,0,.065,.3,.35,.065)],'mapped_low_box_near_wall':[(1.6,0,.065,.3,.35,.065),(1.6,.75,.7,1.,.025,.7)],'mapped_box':[(1.6,0,.45,.3,.35,.45)],'mapped_short_wall':[(1.6,0,.21,.1,.55,.21)],'mapped_overhead':[(1.6,0,.4,.4,.55,.04)]}
def surfaces(box):
 c=np.array(box[:3]);h=np.array(box[3:]);cloud=[]
 for axis in range(3):
  others=[i for i in range(3) if i!=axis];a,b=[np.linspace(-h[i],h[i],int(np.ceil(2*h[i]/.02))+1) for i in others];aa,bb=np.meshgrid(a,b,indexing='ij')
  for sign in [-1,1]:
   pts=np.zeros((aa.size,3));pts[:,axis]=sign*h[axis];pts[:,others[0]]=aa.ravel();pts[:,others[1]]=bb.ravel();cloud.append(pts+c)
 return np.concatenate(cloud).astype(np.float32)
summary=[]
for name,objects in cases.items():
 dest=HERE/name;dest.mkdir();builder=newton.ModelBuilder()
 for i,box in enumerate(room+objects):
  builder.add_shape_box(-1,xform=wp.transform(wp.vec3(*box[:3])),hx=box[3],hy=box[4],hz=box[5],label='shape_'+str(i))
 model=builder.finalize(device='cpu');model.bvh_build_shapes(model.state())
 names=[]
 for index in range(20):
  rays,_=pattern.scan_window(index);world=(rays@rotation.T).astype(np.float32);n=len(rays);dist=wp.zeros(n,dtype=wp.float32);hits=wp.zeros(n,dtype=wp.int32)
  newton.intersect_ray(model,ray_origins=wp.array(np.repeat(origin[None,:],n,axis=0),dtype=wp.vec3),ray_directions=wp.array(world,dtype=wp.vec3),ray_worlds=wp.zeros(n,dtype=wp.int32),out_dist=dist,out_shape_id=hits,fast_math=False)
  ranges=dist.numpy();keep=np.isfinite(ranges)&(ranges>=.1)&(ranges<=40.);fn=f'cloud_{index:03d}.f32';(rays[keep]*ranges[keep,None]).astype('<f4').tofile(dest/fn);names.append(fn)
 # The offline mapped test scene is a separate synthetic PCT prior, never live
 # actor metadata. Its point samples are used only by the original generator.
 points=np.concatenate([surfaces(box) for box in room+objects]);lo,hi=points.min(0),points.max(0);center=(lo[:2]+hi[:2])/2;nx,ny=(np.ceil((hi[:2]-lo[:2])/.1).astype(int)+4).tolist();count=int(np.ceil(hi[2]/.5));capture={}
 def observe(frame,event,arg):
  if event=='return' and frame.f_code is generator.cpu_point2map.__code__:
   f=frame.f_locals;capture['raw']=f['trav_cost'][f['idx_simp']].copy()
 sys.setprofile(observe)
 try:r=generator.cpu_point2map(points,center,nx,ny,count,.5,config,np,ndimage)
 finally:sys.setprofile(None)
 prior={'data':np.stack(r[:5]).astype(np.float16),'resolution':.1,'center':center,'slice_dh':.5,'slice_h0':.5}
 selected=publisher.selected_ground_points(prior);selected.tofile(dest/'ground.f32')
 shadow=dict(prior);shadow['data']=prior['data'].copy();shadow['data'][0]=capture['raw'].astype(np.float16);qualified=publisher.selected_ground_points(shadow)
 key=lambda x:tuple(x[:3].view(np.uint32));oldkeys={key(x) for x in selected};rawkeys={key(x) for x in qualified};assert oldkeys<=rawkeys
 qualified.tofile(dest/'qualified_ground.f32')
 (dest/'clouds.txt').write_text('\n'.join(names)+'\n');(dest/'body_pose.txt').write_text('0 0 0.3 0 0 0 1\n');(dest/'sensor_pose.txt').write_text(' '.join(map(str,np.r_[origin,quat]))+'\n');(dest/'start_goal.txt').write_text('0 0 0.3 3.0 1.0 0.3\n')
 queries=['0 0 .3 0 start','1.6 0 .3 0 obstacle_center','1.3 0 .3 0 obstacle_front','1.6 -1.2 .3 0 detour','3 1 .3 0 goal','4.8 4.8 .3 0 unknown_corner']
 # Dense same-height footprint queries reveal newly admitted overlap instead of
 # testing only one convenient obstacle-center query.
 for x in np.arange(.6,2.61,.1):
  for y in np.arange(-1.1,1.11,.1):queries.append(f'{x:.3f} {y:.3f} .3 0 grid_{x:.3f}_{y:.3f}')
 (dest/'queries.txt').write_text('\n'.join(queries)+'\n')
 summary.append({'case':name,'selected':len(selected),'qualified':len(qualified),'added':len(rawkeys-oldkeys),'geometry_scoring_only':objects,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.iterdir() if p.is_file()}})
(HERE/'fixtures.json').write_text(json.dumps({'cases':summary,'claim':'Synthetic mapped-object acceptance fixtures; actual original-mounted first-hit sensor rays; no production change.'},indent=2)+'\n');print(json.dumps([{k:r[k] for k in ['case','selected','qualified','added']} for r in summary]))

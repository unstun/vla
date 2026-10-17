"""Independent original-mesh/torso overlap check at recorded poses; zero integration."""
from pathlib import Path
import bisect
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
from scipy.spatial.transform import Rotation

ROOT=Path('/data/sun/vla_mppi_20261009/stair_collision_replay_20261016')
BASE=ROOT.parent/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
RUN=ROOT.parent/'trials/v217_linux_full_attempt01/runs/v217_linux_full_attempt01'
sys.path.insert(0,str(BASE/'scripts'))
from scene_assets import building_mesh


def box_triangle_overlap(triangles,half):
    """Separating-axis test: three box axes, triangle normal and nine cross axes."""
    if not len(triangles):return np.zeros(0,dtype=bool)
    valid=np.all(triangles.max(axis=1)>=-half,axis=1)&np.all(triangles.min(axis=1)<=half,axis=1)
    edges=np.roll(triangles,-1,axis=1)-triangles
    axes=[np.cross(edges[:,0],edges[:,1])]
    for edge in range(3):
        for unit in np.eye(3):axes.append(np.cross(edges[:,edge],unit))
    for axis in axes:
        projection=np.einsum('nvi,ni->nv',triangles,axis)
        radius=np.abs(axis)@half
        valid &= (projection.min(axis=1)<=radius+1e-10)&(projection.max(axis=1)>=-radius-1e-10)
    return valid


def floor_hits(triangles,x,y,maximum):
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1])
    good=np.abs(den)>1e-10
    aa,bb,cc,dd=a[good],b[good],c[good],den[good]
    u=((bb[:,1]-cc[:,1])*(x-cc[:,0])+(cc[:,0]-bb[:,0])*(y-cc[:,1]))/dd
    v=((cc[:,1]-aa[:,1])*(x-cc[:,0])+(aa[:,0]-cc[:,0])*(y-cc[:,1]))/dd
    z=u*aa[:,2]+v*bb[:,2]+(1-u-v)*cc[:,2]
    z=z[(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)&(z<=maximum)]
    return sorted(set(np.round(z,7).tolist()))


def main():
    fixture=np.array([[[0,0,0],[.2,0,0],[0,.2,0]],[[2,0,0],[2,.2,0],[2,0,.2]],[[0,0,0],[2,0,0],[0,2,0]]],dtype=float)
    assert box_triangle_overlap(fixture,np.ones(3)*.5).tolist()==[True,False,True]
    vertices,faces,_=building_mesh();triangles=vertices[faces].astype(float)
    urdf=BASE/'inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface.urdf'
    torso=next(x for x in ET.parse(urdf).getroot().findall('link') if x.get('name')=='TORSO')
    boxes=[]
    for c in torso.findall('collision'):
        box=c.find('geometry/box')
        if box is None:continue
        origin=c.find('origin')
        xyz=np.fromstring(origin.get('xyz','0 0 0') if origin is not None else '0 0 0',sep=' ')
        rpy=np.fromstring(origin.get('rpy','0 0 0') if origin is not None else '0 0 0',sep=' ')
        boxes.append((xyz,Rotation.from_euler('xyz',rpy).as_matrix(),np.fromstring(box.get('size'),sep=' ')*.5))
    assert len(boxes)==2
    with zipfile.ZipFile(RUN/'raw_capture.zip') as z:
        raw=(RUN/'telemetry.jsonl').read_bytes() if (RUN/'telemetry.jsonl').exists() else z.read('telemetry.jsonl')
    telemetry=[json.loads(x) for x in raw.splitlines()];times=[x['physics_time_s'] for x in telemetry]
    frames=json.loads((ROOT/'input/frames.json').read_text());results=[]
    for f in frames:
        body=f['body_event']['data']['pose']['pose'];position=np.array([body['position'][k] for k in ('x','y','z')])
        rot=Rotation.from_quat([body['orientation'][k] for k in ('x','y','z','w')]).as_matrix()
        local=(triangles-position)@rot
        overlaps=[]
        for center,rotation,half in boxes:
            q=(local-center)@rotation
            overlaps.append(np.flatnonzero(box_triangle_overlap(q,half)).tolist())
        ti=bisect.bisect_right(times,f['time_s'])-1;t=telemetry[ti]
        heights=floor_hits(triangles,*position[:2],position[2])
        results.append({'frame':f['index'],'time_s':f['time_s'],'body_xyz':position.tolist(),
            'ground_hits_below_body_m':heights,'vertical_clearance_below_center_m':None if not heights else float(position[2]-heights[-1]),
            'torso_mesh_overlap_triangles':overlaps,'torso_mesh_clear':not any(overlaps),
            'telemetry_time_s':times[ti],'telemetry_age_s':f['time_s']-times[ti],
            'foot_forces_n':t['foot_forces_n'],'stance_mode':t['stance_mode'],
            'linear_speed_mps':float(np.linalg.norm(t['joint_qd'][:3])),
            'tilt_deg':float(np.degrees(np.arccos(np.clip(t['base_up_z'],-1,1))))})
    result={'method':'13-axis original torso-box versus original Building-triangle SAT; independent downward vertical triangle intersection',
        'mesh_triangles':len(triangles),'urdf_sha256':hashlib.sha256(urdf.read_bytes()).hexdigest(),
        'telemetry_sha256':hashlib.sha256(raw).hexdigest(),'sat_fixtures_passed':3,
        'physics_steps':0,'scope':'Torso collision and recorded foot support; not a newly executed trajectory or full leg-sweep proof.',
        'boxes':[{'center':x.tolist(),'rotation':r.tolist(),'half_size':h.tolist()} for x,r,h in boxes], 'frames':results}
    (ROOT/'output/geometry_check.json').write_text(json.dumps(result,indent=2)+'\n')
    for x in results:
        if x['frame']%10==0:print(json.dumps(x),flush=True)


if __name__=='__main__':main()

"""Read-only recorded foot geometry against the original Building triangles."""
from pathlib import Path
import hashlib
import json
import os
import sys

import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
TASK = Path('/data/sun/vla_mppi_20261009')
sys.path[:0] = [str(BASE/'versions/v127'), str(BASE/'versions/v40/physics'),
                str(BASE/'scripts')]
os.environ.setdefault('WARP_CACHE_PATH', str(TASK/'cache/posture_readonly'))
import warp as wp
wp.config.kernel_cache_dir = os.environ['WARP_CACHE_PATH']
wp.init()
wp.set_device('cpu')
import newton
from analyze_remote import Capture
from robot_scene_v40 import StairRobot


def heights(triangles, xy):
    a = triangles[:, 0, :2]
    u = triangles[:, 1, :2]-a
    v = triangles[:, 2, :2]-a
    d = np.linalg.det(np.stack([u, v], axis=2))
    mask = abs(d)>1e-8
    a, u, v, d, ts = a[mask], u[mask], v[mask], d[mask], triangles[mask]
    p = np.asarray(xy)-a
    s = (p[:,0]*v[:,1]-p[:,1]*v[:,0])/d
    t = (u[:,0]*p[:,1]-u[:,1]*p[:,0])/d
    inside = (s>=-1e-6)&(t>=-1e-6)&(s+t<=1+1e-6)
    z = ts[:,0,2]+s*(ts[:,1,2]-ts[:,0,2])+t*(ts[:,2,2]-ts[:,0,2])
    return sorted(set(np.round(z[inside], 5).tolist()))


def main():
    out = TASK/'results/v133_posture/geometry01'
    out.mkdir(parents=True, exist_ok=False)
    c = Capture(TASK/'trials/v133_candidate_attempt02/runs/v133_candidate_attempt02')
    robot = StairRobot(automatic_contact_capacity=True, model_device='cpu')
    states = c.json('video_states.json')
    telemetry = c.rows('telemetry.jsonl')
    bodies, kinds, scales = (getattr(robot.model, name).numpy() for name in
                              ('shape_body','shape_type','shape_scale'))
    transforms = robot.model.shape_transform.numpy()
    feet = []
    for leg in ('FL','FR','HL','HR'):
        matches = [i for i in range(robot.model.shape_count) if bodies[i]>=0 and
            robot.model.body_label[bodies[i]].rsplit('/',1)[-1]==leg+'_SHANK' and
            kinds[i]==int(newton.GeoType.SPHERE) and np.isclose(scales[i,0],.022)]
        assert len(matches)==1, (leg,matches)
        feet.append((leg,matches[0]))
    triangles = robot.building_vertices[robot.building_faces]
    samples = []
    for time_s in (35.9,36.5,36.9,37.1,37.3,37.5,37.9,38.5,40.,42.):
        s = min(states,key=lambda r:abs(r['physics_time_s']-time_s))
        r = min(telemetry,key=lambda r:abs(r['physics_time_s']-s['physics_time_s']))
        body_q = np.asarray(s['body_q'])
        record = {'time_s':s['physics_time_s'], 'telemetry_time_s':r['physics_time_s'],
            'position':r['body_sensor']['position'], 'mode':s['stance_mode'],
            'command':s['command'], 'tilt_deg':float(np.degrees(np.arccos(np.clip(r['base_up_z'],-1,1)))),
            'feet':[]}
        for idx,(leg,shape) in enumerate(feet):
            b = body_q[bodies[shape]]
            p = Rotation.from_quat(b[3:]).apply(transforms[shape,:3])+b[:3]
            record['feet'].append({'leg':leg,'xyz':p.tolist(),
                'vertical_surface_heights':heights(triangles,p[:2]),
                'force_n_previous_control_boundary':r['foot_forces_n'][idx]})
        samples.append(record)
    report = {'run':c.root.name,'samples':samples,'source':c.sources,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limits':['Recorded body transforms, not a resimulation.',
                  'Foot force is sampled at the preceding control boundary, not at the recorded video instant.',
                  'Vertical geometric intersections do not prove load bearing or reconstruct solver contacts.']}
    (out/'geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    fig,axes=plt.subplots(1,2,figsize=(12,6))
    for ax,indices in zip(axes,([1,3,5],[5,7,9])):
        area=triangles[(triangles[:,:,0].max(1)>6.7)&(triangles[:,:,0].min(1)<8.7)&
                       (triangles[:,:,1].max(1)>5)&(triangles[:,:,1].min(1)<6.8)&
                       (triangles[:,:,2].max(1)<5.2)&(triangles[:,:,2].min(1)>4.1)]
        pc=PolyCollection(area[:,:,:2],array=area[:,:,2].mean(1),cmap='terrain',alpha=.3,edgecolor='#555',linewidth=.2)
        ax.add_collection(pc)
        for index,color in zip(indices,('blue','orange','red')):
            s=samples[index];pts=np.array([f['xyz'] for f in s['feet']]);p=s['position']
            ax.scatter(pts[:,0],pts[:,1],color=color,s=25)
            ax.scatter([p[0]],[p[1]],color=color,marker='x',s=80,label=f"{s['time_s']:.2f}s, tilt {s['tilt_deg']:.1f}")
            for f in s['feet']:ax.annotate(f['leg'],f['xyz'][:2],fontsize=7,color=color)
        ax.set(xlim=(6.7,8.7),ylim=(5,6.8),xlabel='World x (m)',ylabel='World y (m)',aspect='equal')
        ax.legend();ax.grid(alpha=.2)
    fig.suptitle('v133 failed run: measured feet and original scene (read-only geometry)')
    fig.tight_layout();fig.savefig(out/'geometry.png',dpi=150)
    print(json.dumps({'output':str(out),'samples':samples}))


if __name__=='__main__':main()

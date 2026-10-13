"""Prepare ordered original-sensor diagnostics, never claim exact async replay."""
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import sys
import zipfile
import numpy as np

BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'versions/v177'))
from analyze_remote import Capture
TASK=Path('/data/sun/vla_mppi_20261009')
OUT=TASK/'replay_v177_stop_inputs02'


def numbers(xs):return ' '.join(format(float(x),'.17g') for x in xs)
def pose(d,optical=False):
    p=d['sensor_position' if optical else 'position'];w,x,y,z=d['sensor_quaternion' if optical else 'quaternion']
    return numbers([*p,x,y,z,w])+'\n'
def stamp(d):return d['sec']+d['nanosec']/1e9


def main():
    OUT.mkdir(exist_ok=False)
    cases=[('a01_g01',1,19.745777130,220,0.0,19.620845795),
           ('a03_g05',3,97.862846375,2009,0.0,97.777893066),
           ('a05_g01',5,31.304424286,372,.731357,31.114528656),
           ('a01_pause65',1,65.,1278,None,None),
           ('a01_pause76',1,76.,1293,None,None),
           ('a03_pause68',3,68.,1379,None,None),
           ('a01_g05_start',1,82.,None,None,None),
           ('a01_g06_start',1,85.,None,None,None),
           ('a01_g07_start',1,88.6,None,None,None),
           ('a01_g08_start',1,91.8,None,None,None)]
    # Original static inputs, verified by their frozen declaration.
    sys.path.insert(0,str(BASE/'runtime_sources/bridge/lite3_sim_bridge'))
    from pct_sim_clock_core import load_pinned_map,load_paired_elevations,selected_ground_points,load_dense_surface_points
    source=load_pinned_map(BASE/'inputs/new_building.pickle')
    paired=load_paired_elevations(BASE/'inputs/new_building_original_precision.npz',source)
    static=OUT/'static';static.mkdir()
    (static/'navigation.f32').write_bytes(selected_ground_points(source,paired_elevations=paired).astype('<f4').tobytes())
    (static/'surface.f32').write_bytes(load_dense_surface_points(BASE/'inputs/new_building_dense_surface.npy').astype('<f4').tobytes())
    shutil.copyfile(TASK/'trials/v177_full_candidate_attempt01/physical_floor.f32',static/'physical_floor.f32')
    ident=json.loads((BASE/'versions/v131/physical_floor_input.json').read_text())
    expected={'navigation.f32':ident['navigation_payload_sha256'],'surface.f32':ident['selected_surface_payload_sha256'],
              'physical_floor.f32':ident['files']['physical_floor.f32']['sha256']}
    for n,h in expected.items():assert hashlib.sha256((static/n).read_bytes()).hexdigest()==h
    for attempt in (1,3,5):
        tag=f'v177_full_candidate_attempt{attempt:02d}';root=TASK/'trials'/tag/'runs'/tag;c=Capture(root)
        events=c.rows('artifacts/reactive_observations.jsonl')
        records=json.loads((root/'sensor_manifest.json').read_text())
        published={r['timestamp_ns'] for r in c.rows('bridge_scan_audit.jsonl') if r['outcome']=='published_sequentially'}
        archive=zipfile.ZipFile(root/'raw_capture.zip')
        shared=OUT/f'scans_{attempt:02d}';shared.mkdir()
        for name,a,query,trajectory,phase,observed in cases:
            if a!=attempt:continue
            observed_selection='recorded controller validation source stamp'
            if observed is None:
                # Timer safety messages can stop while the controller keeps
                # checking independently. Do not mistake the last timer proof
                # for the map the controller actually used during a long stall.
                last_fresh=max((r for r in records if r['stamp_ns'] in published and r['stamp_ns']/1e9<=query-.15),key=lambda r:r['stamp_ns'])
                observed=last_fresh['stamp_ns']/1e9
                observed_selection='controlled fresh ordered prefix, latest published scan at least 150 ms before query; not original async revision'
            last=min(records,key=lambda r:abs(r['stamp_ns']/1e9-observed));assert abs(last['stamp_ns']/1e9-observed)<1e-6
            scans=[r for r in records if r['stamp_ns']<=last['stamp_ns'] and r['stamp_ns'] in published]
            out=OUT/name;out.mkdir();listing=[]
            for i,r in enumerate(scans):
                if not (shared/f'cloud_{i:05d}.f32').exists():
                    data=archive.read(r['file']);assert hashlib.sha256(data).hexdigest()==r['sha256']
                    pts=np.asarray(np.load(io.BytesIO(data),allow_pickle=False)['sensor_points'],dtype='<f4')
                    (shared/f'cloud_{i:05d}.f32').write_bytes(pts.tobytes())
                    (shared/f'body_{i:05d}.txt').write_text(pose(r['body_sensor']))
                    (shared/f'sensor_{i:05d}.txt').write_text(pose(r['body_sensor'],True))
                for filename in (f'cloud_{i:05d}.f32',f'body_{i:05d}.txt',f'sensor_{i:05d}.txt'):
                    (out/filename).symlink_to(Path('..')/shared.name/filename)
                listing.append(f'{i} {r["stamp_ns"]} body_{i:05d}.txt sensor_{i:05d}.txt cloud_{i:05d}.f32')
            (out/'scans.txt').write_text('\n'.join(listing)+'\n')
            body=max((r for r in events if r['event']=='body_pose_observer' and stamp(r['data']['header']['stamp'])<=query+1e-8),key=lambda r:stamp(r['data']['header']['stamp']))
            position=body['data']['pose']['pose']['position'];rotation=body['data']['pose']['pose']['orientation']
            (out/'query_body.txt').write_text(numbers([position[k] for k in 'xyz']+[rotation[k] for k in 'xyzw'])+'\n')
            (out/'query.txt').write_text(f'{round(query*1e9)} {round(stamp(body["data"]["header"]["stamp"])*1e9)}\n')
            for n in expected:(out/n).symlink_to(Path('../static')/n)
            curve=None
            if trajectory:
                curve=next(r['data'] for r in events if r['event']=='bspline' and r['data']['traj_id']==trajectory)
                pts=curve['pos_pts'];knots=curve['knots'];duration=knots[len(pts)]-knots[3]
                if phase is None:phase=duration # The observed long-held curve has reached its end.
                (out/'curve.txt').write_text(f'{len(pts)} {phase}\n'+numbers(knots)+'\n'+'\n'.join(numbers([p[k] for k in 'xyz']) for p in pts)+'\n')
            identity={'case':name,'run':tag,'query_s':query,'observation_s':observed,'trajectory':trajectory,'phase':phase,
                      'scans':len(scans),'body_observer':body,'curve':curve,
                      'source':c.sources,'static':expected,'observation_selection':observed_selection,
                      'scope':'Ordered published sensor prefix; asynchronous map batching and publication order are not reproduced.'}
            identity['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
            (out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n');print(name,len(scans),flush=True)
        archive.close()

if __name__=='__main__':main()

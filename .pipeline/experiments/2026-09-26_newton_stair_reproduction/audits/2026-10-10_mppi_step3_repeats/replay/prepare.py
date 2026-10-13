"""Prepare captured candidate curves and explicitly reconstructed map-query cases."""
from pathlib import Path
import hashlib
import io
import json
import re
import shutil
import sys
import zipfile
import numpy as np

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[2]
TASK=Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0,str(BASE/'versions/v127'))
from analyze_remote import Capture
OUT=TASK/'step3_repeats_replay/input'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def numbers(values):return ' '.join(format(float(x),'.17g') for x in values)
def curve_line(identifier,controls,knots):
    return f'{identifier} {len(controls)} {len(knots)} '+numbers([x for p in controls for x in p]+knots)
def pose_line(body,sensor=False):
    pos=body['sensor_position' if sensor else 'position'];w,x,y,z=body['sensor_quaternion' if sensor else 'quaternion']
    return numbers([*pos,x,y,z,w])+'\n'
def read_json(line,marker):return json.JSONDecoder().raw_decode(line.split(marker,1)[1].lstrip())[0]

def main():
    summary=json.loads((TASK/'results/step3_repeats/analysis/summary.json').read_text())
    tags=[r['run'] for r in summary['rows']]+['v127_baseline_attempt01','v127_candidate_attempt01']
    OUT.mkdir(parents=True,exist_ok=False)
    curve_rows=[];epochs=[];index=[];sources={};captures={}
    for tag in tags:
        root=TASK/'trials'/tag/'runs'/tag;capture=Capture(root);text=capture.read('nav2.log')
        captures[tag]=(root,capture,text)
        seed=None;last_curve=None;count=0
        for line_number,line in enumerate(text.splitlines(),1):
            if 'spline_seed_capture ' in line:seed=read_json(line,'spline_seed_capture ')
            if 'spline_curve_capture ' in line:
                record=read_json(line,'spline_curve_capture ');last_curve=record
                if seed is None:raise ValueError('Curve without preceding seed: '+tag)
                assert len(seed['derivatives'])==4
                identifier=len(curve_rows)
                row=curve_line(identifier,record['controls'],record['knots'])+' '+numbers(
                    seed['points'][0]+seed['points'][-1]+[x for p in seed['derivatives'] for x in p])
                curve_rows.append(row);count+=1
                index.append({'id':identifier,'run':tag,'line':line_number,'stage':record['stage']})
            if 'V59_TRAJECTORY_EPOCH ' in line and last_curve is not None:
                age=re.search(r'age_s=([-\d.]+)',line)
                if age:epochs.append((float(age[1]),last_curve['knots'][-4]-last_curve['knots'][3]))
            if 'final_spline_time_invalid ' in line:
                m=re.search(r'elapsed=([-\d.]+) duration=([-\d.]+)',line)
                if m:epochs.append((float(m[1]),float(m[2])))
        sources[tag]={'capture':capture.sources,'candidate_curves':count}
    assert curve_rows and epochs
    (OUT/'curves.txt').write_text('\n'.join(curve_rows)+'\n')
    (OUT/'epochs.txt').write_text('\n'.join(numbers(x) for x in epochs)+'\n')
    (OUT/'curve_index.json').write_text(json.dumps(index,separators=(',',':'))+'\n')
    # Predetermined critical selection: first fresh failed repeat from each arm,
    # plus the original failed candidate. Do not select based on replay verdicts.
    selected=[]
    for variant in ('baseline','candidate'):
        selected+=next(([r['run']] for r in summary['rows'] if r['variant']==variant and not r['arrived']),[])
    selected.append('v127_candidate_attempt01');selected=list(dict.fromkeys(selected))
    fixture=TASK/'fixed_curve_input'
    ground_identity=json.loads((BASE/'versions/v127/physical_floor_input.json').read_text())
    for name,key in [('navigation.f32','navigation_payload_sha256'),('surface.f32','selected_surface_payload_sha256')]:
        assert sha(fixture/name)==ground_identity[key]
    assert sha(fixture/'physical_floor.f32')==ground_identity['files']['physical_floor.f32']['sha256']
    for name in ('navigation.f32','surface.f32','physical_floor.f32'):shutil.copyfile(fixture/name,OUT/name)
    map_cases=[]
    for tag in selected:
        root,capture,text=captures[tag]
        observations=capture.rows('artifacts/reactive_observations.jsonl')
        curves={int(r['data']['traj_id']):r['data'] for r in observations if r['event']=='bspline'}
        telemetry=capture.rows('telemetry.jsonl')
        sensor_records=json.loads((root/'sensor_manifest.json').read_text())
        audit=[json.loads(x) for x in (root/'bridge_scan_audit.jsonl').read_text().splitlines() if x.strip()]
        published={r['timestamp_ns'] for r in audit if r['outcome']=='published_sequentially'}
        hits=[];phase=None
        for line_number,line in enumerate(text.splitlines(),1):
            if 'Controller native validation rejected:' in line:
                match=re.search(r' phase=([-\d.]+)',line);phase=float(match[1]) if match else None
            if 'SCAN evidence rejected now=' in line:
                fields={key:float(value) for key,value in re.findall(r'(now|observation_stamp|observation_age|active)=([-\d.]+)',line)}
                if phase is not None and fields.get('active',0)>0 and fields.get('observation_stamp',0)>0:
                    fields.update(phase=phase,line=line_number);hits.append(fields)
                phase=None
        for hit in hits[:2]:
            curve=curves.get(int(hit['active']))
            if curve is None:raise ValueError('Missing actual rejected curve')
            until=round(hit['observation_stamp']*1e9)
            scans=[r for r in sensor_records if r['stamp_ns']<=until and r['stamp_ns'] in published]
            assert scans and abs(scans[-1]['stamp_ns']-until)<=1,'Recorded observation not found'
            case_id=len(map_cases);directory=OUT/f'map_{case_id:02d}';directory.mkdir()
            listing=[]
            with zipfile.ZipFile(root/'raw_capture.zip') as archive:
                raw_manifest=json.loads((root/'raw_capture_manifest.json').read_text())
                for i,r in enumerate(scans):
                    data=archive.read(r['file']);assert hashlib.sha256(data).hexdigest()==r['sha256']==raw_manifest['members'][r['file']]['sha256']
                    points=np.asarray(np.load(io.BytesIO(data),allow_pickle=False)['sensor_points'],dtype='<f4')
                    assert points.shape==(r['sensor']['point_count'],3)
                    (directory/f'cloud_{i:05d}.f32').write_bytes(points.tobytes())
                    (directory/f'body_{i:05d}.txt').write_text(pose_line(r['body_sensor']))
                    (directory/f'sensor_{i:05d}.txt').write_text(pose_line(r['body_sensor'],True))
                    listing.append(f"{i} {r['stamp_ns']} body_{i:05d}.txt sensor_{i:05d}.txt cloud_{i:05d}.f32")
            (directory/'scans.txt').write_text('\n'.join(listing)+'\n')
            (directory/'curve.txt').write_text(curve_line(case_id,[[p[k] for k in ('x','y','z')] for p in curve['pos_pts']],curve['knots'])+'\n')
            now=hit['now'];actual_pose=max((r for r in telemetry if r['physics_time_s']<=now),key=lambda r:r['physics_time_s'])
            fixed_pose=max((r for r in telemetry if r['physics_time_s']<=hit['observation_stamp']+.2),key=lambda r:r['physics_time_s'])
            (directory/'actual_body.txt').write_text(pose_line(actual_pose['body_sensor']))
            (directory/'fixed_body.txt').write_text(pose_line(fixed_pose['body_sensor']))
            # The second/third queries are explicit clock counterfactuals on one
            # fixed recorded body/curve/map; source timestamps are never renewed.
            checks=[(now,actual_pose['physics_time_s'],'actual_body.txt','logged_phase'),
                    (hit['observation_stamp']+.249,fixed_pose['physics_time_s'],'fixed_body.txt','age_249ms'),
                    (hit['observation_stamp']+.251,fixed_pose['physics_time_s'],'fixed_body.txt','age_251ms')]
            (directory/'queries.txt').write_text('\n'.join(f'{round(t*1e9)} {round(body_t*1e9)} {name} {hit["phase"]:.17g} {label}' for t,body_t,name,label in checks)+'\n')
            map_cases.append({'id':case_id,'run':tag,'event':hit,'scans':len(scans),
                'actual_body_age_s':now-actual_pose['physics_time_s'],'phase_precision_s':1e-6,
                'scope':'Ordered bridge-published scan prefix reconstructed from exact captured points/poses. Original DDS take batching, discarded frames and asynchronous map revision are not restored.'})
        sources[tag]['replay_capture']=capture.sources
    (OUT/'maps.txt').write_text('\n'.join(f'map_{r["id"]:02d}' for r in map_cases)+'\n')
    record={'candidate_curves':len(curve_rows),'epochs':len(epochs),'map_cases':map_cases,'sources':sources,
            'ground_sha256':{n:sha(OUT/n) for n in ('navigation.f32','surface.f32','physical_floor.f32')},
            'input_sha256':{n:sha(OUT/n) for n in ('curves.txt','epochs.txt','curve_index.json','maps.txt')},
            'script_sha256':sha(Path(__file__))}
    (OUT/'identity.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'candidate_curves':len(curve_rows),'epochs':len(epochs),'map_cases':len(map_cases),'output':str(OUT)}),flush=True)
if __name__=='__main__':main()

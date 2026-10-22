"""Inspect recorded input order and latched body-admission failures; no physics."""
from pathlib import Path
import hashlib
import json
import math
import re
import sys

R=Path('/home/ubuntu/sun/vla_v288_20261020')
E=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
sys.path.insert(0,str(E/'versions/v196'))
from analyze_remote import Capture

def main():
    output=R/'evidence/input_order_audit01.json'
    assert not output.exists()
    rows=[]
    cohort=json.loads((R/'cohort/cases_manifest.json').read_text())
    for cid in cohort['physical_cases']:
        capture=Capture(R/'physical_runs'/f'v288_{cid}_attempt01/runs/v288_{cid}_attempt01')
        result=capture.json('result.json')
        sensors=capture.rows('sensor.jsonl')
        times=[r['sim_time_s'] for r in sensors]
        goal=next(c['goal'] for c in cohort['cases'] if c['case_id']==cid)
        errors=[math.dist(s['body_sensor']['position'][:2],goal['ground'][:2]) for s in sensors]
        near=[i for i,e in enumerate(errors) if e<=.25]
        index=min(range(len(errors)),key=errors.__getitem__)
        q=sensors[index]['body_sensor']['quaternion'];x,y,z,w=q
        yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
        center=dict(minimum_recorded_xy_error_m=min(errors),final_recorded_xy_error_m=errors[-1],
            samples_within_2cm=sum(e<=.02 for e in errors),samples_within_25cm=len(near),
            first_within_25cm_s=times[near[0]] if near else None,last_within_25cm_s=times[near[-1]] if near else None,
            minimum_error_time_s=times[index],yaw_error_at_minimum_xy_rad=math.atan2(math.sin(yaw-goal['yaw']),math.cos(yaw-goal['yaw'])),
            definition='Recorded XY proximity only; not a reconstruction of tracker capture state or final goal acceptance')
        text=capture.read('nav2.log');lines=text.splitlines()
        faults=[i for i,line in enumerate(lines) if 'regressed_body_source_stamp' in line]
        body=[line for line in lines if 'body admission failed:' in line]
        restored=re.findall(r'LBFGS_RESTORED stage=(\w+) return=(-\d+)',text)
        row=dict(case_id=cid,physics_steps=0,actual_recorded_physics_steps=result['physics_steps'],
            terminal_centering=center,failed_to_make_progress_mentions=text.count('Failed to make progress'),
            recorded_sensor_samples=len(times),recorded_sensor_time_regressions=sum(b<a for a,b in zip(times,times[1:])),
            recorded_sensor_time_duplicates=sum(b==a for a,b in zip(times,times[1:])),
            regressed_body_source_stamp_mentions=len(faults),all_body_admission_failures=len(body),
            gridmap_regressed_mentions=text.count('Live body admission failed: regressed_body_source_stamp'),
            fsm_regressed_mentions=text.count('FSM body admission failed: regressed_body_source_stamp'),
            first_regression_context=None if not faults else dict(one_based_line=faults[0]+1,
                lines=lines[max(0,faults[0]-8):faults[0]+8]),
            last_regression_line=None if not faults else lines[faults[-1]],
            restored_solver_returns={stage:{code:sum(s==stage and c==code for s,c in restored)
                for code in sorted({c for s,c in restored if s==stage})} for stage in sorted({s for s,c in restored})},
            finish=result.get('finish_request'),sources=capture.sources)
        rows.append(row)
        print(json.dumps({k:row[k] for k in ('case_id','recorded_sensor_samples','recorded_sensor_time_regressions','regressed_body_source_stamp_mentions','restored_solver_returns')}),flush=True)
    output.write_text(json.dumps(dict(version='v288',physics_steps=0,cases=rows,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        claim='Sensor capture order is not executor callback-entry order. A monotone recorded stream cannot alone prove which DDS take or lock wait reordered a callback. BodyTimeBuffer push permanently latches its first rejected stamp; source references and first actual error contexts are retained.'),indent=2)+'\n')

if __name__=='__main__':main()

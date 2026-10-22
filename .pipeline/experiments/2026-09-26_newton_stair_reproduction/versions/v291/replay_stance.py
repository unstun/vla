"""Replay measured v290 terminal joint inputs through both stance controllers.

No new physics: the candidate changes targets, never the measured trajectory.
Parent gate timing and source hashes are checked before interpreting differences.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import numpy as np
import stance_hold as candidate

EXPECTED = {
    'D07': 'f1bcfead24910480c6325bbbe46f1ad42416cffec1bf4964c3cc1dda7d969128',
    'CD12': 'f01e986ba87d7c46475224c86725acd9466f1a2ffc6897aff2ca92f7b7d3cbfd'}
STOP = {'D07':107.39260864257812,'CD12':115.18832397460938}
Q0 = np.tile([0.,-.8,1.6],4)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--raw-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    report={'new_physics_steps':0,'cases':{},'claim':'Recorded measured kinematics stay fixed; target changes are not physical drift reduction.'}
    for case in ('D07','CD12'):
        source=args.raw_root/f'v290_{case}_attempt01/runs/v290_{case}_attempt01/telemetry.jsonl'
        data=source.read_bytes();assert hashlib.sha256(data).hexdigest()==EXPECTED[case]
        rows=[json.loads(line) for line in data.splitlines()]
        controls={'parent':candidate.parent.StanceHold('auto',entry_kd='xfade2s'),
                  'candidate':candidate.StanceHold('auto',entry_kd='xfade2s',settling_capture=True)}
        entries={key:None for key in controls};targets={};gains={};records=[];previous_target={};variation={key:0. for key in controls}
        for previous,row in zip(rows,rows[1:]):
            t=previous['physics_time_s']
            if t<STOP[case]-1.0:continue
            values=dict(now_s=t,command=row['effective_command'],
                        joint_pos=np.asarray(previous['joint_q'][-12:]),joint_vel=np.asarray(previous['joint_qd'][-12:]),
                        policy_target=Q0+.25*np.asarray(row['action']),
                        linear_speed=float(np.linalg.norm(previous['body_sensor']['linear_world'])),
                        angular_speed=float(np.linalg.norm(previous['body_sensor']['angular_world'])),
                        tilt_deg=math.degrees(math.acos(np.clip(previous['base_up_z'],-1,1))),foot_forces=row['foot_forces_n'])
            outputs={}
            for key,control in controls.items():
                applied=targets.get(key,np.asarray(previous['target']))
                kp,kd=gains.get(key,(np.asarray(previous['motor_kp']),np.asarray(previous['motor_kd'])))
                out=control.update(candidate.HoldInput(**values,applied_target=applied,applied_kp=kp,applied_kd=kd))
                targets[key]=out.target.copy();gains[key]=(out.kp.copy(),out.kd.copy());outputs[key]=out
                if out.mode=='STAND_TRANSITION' and entries[key] is None:entries[key]=t
                if t>=STOP[case] and entries[key] is None and key in previous_target:
                    variation[key]+=float(np.sum(np.abs(out.target-previous_target[key])))
                previous_target[key]=out.target.copy()
            mask=controls['candidate'].settling_contact_mask
            if outputs['candidate'].mode=='STAND_SETTLING' and mask.any():
                assert not outputs['candidate'].policy_owns_joints
                assert all(row['foot_forces_n'][i]>candidate.HOLD_CONTACT_N for i in np.flatnonzero(mask))
                free=np.repeat(~mask,3)
                np.testing.assert_allclose(outputs['candidate'].target[free],values['policy_target'][free])
            if t>=STOP[case]:records.append({'time_s':t,'mode':outputs['candidate'].mode,
                'captured_legs':int(mask.sum()),'parent_owns':outputs['parent'].policy_owns_joints,
                'candidate_owns':outputs['candidate'].policy_owns_joints,
                'target_delta_l2_rad':float(np.linalg.norm(outputs['candidate'].target-outputs['parent'].target))})
        measured=next(r['physics_time_s'] for r in rows if r['physics_time_s']>=STOP[case] and r['stance_mode']=='STAND_TRANSITION')
        assert abs(entries['parent']-measured)<.041,(case,entries,measured)
        assert entries['candidate']==entries['parent'],'Unchanged measured inputs must retain original entry gate timing'
        assisted=[r for r in records if r['mode']=='STAND_SETTLING' and r['captured_legs']>0]
        assert assisted,(case,'no stopping assistance exercised')
        report['cases'][case]={'source_sha256':EXPECTED[case], 'measured_PD_entry_s':measured,
            'replayed_PD_entry_s':entries,'assisted_settling_samples':len(assisted),
            'maximum_captured_legs':max(r['captured_legs'] for r in assisted),
            'target_total_variation_rad_before_PD':variation,
            'maximum_target_difference_l2_rad':max(r['target_delta_l2_rad'] for r in records),
            'first_assisted_sample':assisted[0], 'all_free_leg_targets_equal_policy':True,
            'all_captured_legs_remain_supported':True}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()

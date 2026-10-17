"""Compare entry decisions on captured inputs; stop candidate at first transfer."""
from pathlib import Path
import json
import numpy as np
from capture import RAW, SEEDS, load_module, telemetry

HERE=Path(__file__).resolve().parent
rows,receipt=telemetry()
old=load_module(RAW/'executed_stance_hold.py','recorded_v206_hold')
new=load_module(HERE/'stance_hold.py','candidate_v208_hold')
pairs=[(a,b) for a,b in zip(rows,rows[1:]) if a['physics_time_s']>=SEEDS['zero_boundary']]
result={'fixture':receipt,'candidate_claim':'First transfer decision only; future physics differs after takeover.'}
for label,module in [('old',old),('candidate',new)]:
    hold=module.StanceHold('auto',entry_kd='xfade1s' if label=='old' else 'xfade2s')
    mismatches=[];entry=None;count=0
    for a,b in pairs:
        qd=np.array(a['joint_qd'],dtype=np.float32)
        x=module.HoldInput(now_s=a['physics_time_s'],command=b['effective_command'],
            joint_pos=np.array(b['observation'][9:21])+np.tile([0.,-.8,1.6],4),
            joint_vel=np.array(b['observation'][21:33])/.05,
            policy_target=b['target'],applied_target=a['target'],applied_kp=a['motor_kp'],applied_kd=a['motor_kd'],
            linear_speed=float(np.linalg.norm(qd[:3])),angular_speed=float(np.linalg.norm(qd[3:6])),
            tilt_deg=float(np.degrees(np.arccos(np.clip(a['base_up_z'],-1,1)))),foot_forces=b['foot_forces_n'])
        out=hold.update(x);count+=1
        if label=='old' and (out.mode!=b['stance_mode'] or out.reason!=b['stance_reason'] or abs(out.progress-b['stance_progress'])>1e-9):mismatches.append(x.now_s)
        if out.mode=='STAND_TRANSITION':entry=x.now_s;break
    result[label]=dict(samples=count,first_transfer_s=entry,final_mode=hold.mode,
                       recorded_mismatches=mismatches,counters=hold.counters)
assert not result['old']['recorded_mismatches'] and result['old']['first_transfer_s'] is None
assert result['candidate']['first_transfer_s'] is not None
(HERE/'results/components/recorded_input.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

"""Collect compact evidence from completed short probes; retain raw data remotely."""
from pathlib import Path
import csv
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
REMOTE=Path('/data/sun/vla_mppi_20261009/stance_v208')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records={}
for variant in ['old','candidate']:
    for seed in ['zero_boundary','quiet_blocked']:
        name=f'{variant}_{seed}_01';root=REMOTE/name
        out=HERE/'physical'/name;out.mkdir(parents=True,exist_ok=False)
        for filename in ['request.json','preflight.json','result.json']:
            shutil.copyfile(root/filename,out/filename)
        shutil.copyfile(REMOTE/(name+'.log'),out/'execution.log')
        initial=json.loads((root/'initial_state.json').read_text())
        records[name]=dict(result=json.loads((root/'result.json').read_text()),
                           raw_root=str(root),raw_files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))
                            for p in root.iterdir() if p.is_file()})
        with (out/'motion.csv').open('w') as target:
            writer=csv.writer(target)
            writer.writerow(['elapsed_s','mode','reason','policy_owns_joints','x','y','z','base_up_z',
                             'vx','vy','vz','wx','wy','wz','FL_N','FR_N','HL_N','HR_N'])
            for line in (root/'telemetry.jsonl').open():
                row=json.loads(line);b=row['body_sensor']
                writer.writerow([row['elapsed_s'],row['stance_mode'],row['stance_reason'],row['policy_owns_joints'],
                                  *b['position'],row['base_up_z'],*b['linear_world'],*b['angular_world'],*row['foot_forces_n']])
        records[name]['initial_physics_time_s']=initial['physics_time_s']
for seed in ['zero_boundary','quiet_blocked']:
    old=records[f'old_{seed}_01'];new=records[f'candidate_{seed}_01']
    assert old['raw_files']['initial_state.json']['sha256']==new['raw_files']['initial_state.json']['sha256']
    assert new['result']['passed']
    assert not old['result']['passed']
summary=dict(version='v208',status='two_initialized_state_pairs_passed',same_initial_bytes=True,
             new_full_route_runs=0,physics_steps=sum(r['result']['actual_physics_steps'] for r in records.values()),
             candidate_cases_passed=2,candidate_cases=2,records=records,
             boundary='Same-host short tests initialized from recorded states; not exact solver continuation or full navigation.')
(HERE/'physical_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='records'}))

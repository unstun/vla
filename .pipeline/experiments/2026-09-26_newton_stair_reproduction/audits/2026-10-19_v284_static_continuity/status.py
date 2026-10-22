"""Read-only compact status for the owned physical and analysis batch."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/sun/vla_exec/static_continuity_v284')
RAW = Path('/home/sun/vla_exec/physical_runs_v284')


def read(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


for name in ['authorized_continuation03', 'physical02_coordinator', 'after_physics01']:
    record = read(ROOT / (name + '.json'))
    if record:
        print(json.dumps(dict(coordinator=name, **{k: record.get(k) for k in
              ['stage', 'returncode', 'error']})))
for row in read(HERE / 'results/physical_batch_status.json') or []:
    cid = row['case_id']
    folder = RAW / f'v284_{cid}_attempt01/runs/v284_{cid}_attempt01'
    result = read(folder / 'result.json')
    output = dict(case=cid, stage=row['stage'])
    if result:
        output.update(physics_s=result['physics_duration_s'], physics_steps=result['physics_steps'],
                      terminal=(result.get('finish_request') or {}).get('backend_terminal_status'))
    else:
        latest = read(folder / 'backend_latest.json') or {}
        pose = latest.get('measurement_body_pose')
        if pose:
            output.update(observed_physics_s=pose['stamp_ns']*1e-9,
                          body=[pose[k] for k in ('x', 'y', 'z')])
    print(json.dumps(output))
analysis = read(HERE / 'results/analysis_batch_status.json')
if analysis:
    print(json.dumps(dict(analysis_cases=analysis)))

"""Derive display metrics without promoting a missing terminal handshake."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
VERSIONS = HERE.parent
V196 = VERSIONS / 'v196'
OUT = VERSIONS / 'v212/results'
RAW = Path('/data/sun/vla_mppi_20261009/trials/v212_linux_full_attempt01/runs/v212_linux_full_attempt01')
sys.path.insert(0, str(V196))
from analyze_remote import Capture
capture = Capture(RAW)
result = capture.json('result.json')
closed = capture.json('shared_state.json')
assert result['fallen'] is True and 'finish_request' not in result
assert closed['verified'] is False and closed['error'].startswith('FileNotFoundError')
finish_name = 'artifacts/external_episode/finish_request.json'
assert not (RAW / finish_name).exists()
assert finish_name not in capture.json('raw_capture_manifest.json')['members']
request = capture.json('episode_request.json')
current = capture.json('artifacts/external_episode/current_command.json')
assert current['run_id'] == RAW.name and current['run_epoch_ns'] == request['run_epoch_ns']
source = (V196 / 'analyze_remote.py').read_text()
needle = "'shared_state_verified':__import__('shared_state').verify_capture(capture)"
assert source.count(needle) == 1
source = source.replace(needle, "'shared_state_verified':False")
(OUT / 'executed_failure_metrics.py').write_text(source)
scope = {'__file__': str(V196 / 'analyze_remote.py'), '__name__': 'fall_display_analysis'}
exec(compile(source, str(OUT / 'executed_failure_metrics.py'), 'exec'), scope)
scope['analyze'](RAW, OUT, True)
path = OUT / 'metrics.json'
metrics = json.loads(path.read_text())
metrics.update(closed_shared_state_report=closed, physical_stop_reason='fallen',
    native_version='v212 event-triggered BT; v206 navigation core; v208 locomotion',
    analysis_boundary='Physical fall ended simulation before a Nav2 finish request. Shared terminal proof is false; timing/curves are display analysis only.')
path.write_text(json.dumps(metrics, indent=2)+'\n')
rows = capture.rows('telemetry.jsonl')
samples = []
for t in (45., 48., 50., 51., 52., 53., 53.5, 54., rows[-1]['physics_time_s']):
    row = min(rows, key=lambda r:abs(r['physics_time_s']-t))
    samples.append({key:row[key] for key in ('physics_time_s','joint_q','stance_mode','stance_reason',
        'policy_owns_joints','effective_command','body_sensor','base_up_z','foot_forces_n')})
proof = {'physical_result_fallen':True,'original_fall_gate':'base_up_z < 0.5',
    'first_recorded_below_gate_s':next(r['physics_time_s'] for r in rows if r['base_up_z']<.5),
    'final_base_up_z':rows[-1]['base_up_z'],'final_tilt_deg':float(np.degrees(np.arccos(np.clip(rows[-1]['base_up_z'],-1,1)))),
    'final_stance':rows[-1]['stance_mode'],'final_policy_owns_joints':rows[-1]['policy_owns_joints'],
    'source_terminal_status':None,'shared_terminal_proof':False,'samples':samples,
    'physics_changes':False,'navigation_rerun':False,
    'causal_boundary':'Observed physical fall during navigation. This single pair does not identify why the changed route history produced this outcome.'}
(OUT / 'fall_evidence.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({key:proof[key] for key in ('first_recorded_below_gate_s','final_base_up_z','final_tilt_deg','final_stance','shared_terminal_proof')}))

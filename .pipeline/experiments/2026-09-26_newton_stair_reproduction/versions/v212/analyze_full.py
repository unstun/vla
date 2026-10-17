"""Evaluate the closed v212 run using unchanged full-route acceptance rules."""
from pathlib import Path
import hashlib
import json
import math
import sys
import zipfile
import numpy as np

HERE = Path(__file__).resolve().parent
V196 = HERE.parent / 'v196'
RAW = Path('/data/sun/vla_mppi_20261009/trials/v212_linux_full_attempt01/runs/v212_linux_full_attempt01')
OUT = HERE / 'results'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(V196))
from analyze_remote import Capture, analyze
from launch import verify_sources


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


capture = Capture(RAW)
source = (V196 / 'verify_full_route.py').read_text()
before = "request['integration_version'] == 'v196'"
assert source.count(before) == 1
source = source.replace(before, "request['integration_version'] == 'v212'")
source = source.replace('v196 native / v196 shared-state Option B direct Nav2 + SCAN candidate on ',
                        'v212 event planning / v206 navigation core / v208 locomotion on ')
(OUT / 'executed_full_route_verifier.py').write_text(source)
scope = {'__file__': str(V196 / 'verify_full_route.py'), '__name__': 'v212_acceptance'}
exec(compile(source, str(OUT / 'executed_full_route_verifier.py'), 'exec'), scope)
try:
    gate = scope['verify'](RAW)
except Exception as error:
    gate = {'passed': False, 'error': repr(error), 'run': RAW.name}
write('full_route_verification.json', gate)
try:
    analyze(RAW, OUT, True)
    metrics = json.loads((OUT / 'metrics.json').read_text())
    metrics['native_version'] = 'Nav2 Foxy linux/amd64 v206; v208 locomotion adapter'
    write('metrics.json', metrics)
except Exception as error:
    write('analysis_error.json', {'error': repr(error)})
result = capture.json('result.json')
rows = capture.rows('telemetry.jsonl')
video = capture.json('video_states.json')
stance = capture.json('stance_status.json')
assert stance['source_sha256'] == '3974c8b3d641a80c3d3a2a54bed021df8494e0dc0fcf2428c7a9692c4e2c130c'
activation = capture.json('locomotion_activation.json')
assert activation['locomotion'] == 'v208'
pd = []
for row in reversed(rows):
    if row['stance_mode'] != 'FIXED_STAND' or row['policy_owns_joints']:
        break
    pd.append(row)
pd.reverse()
final = rows[-1]
original = json.loads((V196 / 'full_route_input.json').read_text())
target = original['goal_ground_xyz_m']
xyz = final['joint_q'][:3]
tail = {'continuous_final_fixed_pd_s': 0. if len(pd) < 2 else pd[-1]['physics_time_s'] - pd[0]['physics_time_s'],
        'first_final_fixed_pd_s': pd[0]['physics_time_s'] if pd else None,
        'samples': len(pd), 'final_stance_mode': final['stance_mode'],
        'final_policy_owns_joints': final['policy_owns_joints'],
        'final_effective_command': final['effective_command'],
        'final_linear_speed_mps': float(np.linalg.norm(final['body_sensor']['linear_body'])),
        'final_angular_speed_radps': float(np.linalg.norm(final['body_sensor']['angular_body'])),
        'final_foot_forces_n': final['foot_forces_n'],
        'final_kp': final['motor_kp'], 'final_kd': final['motor_kd'],
        'final_body_xyz_m': xyz, 'final_xy_error_m': math.dist(xyz[:2], target[:2]),
        'pd_gains_60_1_throughout_final_hold': bool(pd) and all(np.allclose(r['motor_kp'], 60.) and np.allclose(r['motor_kd'], 1.) for r in pd)}
write('final_hold.json', tail)
write('terminal_telemetry.json', final)
write('stance_status.json', stance)
write('locomotion_activation.json', activation)
archive = capture.json('raw_capture_manifest.json')
assert digest(RAW / 'raw_capture.zip') == archive['archive_sha256']
with zipfile.ZipFile(RAW / 'raw_capture.zip') as handle:
    assert handle.testzip() is None
    for name, item in archive['members'].items():
        data = handle.read(name)
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], name
process = capture.json('process.json')
retention = capture.json('retention_result.json')
summary = {'run': RAW.name, 'full_route_gate_passed': gate['passed'],
           'terminal_status': result.get('finish_request', {}).get('backend_terminal_status'),
           'fallen': result.get('fallen'), 'physics_duration_s': result['physics_duration_s'],
           'physics_steps': result['physics_steps'], 'final_hold': tail,
           'raw_root': str(RAW), 'archive_sha256': archive['archive_sha256'],
           'archive_members_verified': len(archive['members']), 'archive_bytes': (RAW / 'raw_capture.zip').stat().st_size,
           'process': process, 'retention_status': retention['status'],
           'source_identity_after': verify_sources(),
           'verifier_source_sha256': digest(V196 / 'verify_full_route.py'),
           'verifier_version_assertion_only_rebound': True, 'navigation_strategy_changed': 'only periodic global refresh replaced by goal/recovery triggers'}
write('outcome.json', summary)
print(json.dumps(summary), flush=True)

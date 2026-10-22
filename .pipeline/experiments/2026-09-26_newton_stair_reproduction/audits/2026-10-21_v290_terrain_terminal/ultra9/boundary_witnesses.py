"""Correlate negative sampled margins with unchanged recorded body/control state."""
from pathlib import Path
import csv
import hashlib
import json
import math
import sys

R = Path('/home/ubuntu/sun/vla_v290_20261021')
E = R / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
A = E / 'audits/2026-10-21_v290_terrain_terminal'
sys.path.insert(0, str(E / 'versions/v196'))
from analyze_remote import Capture

cases = json.loads((R / 'migration/physical_manifest01.json').read_text())['physical_cases']
rows = []
for case in cases:
    path = A / 'physical' / case / 'results/body_margins_with_raw.csv'
    samples = list(csv.DictReader(path.open()))
    negative = [s for s in samples if float(s['native_source_solid_margin_m']) < -1e-10]
    if not negative:
        rows.append(dict(case_id=case, source_solid_negative_samples=0))
        continue
    capture = Capture(R / f'physical_runs/v290_{case}_attempt01/runs/v290_{case}_attempt01')
    telemetry = capture.rows('telemetry.jsonl')
    scenario = capture.json('inputs/stair_scenario.json')
    goal = scenario['goal_ground_xyz_m']
    def witness(sample):
        time_s = float(sample['time_s'])
        index = min(range(len(telemetry)), key=lambda i: abs(telemetry[i]['physics_time_s'] - time_s))
        state = telemetry[index]
        delta = abs(state['physics_time_s'] - time_s)
        assert delta <= .021, (case, delta)
        body = state['body_sensor']
        w, x, y, z = body['quaternion']
        yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
        return dict(margin_sample=sample, telemetry_one_based_row=index+1,
            telemetry_physics_s=state['physics_time_s'], association_delta_s=delta,
            body_position=body['position'], body_yaw_rad=yaw,
            goal_xy_error_m=math.dist(body['position'][:2], goal[:2]),
            goal_yaw_error_rad=math.remainder(yaw-scenario['goal_yaw_rad'], 2*math.pi),
            effective_command=state['effective_command'], requested_command=state['requested_command'],
            stance_mode=state['stance_mode'], stance_reason=state['stance_reason'],
            command_reason=state['command_reason'], policy_owns_joints=state['policy_owns_joints'],
            measured_xy_speed_m_s=math.hypot(*body['linear_world'][:2]))
    rows.append(dict(case_id=case, source_solid_negative_samples=len(negative),
        requested_goal_ground=goal, requested_goal_yaw_rad=scenario['goal_yaw_rad'],
        first=witness(negative[0]), worst=witness(min(negative, key=lambda s: float(s['native_source_solid_margin_m']))),
        last=witness(negative[-1]), margin_csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        sources=capture.sources))
out = R / 'physical_return/boundary_witnesses.json'
assert not out.exists()
out.write_text(json.dumps(dict(physics_steps=0, cases=rows,
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    claim='Measured sampled body margins paired with nearest actual applied telemetry within21ms. First and worst crossings are separate; no inferred internal tracker phase, new physics, or interpolated state.'), indent=2) + '\n')
print('Recorded boundary witnesses extracted')

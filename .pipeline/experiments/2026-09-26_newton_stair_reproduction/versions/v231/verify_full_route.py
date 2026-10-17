"""Verify the original spatial route from a closed continuously recorded episode (Option B direct Nav2 + SCAN)."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from analyze_remote import Capture

HERE = Path(__file__).resolve().parent.parent / "v196"
BASE = HERE.parents[1]


def verify(root):
    capture = Capture(root)
    request = capture.json('episode_request.json')
    if request.get('building_route_profile') != 'historical_full':
        raise ValueError('Original spatial full route required; a corner episode is insufficient')
    original_path = BASE / 'inputs/historical_full_building.json'
    identity = json.loads((HERE / 'full_route_input.json').read_text())
    assert hashlib.sha256(original_path.read_bytes()).hexdigest() == identity['source_sha256']
    original = json.loads(original_path.read_text())
    scenario = capture.json('inputs/stair_scenario.json')
    for key in ['spawn_ground_xyz_m', 'spawn_yaw_rad', 'goal_ground_xyz_m']:
        assert scenario[key] == original[key] == identity[key], key
    assert request['integration_version'] == 'v231' and request['scene'] == 'building_full'
    rows = capture.json('video_states.json')
    proof = capture.json('initial_state.json')
    assert rows[0] == proof['frame'] and proof['physics_steps'] == 0
    times = np.array([r['physics_time_s'] for r in rows])
    poses = np.array([r['joint_q'][:3] for r in rows])
    assert times[0] == 0.0 and np.isfinite(poses).all() and np.all(np.diff(times) > 0)
    height = 0.14 if request['startup_mode'] == 'factory_pd' else original['spawn_body_height_m']
    expected = np.array(original['spawn_ground_xyz_m']) + [0.0, 0.0, height]
    assert np.max(np.abs(poses[0] - expected)) < 1e-5, 'Initial physical pose differs from original spawn'
    x, y, z, w = rows[0]['joint_q'][3:7]
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    yaw_error = math.atan2(math.sin(yaw - original['spawn_yaw_rad']), math.cos(yaw - original['spawn_yaw_rad']))
    assert abs(yaw_error) < 1e-5
    jumps = np.linalg.norm(np.diff(poses, axis=0), axis=1)
    assert float(jumps.max()) < 0.20, 'Discontinuous physical position in the recording'
    result = capture.json('result.json')
    assert not result.get('fallen', False)
    assert result['finish_request']['backend_terminal_status'] == 'FINISHED'
    from shared_state import verify_capture
    assert verify_capture(capture)
    driver = capture.json('artifacts/stair_driver_result.json')
    assert driver['execution_completed'] and driver['route_arrived']
    goal = next(r for r in driver['journal'] if r['event'] == 'goal_request')
    assert goal['payload']['target_ground_xyz'] == original['goal_ground_xyz_m']
    first_measured = goal['initial_snapshot']['measured']['base_xyz']
    assert math.dist(first_measured[:2], original['spawn_ground_xyz_m'][:2]) < 0.30
    final = driver['final_snapshot']
    assert final['control']['stance_mode'] == 'FIXED_STAND'
    assert final['control']['policy_owns_joints'] is False
    target = original['goal_ground_xyz_m']
    pilot = capture.json('inputs/pilot.json')
    final_xy_error = math.dist(poses[-1, :2], target[:2])
    assert final_xy_error <= pilot['goal_xy_tolerance_m']
    contract = json.loads((HERE / 'navigation_contract.json').read_text())
    final_height_error = abs(float(poses[-1, 2]) - target[2] - original['locomotion_reference_height_m'])
    assert final_height_error <= contract['z_goal_tolerance_m']
    route_messages = [r['data'] for r in capture.rows('artifacts/reactive_observations.jsonl') if r['event'] == 'pct_route']
    assert route_messages and all(r['poses'][-1]['pose'] == route_messages[0]['poses'][-1]['pose'] for r in route_messages)
    goal_q = route_messages[0]['poses'][-1]['pose']['orientation']
    goal_yaw = math.atan2(2 * (goal_q['w'] * goal_q['z'] + goal_q['x'] * goal_q['y']),
                          1 - 2 * (goal_q['y'] ** 2 + goal_q['z'] ** 2))
    x, y, z, w = rows[-1]['joint_q'][3:7]
    final_yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    final_yaw_error = abs(math.atan2(math.sin(final_yaw - goal_yaw), math.cos(final_yaw - goal_yaw)))
    assert final_yaw_error <= contract['yaw_goal_tolerance_rad'], 'Final held body outside requested yaw tolerance'
    return {'passed': True, 'profile': 'historical_full', 'run': root.name,
            'native_navigation': 'v231 execution / v230 navigation / v216 locomotion on ' + request['execution_host_platform'],
            'original_profile_sha256': identity['source_sha256'],
            'original_spawn_ground_xyz_m': original['spawn_ground_xyz_m'],
            'actual_initial_body_xyz_m': poses[0].tolist(), 'initial_yaw_error_rad': yaw_error,
            'original_goal_ground_xyz_m': target, 'actual_final_body_xyz_m': poses[-1].tolist(),
            'final_xy_error_m': final_xy_error, 'final_yaw_error_rad': final_yaw_error, 'final_height_error_m': final_height_error,
            'recorded_states': len(rows), 'all_physics_times_strictly_increasing': True,
            'largest_recorded_position_step_m': float(jumps.max()),
            'measured_recorded_body_path_m': float(jumps.sum()),
            'first_physics_time_s': float(times[0]), 'last_physics_time_s': float(times[-1]),
            'arrived': True, 'fallen': False, 'final_pd_hold': True, 'shared_state_verified': True,
            'source_files': capture.sources,
            'claim': 'One actual continuous original-start to original-goal episode; no repeated reliability claim.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-root', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify(args.run_root)
    except Exception as error:
        report = {'passed': False, 'profile': 'historical_full', 'run': args.run_root.name,
                  'error': repr(error), 'claim': 'Full-route gate failed; preserve this attempt.'}
    (args.run_root / 'full_route_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

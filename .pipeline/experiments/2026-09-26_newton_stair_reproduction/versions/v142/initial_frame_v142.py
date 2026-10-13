"""Record the real initial state without changing the audited startup algorithm."""
import hashlib
import json
import time


def state_digest(frame):
    state = {name: frame[name] for name in ('body_q', 'joint_q')}
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def capture_zero(robot, out):
    if robot.steps != 0 or robot.physics_time() != 0.0:
        raise ValueError('Zero-time recording requires the actual unstepped robot')
    frame = {
        'physics_time_s': robot.physics_time(), 'physics_steps': robot.steps,
        'body_q': robot.state.body_q.numpy().tolist(),
        'joint_q': robot.state.joint_q.numpy().tolist(),
        'command': [0.0, 0.0, 0.0], 'controller_phase': 'initial_state',
        'stance_mode': 'FACTORY', 'policy_owns_joints': False,
        'policy_calls': 0, 'navigation_ready': False,
        'recorded_before_first_physics_step': True,
    }
    before = state_digest(frame)
    after = state_digest({'body_q': robot.state.body_q.numpy().tolist(),
                          'joint_q': robot.state.joint_q.numpy().tolist()})
    if before != after or robot.steps != 0 or robot.physics_time() != 0.0:
        raise RuntimeError('Initial state capture changed the physical state')
    witness = {'passed': True, 'recorded_wall_monotonic_s': time.monotonic(),
               'physics_time_s': 0.0, 'physics_steps': 0,
               'state_sha256_before': before, 'state_sha256_after': after,
               'frame': frame, 'native_navigation_version': 'v139',
               'claim': 'Actual initialized state read before the first integration.'}
    (out / 'initial_state.json').write_text(json.dumps(witness, indent=2) + '\n')
    return frame


def initialize(robot, out):
    from factory_navigation_startup import initialize as audited_initialize
    first = capture_zero(robot, out)
    frames = [first] + audited_initialize(robot, out)
    (out / 'factory_video_states.json').write_text(json.dumps(frames) + '\n')
    return frames

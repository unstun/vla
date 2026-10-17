"""Check the actual graph-enabled physical entry and locomotion selection."""
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent / 'v40/physics'), str(BASE / 'scripts')]
import warp as wp
wp.config.kernel_cache_dir = os.environ['WARP_CACHE_PATH']
wp.init()
wp.set_device('cpu')
from newton_episode import activate
adapter = activate()
from robot_scene_v40 import StairRobot
robot = StairRobot(startup_mode='factory_pd', stance_hold=True, model_device='cpu',
                   use_solver_graph=True, automatic_contact_capacity=True)
assert isinstance(robot.stance, adapter.NewtonStance)
status = robot.stance.status()
assert status['source_sha256'] == adapter.SOURCE_SHA256
assert robot.steps == robot.policy_calls == 0
# Exact factory hold seed must remain uncapped despite the v208 return cap.
import numpy as np
seed = robot.state.joint_q.numpy()[robot.q_indices].astype(float)
robot.stance.boot_standing(seed)
np.testing.assert_array_equal(robot.target, seed)
np.testing.assert_array_equal(robot.motor_kp, np.full(12, 60.))
np.testing.assert_array_equal(robot.motor_kd, np.ones(12))
assert robot.stance.row['stance_mode'] == 'FIXED_STAND'
assert robot.stance.row['policy_owns_joints'] is False
assert robot.steps == robot.policy_calls == 0
report = {'passed': True, 'physics_steps': 0, 'policy_calls': 0,
          'actual_robot': 'v40 graph-enabled Warp CPU', 'adapter': str(adapter.__file__),
          'hold_source_sha256': status['source_sha256'], 'factory_seed_preserved': True}
(HERE / 'integration_preflight.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))

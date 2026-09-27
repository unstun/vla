"""Captured-state asynchronous sensing must preserve the exact ray sample."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
from flat_scene import FlatSceneRobot
from geometric_lidar import GeometricLidar


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    robot = FlatSceneRobot(None, obstacle_kind="none")
    lidar = GeometricLidar(robot, None, emitter_self_exclusion=True)
    robot.step([0.,0.,0.])
    pose = robot.body_and_sensor()
    captured = robot.model.state()
    captured.body_q.assign(robot.state.body_q)
    reference = lidar.scan(0, robot.physics_time())
    for _ in range(15):
        robot.step([.4,0.,0.])
    before = robot.state.body_q.numpy().copy()
    with ThreadPoolExecutor(max_workers=1) as executor:
        replay = executor.submit(lidar.scan, 0, .02, override_pose=pose, captured_state=captured).result(timeout=10.)
    live = lidar.scan(0, robot.physics_time())
    checks = {"captured_points_exact": np.array_equal(reference[0],replay[0]),
              "captured_world_exact": np.array_equal(reference[1],replay[1]),
              "physics_state_unchanged": np.array_equal(before,robot.state.body_q.numpy()),
              "later_live_sample_differs": not np.array_equal(reference[0],live[0]),
              "original_capture_not_restamped": pose != robot.body_and_sensor()}
    result={"checks":checks,"passed":all(checks.values()),
            "capture_physics_s":.02,"actual_physics_s":robot.physics_time(),
            "points_sha256":hashlib.sha256(reference[0].tobytes()).hexdigest(),
            "source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('geometric_lidar.py')]}}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

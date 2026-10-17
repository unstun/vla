"""Measure vertical robot bounds using Newton's existing collision broadphase."""
import json
import math
import os
from pathlib import Path
import sys

from materialize import BASE
sys.path.insert(0, str(BASE / "scripts"))
import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
import newton
from robot_scene import StairRobot


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    robot = StairRobot()
    rows = [json.loads(line) for line in (BASE / "runs/stair_native_walk_v2/telemetry.jsonl").open()]
    selected = rows[::50]
    samples = []
    mask = robot.model.shape_body.numpy() >= 0
    for row in selected:
        robot.state.joint_q.assign(np.asarray(row["joint_q"], dtype=np.float32))
        robot.state.joint_qd.assign(np.asarray(row["joint_qd"], dtype=np.float32))
        newton.eval_fk(robot.model, robot.state.joint_q, robot.state.joint_qd, robot.state)
        robot.collision_pipeline.collide(robot.state, robot.contacts)
        lower = robot.collision_pipeline.narrow_phase.shape_aabb_lower.numpy()[mask]
        upper = robot.collision_pipeline.narrow_phase.shape_aabb_upper.numpy()[mask]
        base_z = row["body_sensor"]["position"][2]
        samples.append({"state_sequence": row["state_sequence"], "physics_time_s": row["physics_time_s"],
                        "below_body_m": float(base_z - lower[:, 2].min()),
                        "above_body_m": float(upper[:, 2].max() - base_z)})
    result = {"physics_steps": robot.steps, "samples": samples,
              "inflation_z_up_m": math.ceil(max(s["below_body_m"] for s in samples) / .05) * .05,
              "inflation_z_down_m": math.ceil(max(s["above_body_m"] for s in samples) / .05) * .05,
              "claim": "Envelope of recorded poses, using native Newton AABBs including contact margins. Not a bound over every possible robot articulation. Obstacle inflation directions are opposite robot extents."}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

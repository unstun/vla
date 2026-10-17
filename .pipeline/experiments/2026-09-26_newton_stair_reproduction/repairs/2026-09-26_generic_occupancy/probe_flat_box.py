"""Qualify the native box scene and contact observer before navigation."""
import json
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
from flat_scene import FlatSceneRobot
from geometric_lidar import GeometricLidar


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    robot = FlatSceneRobot(None, obstacle_kind="box")
    lidar = GeometricLidar(robot, None, emitter_self_exclusion=True, visible_human_only=True)
    for _ in range(150):
        robot.step((0.,0.,0.))
    points, _, info, _, audit = lidar.scan(0, robot.physics_time())
    box_hits = int(((audit["shape_id"] == robot.human_contact_shape) & audit["keep"]).sum())
    checks = {"continuous_3000_steps": robot.steps == 3000,
              "every_physics_step_scored": robot.contact_scoring["physics_substeps_checked"] == robot.steps,
              "stance_has_no_obstacle_contact": robot.contact_scoring["touching_substeps"] == 0,
              "stance_upright": robot.telemetry()["base_up_z"] > .9,
              "native_rays_hit_box": box_hits > 20,
              "finite_unfiltered_cloud": len(points) > 1000 and np.isfinite(points).all(),
              "no_human_geometry": info["human_visibility"] == "absent" and info["human_hit_count_scoring_only"] == 0}
    # Separate frozen-geometry negative control; never used by navigation.
    negative = FlatSceneRobot(None, obstacle_kind="box")
    q = negative.state.joint_q.numpy();q[0]=1.6
    negative.state.joint_q.assign(q)
    newton.eval_fk(negative.model, negative.state.joint_q, negative.state.joint_qd, negative.state)
    negative.collision_pipeline.collide(negative.state, negative.contacts)
    negative._score_contacts(negative.state, negative.contacts)
    checks["frozen_overlap_is_detected"] = negative.contact_scoring["touching_substeps"] == 1
    checks = {name: bool(value) for name, value in checks.items()}
    result = {"checks":checks,"passed":all(checks.values()),"box_ray_hits":box_hits,
              "stance_scoring":robot.contact_scoring,"negative_scoring":negative.contact_scoring,
              "claim":"3-second continuous stance/sensing; separate no-step overlap scoring control. Not navigation."}
    (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not result["passed"]:
        raise AssertionError("Box scene qualification failed")


if __name__ == "__main__":
    main()

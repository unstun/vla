"""Bounded continuous stance and shared visible/contact mesh checks."""
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
from flat_scene import FlatSceneRobot, FlatStaticHuman
from geometric_lidar import GeometricLidar

out = Path(os.environ["NEWTON_RUN_DIR"])
human = FlatStaticHuman(out)
robot = FlatSceneRobot(human)
lidar = GeometricLidar(robot, human, emitter_self_exclusion=True, visible_human_only=True)
rows = []
for _ in range(150):
    robot.step((0., 0., 0.))
    row = robot.telemetry()
    row["actor_contacts_scoring_only"] = robot.actor_contact_count()
    rows.append(row)
points, _, info, _, _ = lidar.scan(0, 3.)
expected, _ = human.vertices(0.)
actual, _ = human.vertices(100.)
mesh = robot.model.shape_source[robot.human_contact_shape]
checks = {
    "continuous_three_seconds": robot.steps == 3000,
    "upright": min(row["base_up_z"] for row in rows) > .9,
    "no_actor_contact": all(row["actor_contacts_scoring_only"] == 0 for row in rows),
    "stationary_human_vertices_exact": bool(np.array_equal(expected, actual)),
    "contact_vertices_match_visible_skin": bool(np.array_equal(expected, mesh.vertices)),
    "contact_faces_match_visible_skin": bool(np.array_equal(mesh.indices, human.visible_faces.reshape(-1))),
    "measured_human_returns": info["human_hit_count_scoring_only"] > 10,
    "finite_cloud": bool(np.isfinite(points).all()),
}
(out / "telemetry.json").write_text(json.dumps(rows, indent=2) + "\n")
result = {"checks": checks, "passed": all(checks.values()), "last_pose": robot.body_and_sensor(), "sensor": info,
          "claim": "Flat scene stance and measured sensing only; no navigation result"}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
if not all(checks.values()):
    raise AssertionError("Flat scene physics/sensor qualification failed")

"""Two-second stance on original Building triangles, without planner motion."""
import json
import os
from pathlib import Path
import shutil
import time

import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")

from robot_scene import QUALIFIED, StairRobot

out = Path(os.environ["NEWTON_RUN_DIR"])
for name in ("robot_scene.py", "probe_stance.py", "scene_assets.py"):
    shutil.copyfile(Path(__file__).with_name(name), out / ("executed_" + name))
shutil.copyfile(QUALIFIED / "scripts/lite3_newton.py", out / "executed_lite3_newton.py")
robot = StairRobot()
(out / "model_identity.json").write_text(json.dumps({
    "joint_labels": robot.model.joint_label, "body_labels": robot.model.body_label,
    "shape_count": robot.model.shape_count, "sensor_mount": robot.sensor_mount.tolist(),
    "solver": "MuJoCo-Warp CPU with Newton triangle-mesh CollisionPipeline",
    "building_triangles": len(robot.building_faces)}, indent=2) + "\n")
started = time.monotonic()
rows = []
with (out / "telemetry.jsonl").open("w") as log:
    for i in range(100):
        robot.step((0., 0., 0.))
        row = robot.telemetry()
        row["body_sensor"] = robot.body_and_sensor()
        log.write(json.dumps(row) + "\n")
        log.flush()
        rows.append(row)
        if i % 25 == 0:
            print(row["physics_time_s"], row["joint_q"][:3], row["base_up_z"], row["contacts"], flush=True)
accepted = all(r["base_up_z"] > .9 and r["joint_q"][2] > .24 for r in rows[50:])
result = {"accepted": accepted, "physics_time_s": rows[-1]["physics_time_s"],
          "loop_wall_s": time.monotonic() - started, "final_body": rows[-1]["body_sensor"],
          "final_contacts": rows[-1]["contacts"], "final_up_z": rows[-1]["base_up_z"],
          "source": "original Building mesh and sensor-rig URDF; no ground-plane substitute"}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
if not accepted:
    raise RuntimeError("Original-scene stance failed")

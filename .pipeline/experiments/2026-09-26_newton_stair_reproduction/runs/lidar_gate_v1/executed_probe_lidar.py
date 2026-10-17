"""Sensor gate: analytic geometry, fixed-root skin motion and current scene hits."""
import json
import os
from pathlib import Path
import shutil

import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
import newton
from scene_assets import OfficialHuman
from robot_scene import StairRobot
from geometric_lidar import GeometricLidar

out = Path(os.environ["NEWTON_RUN_DIR"])
for name in ("scene_assets.py", "robot_scene.py", "geometric_lidar.py", "probe_lidar.py"):
    shutil.copyfile(Path(__file__).with_name(name), out / ("executed_" + name))
builder = newton.ModelBuilder()
builder.add_shape_box(-1, xform=wp.transform(wp.vec3(3., 0., 0.)), hx=1., hy=1., hz=1.)
model = builder.finalize(device="cpu")
distance = wp.zeros(1, dtype=float, device="cpu")
newton.intersect_ray(model, ray_origins=wp.array([[0, 0, 0]], dtype=wp.vec3),
                     ray_directions=wp.array([[1, 0, 0]], dtype=wp.vec3),
                     ray_worlds=wp.zeros(1, dtype=wp.int32), out_dist=distance, fast_math=False)
if abs(float(distance.numpy()[0]) - 2.) > 1e-6:
    raise RuntimeError("Analytic box first-hit distance mismatch")
robot = StairRobot()
human = OfficialHuman(out)
sensor = GeometricLidar(robot, human)
rows, saved = [], {}
for label, frame, root in (("skin_a", 0, (-5.3, 3., .08)), ("skin_b", 30, (-5.3, 3., .08)),
                           ("skin_repeat", 0, (-5.3, 3., .08)), ("translation", 0, (-4.8, 3., .08))):
    points, world, info, actor, audit = sensor.scan(0, 10.1, fixed_frame=frame, fixed_root=root)
    saved[label + "_ranges"] = audit["ranges"]
    saved[label + "_human"] = audit["actor_nearest"] & audit["keep"]
    rows.append({"label": label, **info})
both = np.isfinite(saved["skin_a_ranges"]) & np.isfinite(saved["skin_b_ranges"])
change = both & (np.abs(np.nan_to_num(saved["skin_a_ranges"], posinf=0) -
                       np.nan_to_num(saved["skin_b_ranges"], posinf=0)) > .005)
repeat_ok = np.array_equal(saved["skin_a_ranges"], saved["skin_repeat_ranges"])
if int(change.sum()) < 5 or not repeat_ok or int(saved["skin_a_human"].sum()) < 5:
    raise RuntimeError("Fixed-root skin sensing or fixed-frame control failed")
for i in range(3):
    points, world, info, actor, audit = sensor.scan(i, 0.)
    saved[f"scene_points_{i}"] = points
    rows.append({"label": f"scene_{i}", **info})
    if len(points) < 100:
        raise RuntimeError("No usable current Building sweep")
np.savez_compressed(out / "sensor_controls.npz", **saved)
result = {"accepted": True, "analytic_box_distance_m": float(distance.numpy()[0]),
          "fixed_root_skin_changed_ranges": int(change.sum()), "identical_frame_repeat": repeat_ok,
          "pattern": sensor.pattern.identity(), "controls": rows,
          "claim": "Geometric ray/skin sensor evidence; no RTX or intensity equivalence claim."}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)

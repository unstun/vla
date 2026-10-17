"""Sensor gate: analytic geometry, fixed-root skin motion and current scene hits."""
import json
import os
from pathlib import Path
import shutil

import numpy as np
import mujoco
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
import newton
from scene_assets import OfficialHuman, verify_inputs
from robot_scene import StairRobot
from geometric_lidar import GeometricLidar, sensor_view, EXCLUSION_SOURCE

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
source_identity = verify_inputs()
physical_flags = robot.model.shape_flags.numpy().copy()
sensor = GeometricLidar(robot, human, emitter_self_exclusion=True)
np.testing.assert_array_equal(robot.model.shape_flags.numpy(), physical_flags)
changed_flags = np.flatnonzero(sensor.sensor_model.shape_flags.numpy() != physical_flags)
np.testing.assert_array_equal(np.sort(changed_flags), np.sort(sensor.emitter_shapes))

# Compare the selected convention with the upstream native API. A distinct
# robot part or an external near occluder must still win over the background.
exclusion_controls = []
for label, x, half in (("background", 2.0, .1), ("other_robot_part", .4, .05),
                        ("external_inside_minimum_range", .07, .01)):
    xml = f'''<mujoco><worldbody>
      <body name="emitter"><geom name="housing" type="sphere" size=".025"/></body>
      <body name="occluder" pos="{x} 0 0"><geom type="box" size="{half} .1 .1"/></body>
      <geom type="box" pos="3 0 0" size=".1 .1 .1"/>
    </worldbody></mujoco>'''
    native = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(native)
    mujoco.mj_forward(native, data)
    native_id = np.zeros(1, dtype=np.int32)
    native_distance = mujoco.mj_ray(native, data, np.zeros(3), np.array([1., 0., 0.]),
                                   None, True, native.body("emitter").id, native_id)
    control_builder = newton.ModelBuilder()
    emitter = control_builder.add_shape_sphere(-1, radius=.025)
    occluder = control_builder.add_shape_box(-1, xform=wp.transform(wp.vec3(x, 0., 0.)),
                                            hx=half, hy=.1, hz=.1)
    control_builder.add_shape_box(-1, xform=wp.transform(wp.vec3(3., 0., 0.)), hx=.1, hy=.1, hz=.1)
    control_model = control_builder.finalize(device="cpu")
    view = sensor_view(control_model, control_model.state(), [emitter])
    hit = wp.zeros(1, dtype=wp.int32, device="cpu")
    newton.intersect_ray(view, ray_origins=wp.array([[0, 0, 0]], dtype=wp.vec3),
                         ray_directions=wp.array([[1, 0, 0]], dtype=wp.vec3),
                         ray_worlds=wp.zeros(1, dtype=wp.int32), out_dist=distance,
                         out_shape_id=hit, fast_math=False)
    measured = float(distance.numpy()[0])
    if abs(measured - native_distance) > 1e-6 or int(hit.numpy()[0]) != occluder:
        raise RuntimeError(f"Upstream exclusion / preserved occlusion mismatch: {label}")
    exclusion_controls.append({"case": label, "newton_range_m": measured,
                               "native_mujoco_range_m": float(native_distance),
                               "valid_return": measured >= .1})

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
(out / "skin_controls.json").write_text(json.dumps({"changed": int(change.sum()), "repeat_ok": repeat_ok,
                                                   "rows": rows}, indent=2) + "\n")
np.savez_compressed(out / "partial_sensor_controls.npz", **saved)
print(json.dumps({"changed": int(change.sum()), "repeat_ok": repeat_ok, "rows": rows}, indent=2), flush=True)
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
          "exclusion_source": EXCLUSION_SOURCE, "exclusion_controls": exclusion_controls,
          "physical_render_flags_unchanged": True,
          "excluded_original_sensor_shapes": sensor.emitter_shapes,
          "other_robot_near_occlusion_retained": any(row["near_hit_count"] > 0 for row in rows),
          "fixed_root_skin_changed_ranges": int(change.sum()), "identical_frame_repeat": repeat_ok,
          "pattern": sensor.pattern.identity(), "controls": rows,
          "claim": "Geometric ray/skin sensor evidence; no RTX or intensity equivalence claim."}
result["analytic_box_distance_m"] = 2.0
if not result["other_robot_near_occlusion_retained"]:
    raise RuntimeError("Other robot near occlusion disappeared")
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)

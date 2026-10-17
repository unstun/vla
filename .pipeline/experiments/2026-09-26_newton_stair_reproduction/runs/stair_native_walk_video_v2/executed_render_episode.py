"""Render recorded Newton body states; never synthesize a robot trajectory.

Uses pinned Newton ViewerGL log_state/log_mesh/log_instances/log_lines APIs,
original UsdSkel vertices/UVs and the official base-color atlas. Rendering is
after physics execution so video capture cannot change control-loop timing.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pxr import UsdGeom
from scipy.interpolate import BSpline
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
import newton

from scene_assets import BASE, OfficialHuman, verify_inputs
from robot_scene import StairRobot


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run", required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    source = BASE / "runs" / args.source_run
    if source.parent != BASE / "runs" or not (source / "video_states.json").is_file():
        raise ValueError("A recorded experiment run is required")
    out = Path(os.environ["NEWTON_RUN_DIR"])
    verify_inputs()
    rows = json.loads((source / "video_states.json").read_text())
    if args.limit is not None:
        rows = rows[:args.limit]
    if not rows:
        raise ValueError("No recorded physics frames")
    for name in ("render_episode.py", "scene_assets.py", "robot_scene.py"):
        shutil.copyfile(Path(__file__).with_name(name), out / ("executed_" + name))
    robot = StairRobot()
    human = OfficialHuman(out)
    uvs = []
    for path, _, _, faces in human.meshes:
        primvar = UsdGeom.PrimvarsAPI(human.stage.GetPrimAtPath(path)).GetPrimvar("st0")
        if not primvar or primvar.GetInterpolation() != "faceVarying":
            raise ValueError("Official face-varying UV contract changed")
        values = np.asarray(primvar.ComputeFlattened(), dtype=np.float32)
        if len(values) != faces.size:
            raise ValueError("Official UV/face count mismatch")
        uvs.append(values)
    corners = human.faces.reshape(-1)
    indices = wp.array(np.arange(len(corners), dtype=np.int32), dtype=wp.int32, device="cpu")
    uv = wp.array(np.concatenate(uvs), dtype=wp.vec2, device="cpu")
    texture = str(BASE / "inputs/official_human/textures/male_adult_police_04_BaseColor.png")
    points = wp.empty(len(corners), dtype=wp.vec3, device="cpu")
    xforms = wp.array([wp.transform_identity()], dtype=wp.transform, device="cpu")
    scales = wp.array([[1., 1., 1.]], dtype=wp.vec3, device="cpu")
    colors = wp.array([[1., 1., 1.]], dtype=wp.vec3, device="cpu")
    # Pinned example_basic_viewer: roughness, metallic, checker, texture_enable.
    materials = wp.array([[.65, 0., 0., 1.]], dtype=wp.vec4, device="cpu")
    curves = []
    backend_states = [json.loads(line) for line in (source / "backend_states.jsonl").read_text().splitlines()]
    observations = source / "artifacts/reactive_observations.jsonl"
    if observations.exists():
        for line in observations.open():
            row = json.loads(line)
            if row["event"] == "bspline" and row["clock_ns"] is not None:
                curves.append(row)
    frames = out / "frames"
    frames.mkdir()
    manifest = []
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 23)
    viewer = newton.viewer.ViewerGL(width=1280, height=720, vsync=False, headless=True)
    try:
        viewer.set_model(robot.model)
        viewer.camera.fov = 80.0
        for i, row in enumerate(rows):
            t = row["physics_time_s"]
            robot.state.body_q.assign(np.asarray(row["body_q"], dtype=np.float32))
            robot.state.joint_q.assign(np.asarray(row["joint_q"], dtype=np.float32))
            base_position = np.asarray(row["joint_q"][:3])
            # Original initial-heading camera condition, using actual base pose.
            camera = robot.scenario["camera"]
            yaw = robot.scenario["spawn_yaw_rad"]
            forward = np.array([math.cos(yaw), math.sin(yaw), 0.])
            position = base_position - camera["trail_m"] * forward + np.array([0., 0., camera["height_m"]])
            target = base_position + camera["look_ahead_m"] * forward + np.array([0., 0., -camera["look_down_m"]])
            viewer.set_camera(tuple(position), pitch=-20, yaw=0)
            viewer.camera.look_at(tuple(target))
            vertices, actor = human.vertices(t)
            points.assign(vertices[corners])
            viewer.begin_frame(t)
            viewer.log_state(robot.state)
            viewer.log_mesh("official_human", points, indices, uvs=uv, texture=texture,
                            backface_culling=False, dynamic=True, hidden=True)
            viewer.log_instances("official_human_instance", "official_human", xforms, scales, colors, materials)
            available = [c for c in curves if c["clock_ns"] <= round(t * 1e9)]
            if available:
                curve = available[-1]["data"]
                control = np.array([[p["x"], p["y"], p["z"]] for p in curve["pos_pts"]])
                knots = np.asarray(curve["knots"])
                order = int(curve["order"])
                if len(knots) != len(control) + order + 1:
                    raise ValueError("Native spline knot/control contract mismatch")
                spline = BSpline(knots, control, order, extrapolate=False)
                curve_points = spline(np.linspace(knots[order], knots[-order-1], 150)).astype(np.float32)
                viewer.log_lines("native_curve", wp.array(curve_points[:-1], dtype=wp.vec3),
                                 wp.array(curve_points[1:], dtype=wp.vec3), colors=(.05, .8, 1.))
            viewer.end_frame()
            rgb = viewer.get_frame(render_ui=False).numpy()
            frame = Image.fromarray(rgb)
            draw = ImageDraw.Draw(frame)
            draw.rectangle((0, 0, frame.width, 96), fill=(15, 20, 29))
            draw.text((22, 12), f"Lite3 | Newton CPU | recorded physics  {t:05.2f} s", font=font, fill=(242, 245, 250))
            command = row["command"]
            draw.text((22, 53), f"Applied vx/vy/wz: {command[0]:+.3f} / {command[1]:+.3f} / {command[2]:+.3f}   |   native curve messages: {len(available)}", font=small, fill=(153, 216, 239))
            draw.rectangle((0, frame.height-43, frame.width, frame.height), fill=(15, 20, 29))
            observed_states = [s for s in backend_states if s["sim_time_s"] <= t]
            status = "waiting for original driver"
            if observed_states:
                backend = observed_states[-1]["data"]
                if backend.get("terminal_results"):
                    terminal = backend["terminal_results"][-1]
                    status = terminal["status"] + " (" + terminal["cause"] + ")"
                elif backend.get("jobs"):
                    status = "active goal"
            draw.rectangle((0, frame.height-76, frame.width, frame.height), fill=(15, 20, 29))
            draw.text((22, frame.height-68), "Navigation: " + status, font=small, fill=(255, 207, 128))
            draw.text((22, frame.height-35), "Original Building + animated human | geometric LiDAR | rendered from actual recorded physics", font=small, fill=(220, 225, 235))
            path = frames / f"{i:06d}.png"
            frame.save(path)
            manifest.append({"file": str(path.relative_to(out)), "sha256": digest(path),
                             "physics_time_s": t, "actor_clip": actor["clip"], "actor_frame": actor["frame"],
                             "navigation_status": status,
                             "shape": list(rgb.shape)})
            if i % 50 == 0:
                print("Rendered", i, "physics", t, flush=True)
    finally:
        viewer.close()
    video = out / "newton_stair_recorded.mp4"
    command = ["/opt/homebrew/bin/ffmpeg", "-nostdin", "-v", "error", "-framerate", "12.5",
               "-i", str(frames / "%06d.png"), "-vf", "scale=1280:720", "-c:v", "libx264",
               "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]
    subprocess.run(command, check=True, timeout=90)
    (out / "frames.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "result.json").write_text(json.dumps({"source_run": args.source_run,
        "source_states_sha256": digest(source / "video_states.json"), "video": str(video),
        "video_sha256": digest(video), "frames": len(rows), "fps": 12.5,
        "first_physics_s": rows[0]["physics_time_s"], "last_physics_s": rows[-1]["physics_time_s"],
        "display_camera_fov_degrees": 80.0,
        "render_only_no_physics_steps": robot.steps == 0,
        "claim": "Replay visualization of actual logged physics; no synthesized robot trajectory or live-render timing claim"}, indent=2) + "\n")


if __name__ == "__main__":
    main()

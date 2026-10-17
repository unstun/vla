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
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pxr import Usd, UsdGeom, UsdShade
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


def viewer_color(linear):
    """Invert the pinned Newton shader's pow(ObjectColor, 2.2) conversion."""
    color = np.asarray(linear, dtype=np.float64)
    if color.shape != (3,) or not np.isfinite(color).all() or np.any(color < 0) or np.any(color > 1):
        raise ValueError("Expected a bounded linear USD color")
    return np.power(color, 1. / 2.2).tolist()


def prepare_robot_appearance(robot):
    """Resolve original materials and display orientation of mirrored visuals."""
    from newton._src.utils.mesh import load_meshes_from_file
    import trimesh
    reference = BASE / "references/2026-09-26_lite3_visual_materials"
    provenance = json.loads((reference / "source.json").read_text())
    for record in provenance["files"]:
        if digest(reference / record["path"]) != record["sha256"]:
            raise ValueError("Manufacturer material reference changed")
    source = reference / "Lite3/usd/configuration/Lite3_base.usd"
    stage = Usd.Stage.Open(str(source))
    base_links = ET.parse(reference / "Lite3/urdf/Lite3.urdf").getroot()
    rig = BASE / "inputs/sensor_rig"
    local_links = ET.parse(rig / "lite3_pro_sensor_rig_real_with_interface.urdf").getroot()
    before = robot.model.shape_color.numpy().copy()
    colors = before.copy()
    flags = robot.model.shape_flags.numpy()
    bodies = robot.model.shape_body.numpy()
    records = []
    for source_link in base_links.findall("link"):
        if not source_link.findall("visual"):
            continue
        name = source_link.get("name")
        local_link = local_links.find("link[@name='" + name + "']")
        if local_link is None or len(local_link.findall("visual")) != 1:
            raise ValueError("Expected one original base visual: " + name)
        visual = local_link.find("visual")
        mesh = visual.find("geometry/mesh")
        scale = [float(v) for v in mesh.get("scale", "1 1 1").split()]
        expected = load_meshes_from_file(str(rig / mesh.get("filename")), scale=scale, maxhullvert=None)
        if len(expected) != 1:
            raise ValueError("Expected a single original robot mesh: " + name)
        matches = [i for i, shape in enumerate(robot.model.shape_source)
            if bodies[i] >= 0 and robot.model.body_label[bodies[i]].rsplit("/", 1)[-1] == name
            and flags[i] & int(newton.ShapeFlags.VISIBLE) and isinstance(shape, newton.Mesh)
            and np.array_equal(shape.vertices, expected[0].vertices)
            and np.array_equal(shape.indices, expected[0].indices)]
        if len(matches) != 1:
            raise ValueError("Ambiguous original robot visual: " + name)
        prototype = stage.GetPrimAtPath("/visuals/" + name)
        material_meshes = [p for p in Usd.PrimRange(prototype) if p.IsA(UsdGeom.Mesh)]
        if len(material_meshes) != 1:
            raise ValueError("Expected one manufacturer visual material: " + name)
        material = UsdShade.MaterialBindingAPI(material_meshes[0]).ComputeBoundMaterial()[0]
        shader = material.ComputeSurfaceSource("mdl")[0]
        if not shader:
            raise ValueError("Manufacturer material shader missing: " + name)
        source_color = list(shader.GetInput("diffuse_color_constant").Get())
        authored = visual.find("material/color")
        selected = source_color if authored is None else [float(x) for x in authored.get("rgba").split()[:3]]
        index = matches[0]
        colors[index] = viewer_color(selected)
        orientation = None
        if not np.array_equal(np.asarray(scale), np.ones(3)):
            # The pinned URDF loader baked scale into vertices only. Use the
            # upstream mesh transform to keep winding and normals consistent.
            # This copy belongs to recorded-state rendering, never collision I/O.
            if flags[index] & int(newton.ShapeFlags.COLLIDE_SHAPES | newton.ShapeFlags.COLLIDE_PARTICLES):
                raise ValueError("Refusing to adapt collision geometry for display: " + name)
            if not np.array_equal(np.abs(scale), np.ones(3)):
                raise ValueError("Unqualified non-unit robot visual scale: " + name)
            original = robot.model.shape_source[index]
            transformed = trimesh.load(rig / mesh.get("filename"), force="mesh")
            # Materialize source normals before Trimesh updates its cache.
            transformed.vertex_normals
            transformed.apply_transform(np.diag([*scale, 1.]))
            points = np.asarray(transformed.vertices, dtype=np.float32)
            triangles = np.asarray(transformed.faces, dtype=np.int32)
            if not np.array_equal(points, original.vertices):
                raise ValueError("Display transform would change robot vertices: " + name)
            if not np.array_equal(np.sort(triangles, axis=1),
                                  np.sort(original.indices.reshape(-1, 3), axis=1)):
                raise ValueError("Display transform would change geometric triangles: " + name)
            normals = np.asarray(transformed.vertex_normals, dtype=np.float32)
            robot.model.shape_source[index] = newton.Mesh(
                points, triangles.reshape(-1), normals=normals, uvs=original.uvs,
                compute_inertia=False, is_solid=original.is_solid, maxhullvert=original.maxhullvert,
                color=original.color, opacity=original.opacity, texture=original.texture,
                roughness=original.roughness, metallic=original.metallic,
                texture_transform=original.texture_transform)
            orientation = {"upstream": "trimesh.Trimesh.apply_transform",
                "trimesh_version": trimesh.__version__, "source_scale": scale,
                "winding_reversed": bool(np.prod(scale) < 0),
                "vertices_unchanged": True, "geometric_triangles_unchanged": True,
                "display_indices_sha256": hashlib.sha256(triangles.tobytes()).hexdigest(),
                "display_normals_sha256": hashlib.sha256(normals.tobytes()).hexdigest()}
        records.append({"link": name, "shape": index, "original_color": before[index].tolist(),
            "selected_linear_color": selected, "viewer_color": colors[index].tolist(),
            "material_source": "manufacturer USD" if authored is None else "original URDF",
            "manufacturer_material": str(material.GetPath()),
            "original_mesh_sha256": digest(rig / mesh.get("filename")),
            "display_orientation": orientation})
    if len(records) != 13:
        raise ValueError("Expected torso plus twelve original leg visuals")
    selected_shapes = {r["shape"] for r in records}
    untouched = [i for i in range(robot.model.shape_count) if i not in selected_shapes]
    if not np.array_equal(before[untouched], colors[untouched]):
        raise AssertionError("Sensor or scene color changed during robot adaptation")
    robot.model.shape_color.assign(colors)
    return {"repository": provenance["repository"], "commit": provenance["commit"],
        "license": "BSD-3-Clause", "source_usd_sha256": digest(source), "base_visuals": records,
        "sensor_colors_unchanged": True,
        "scope": "Original-link materials and mirrored visual orientation; positions and geometric triangles unchanged; no physics edits"}


def prepare_appearance(robot, human, out, *, visible_sensor_meshes=False):
    """Adapt authored USD albedo/visibility only; keep the recorded ray scene."""
    robot_appearance = prepare_robot_appearance(robot)
    stage = Usd.Stage.Open(str(BASE / "inputs/building.usda"))
    shader = UsdShade.Shader(stage.GetPrimAtPath("/Building/Material/Shader"))
    building_color = list(shader.GetInput("diffuseColor").Get())
    colors = robot.model.shape_color.numpy().copy()
    colors[robot.building_shape] = viewer_color(building_color)
    robot.model.shape_color.assign(colors)
    robot.model.shape_source[robot.building_shape].roughness = float(shader.GetInput("roughness").Get())
    parts, records, textures = [], [], {}
    offset = 0
    for path, _, original_points, faces in ([] if human is None else human.meshes):
        prim = human.stage.GetPrimAtPath(path)
        visibility = str(UsdGeom.Imageable(prim).ComputeVisibility())
        material = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
        shader = material.ComputeSurfaceSource("mdl")[0]
        if not shader:
            raise ValueError("Missing original OmniPBR shader: " + path)
        tint_value = shader.GetInput("diffuse_tint").Get()
        tint = [1., 1., 1.] if tint_value is None else list(tint_value)
        texture_asset = shader.GetInput("diffuse_texture").Get()
        texture = BASE / "inputs/official_human/textures" / Path(texture_asset.path).name
        if not texture.is_file():
            raise ValueError("Missing authored albedo texture: " + str(texture_asset))
        record = {"mesh": path, "visibility": visibility, "material": str(material.GetPath()),
                  "linear_tint": tint, "viewer_tint": viewer_color(tint),
                  "texture": str(texture.relative_to(BASE)), "texture_sha256": digest(texture),
                  "triangles": len(faces)}
        records.append(record)
        corners = (faces + offset).reshape(-1)
        offset += len(original_points)
        if visibility == "invisible":
            continue
        if str(texture) not in textures:
            textures[str(texture)] = newton.utils.load_texture(str(texture))
            if textures[str(texture)] is None:
                raise ValueError("Original texture could not be decoded: " + str(texture))
        primvar = UsdGeom.PrimvarsAPI(prim).GetPrimvar("st0")
        if not primvar or primvar.GetInterpolation() != "faceVarying":
            raise ValueError("Official face-varying UV contract changed")
        uv = np.asarray(primvar.ComputeFlattened(), dtype=np.float32)
        if len(uv) != faces.size:
            raise ValueError("Official UV/face count mismatch")
        roughness_value = shader.GetInput("reflection_roughness_constant").Get()
        roughness = .5 if roughness_value is None else float(roughness_value)
        parts.append({"name": prim.GetName(), "corners": corners,
            "points": wp.empty(len(corners), dtype=wp.vec3, device="cpu"),
            "indices": wp.array(np.arange(len(corners), dtype=np.int32), dtype=wp.int32, device="cpu"),
            "uv": wp.array(uv, dtype=wp.vec2, device="cpu"), "texture": textures[str(texture)],
            "color": wp.array([record["viewer_tint"]], dtype=wp.vec3, device="cpu"),
            "material": wp.array([[roughness, 0., 0., 1.]], dtype=wp.vec4, device="cpu")})
    report = {"robot": robot_appearance,
        "building_linear_color": building_color, "building_viewer_color": viewer_color(building_color),
        "building_roughness": robot.model.shape_source[robot.building_shape].roughness,
        "human_parts": records, "visible_meshes": len(parts), "total_meshes": len(records),
        "color_contract": "Authored linear USD color encoded for Newton's pow2.2 shader; original sRGB atlas untouched",
        "lighting": "Neutral viewport sky/ambient; not radiometric RTX lighting parity",
        "limitations": "OmniPBR normal/ORM maps are not implemented by this basic ViewerGL material API",
        "texture_input": "Unchanged RGBA pixels loaded once with public newton.utils.load_texture; passed via supported ndarray API",
        "recorded_sensor_geometry_unchanged": True,
        "sensor_followup": ("No human geometry in this source run" if human is None else "The source run selected the five authored-visible human meshes; geometric rays are not an RTX equivalence claim"
                            if visible_sensor_meshes else "The recorded ray scene included all9 meshes, including4 authored-invisible accessories; visibility parity requires a separate sensor rerun")}
    (out / "appearance.json").write_text(json.dumps(report, indent=2) + "\n")
    return parts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--view", choices=("original", "rear-right"), default="original")
    args = parser.parse_args()
    source = BASE / "runs" / args.source_run
    if source.parent != BASE / "runs" or not (source / "video_states.json").is_file():
        raise ValueError("A recorded experiment run is required")
    out = Path(os.environ["NEWTON_RUN_DIR"])
    episode_request = (json.loads((source / "episode_request.json").read_text())
                       if (source / "episode_request.json").exists() else {})
    startup_view = episode_request.get("startup_qualification", False)
    verify_inputs()
    rows = json.loads((source / "video_states.json").read_text())
    if args.limit is not None:
        rows = rows[:args.limit]
    if not rows:
        raise ValueError("No recorded physics frames")
    for name in ("render_episode.py", "scene_assets.py", "robot_scene.py", "flat_scene.py"):
        shutil.copyfile(Path(__file__).with_name(name), out / ("executed_" + name))
    long_route = episode_request.get("scene") == "flat_empty_long"
    if episode_request.get("scene") in ("flat_static", "flat_box", "flat_empty_long"):
        from flat_scene import FlatSceneRobot, FlatStaticHuman
        human = FlatStaticHuman(out) if episode_request["scene"] == "flat_static" else None
        robot = FlatSceneRobot(human, obstacle_kind={"flat_box":"box", "flat_static":"human", "flat_empty_long":"none"}[episode_request["scene"]],
                               startup_mode=episode_request.get("startup_mode", "policy"), stance_hold=episode_request.get("stance_hold", False),
                               native_cpu=episode_request.get("physics_backend") == "native",
                               scenario=json.loads((source / "inputs/stair_scenario.json").read_text()) if long_route else None)
    else:
        robot = StairRobot()
        human = OfficialHuman(out)
    parts = prepare_appearance(robot, human, out, visible_sensor_meshes=episode_request.get("geometry_obstacles", False))
    scene_caption = ("Empty flat floor | PCT global route + SCAN local curves" if long_route
                     else "Flat floor + unclassified box" if episode_request.get("scene") == "flat_box"
                     else "Flat floor + stationary human" if episode_request.get("scene") == "flat_static"
                     else "Original Building + stationary human" if episode_request.get("static_human", False)
                     else "Original Building + animated human")
    xforms = wp.array([wp.transform_identity()], dtype=wp.transform, device="cpu")
    scales = wp.array([[1., 1., 1.]], dtype=wp.vec3, device="cpu")
    curves, routes = [], []
    backend_states = [json.loads(line) for line in (source / "backend_states.jsonl").read_text().splitlines()]
    observations = source / "artifacts/reactive_observations.jsonl"
    if observations.exists():
        for line in observations.open():
            row = json.loads(line)
            if row["event"] == "bspline" and row["clock_ns"] is not None:
                curves.append(row)
            elif row["event"] == "pct_route" and row["clock_ns"] is not None:
                routes.append(row)
    frames = out / "frames"
    frames.mkdir()
    manifest = []
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 23)
    viewer = newton.viewer.ViewerGL(width=1280, height=720, vsync=False, headless=True)
    try:
        viewer.set_model(robot.model)
        flat_view = episode_request.get("scene") in ("flat_static", "flat_box", "flat_empty_long")
        viewer.camera.fov = 50.0 if long_route else 45.0 if startup_view or args.view == "rear-right" else 60.0 if flat_view else 80.0
        # Pinned RendererGL controls. Remove the default saturated sky cast;
        # the archived scene used neutral dome lighting, not a camera spotlight.
        viewer.renderer.sky_upper = viewer.renderer.sky_lower = (.9, .9, .9)
        viewer.renderer.ambient_sky = (.8, .8, .8)
        viewer.renderer.ambient_ground = (.3, .3, .3)
        viewer.renderer.spotlight_enabled = False
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
            if flat_view:
                # Fixed display-only side view keeps both the obstacle and
                # the complete recorded robot motion visible. No ray sensor
                # or planner input uses this camera.
                position = np.array([1.5, 3.6, 2.7])
                target = np.array([1.5, 0., .6])
            if long_route:
                position = base_position + np.array([-1.2, -1.5, .9])
                target = base_position + np.array([.3, 0., -.05])
            if startup_view:
                position = np.array([.7, 1.1, .7])
                target = np.array([0., 0., .19])
            if args.view == "rear-right":
                # Robot forward is +X and right is -Y in this recorded episode.
                position = np.array([-.7, -1.1, .7])
                target = np.array([-.05, 0., .19])
            viewer.set_camera(tuple(position), pitch=-20, yaw=0)
            viewer.camera.look_at(tuple(target))
            vertices, actor = (human.vertices(0.0 if episode_request.get("static_human", False) else t)
                               if human is not None else (None, {"clip": "none", "frame": 0}))
            viewer.begin_frame(t)
            viewer.log_state(robot.state)
            current_routes = [r for r in routes if r["clock_ns"] <= round(t * 1e9)]
            if long_route:
                # Display-only metre grid; never included in the ray scene.
                starts, ends = [], []
                for x in range(-2, 16):
                    starts.append([x,-3.,.005]); ends.append([x,3.,.005])
                for y in range(-3, 4):
                    starts.append([-2.,y,.005]); ends.append([15.,y,.005])
                viewer.log_lines("metre_grid", wp.array(starts, dtype=wp.vec3), wp.array(ends, dtype=wp.vec3), colors=(.35,.37,.39))
            if current_routes:
                points = np.array([[p["pose"]["position"][k] for k in ("x","y","z")]
                                   for p in current_routes[-1]["data"]["path"]["poses"]], dtype=np.float32)
                viewer.log_lines("pct_route", wp.array(points[:-1], dtype=wp.vec3), wp.array(points[1:], dtype=wp.vec3), colors=(1.,.55,.05))
            for part in parts:
                part["points"].assign(vertices[part["corners"]])
                name = "official_human/" + part["name"]
                viewer.log_mesh(name, part["points"], part["indices"], uvs=part["uv"], texture=part["texture"],
                                backface_culling=False, dynamic=True, hidden=True)
                viewer.log_instances(name + "_instance", name, xforms, scales, part["color"], part["material"])
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
            view_label = " | rear-right view" if args.view == "rear-right" else ""
            draw.text((22, 12), f"Lite3 | Newton CPU | recorded physics  {t:05.2f} s" + view_label, font=font, fill=(242, 245, 250))
            command = row["command"]
            detail = (f"Phase: {row['controller_phase']} | body height: {row['joint_q'][2]:.3f} m | policy calls: {row['policy_calls']}"
                      if startup_view else f"Applied vx/vy/wz: {command[0]:+.3f} / {command[1]:+.3f} / {command[2]:+.3f}   |   native curve messages: {len(available)}")
            if long_route:
                mode = row.get("stance_mode", row["controller_phase"])
                if mode == "FACTORY":
                    mode = row["controller_phase"]
                distance = float(np.linalg.norm(base_position[:2] - np.array(robot.scenario["goal_ground_xyz_m"][:2])))
                detail = f"Control: {mode} | goal distance: {distance:.2f} m | command vx: {command[0]:+.2f} m/s | curve messages: {len(available)}"
            draw.text((22, 53), detail, font=small, fill=(153, 216, 239))
            if long_route:
                left, right, top, bottom = frame.width-360, frame.width-20, 115, 245
                draw.rectangle((left,top,right,bottom), fill=(20,27,37), outline=(120,130,140), width=2)
                def point(p):
                    return (left+20+(float(p[0])+1.)/14.*300., top+65-float(p[1])*35.)
                draw.text((left+10,top+5), "12 m route | orange: PCT", font=small, fill=(255,207,128))
                if current_routes:
                    draw.line([point(p) for p in points], fill=(255,165,45), width=3)
                track = [point(r["joint_q"]) for r in rows[:i+1]]
                if len(track)>1:
                    draw.line(track, fill=(80,205,255), width=3)
                bx,by=point(base_position)
                draw.ellipse((bx-5,by-5,bx+5,by+5), fill=(245,245,245))
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
            if i == len(rows) - 1 and status == "active goal":
                status = "not arrived at end of bounded observation"
            draw.rectangle((0, frame.height-76, frame.width, frame.height), fill=(15, 20, 29))
            caption = ("Crouch > PD prepare > PD stand > measured stability > policy" if startup_view else "Navigation: " + status)
            footer = ("Official Lite3 SDK spline | continuous physics | startup qualification only"
                      if startup_view else scene_caption + " | geometric LiDAR | actual recorded physics")
            if episode_request.get("factory_runtime", False):
                caption = episode_request["renderer_caption"]
                footer = episode_request["renderer_footer"]
            draw.text((22, frame.height-68), caption, font=small, fill=(255, 207, 128))
            draw.text((22, frame.height-35), footer, font=small, fill=(220, 225, 235))
            path = frames / f"{i:06d}.png"
            frame.save(path)
            manifest.append({"file": str(path.relative_to(out)), "sha256": digest(path),
                             "physics_time_s": t, "actor_clip": actor["clip"], "actor_frame": actor["frame"],
                             "camera_position_m": position.tolist(), "camera_target_m": target.tolist(),
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
        "display_camera_fov_degrees": 50.0 if long_route else 45.0 if startup_view or args.view == "rear-right" else 60.0 if flat_view else 80.0,
        "display_camera_mode": "long_route_follow" if long_route else "rear_right" if args.view == "rear-right" else "startup_close_side" if startup_view else "fixed_flat_side" if flat_view else "original_follow",
        "appearance_sha256": digest(out / "appearance.json"),
        "render_only_no_physics_steps": robot.steps == 0,
        "claim": "Replay visualization of actual logged physics; no synthesized robot trajectory or live-render timing claim"}, indent=2) + "\n")


if __name__ == "__main__":
    main()

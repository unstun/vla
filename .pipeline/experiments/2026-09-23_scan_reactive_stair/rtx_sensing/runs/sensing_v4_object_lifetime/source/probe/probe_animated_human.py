#!/usr/bin/env python3
"""Isolated renderer/LiDAR skin-deformation test with a fixed official actor root."""
from __future__ import annotations

import argparse
import faulthandler
import gc
import inspect
import json
from pathlib import Path
import time
import traceback

from official_building_human import (
    VISUAL_ROOT, file_sha256, make_visual_wrapper, verify_official_bundle,
)

ANNOTATOR = "IsaacExtractRTXSensorPointCloudNoAccumulator"
MIN_POINTS = 30
MIN_POSE_DISTANCE_M = 0.01
CONTROL_MULTIPLIER = 3.0


def serializable(value):
    if isinstance(value, dict):
        return {str(k): serializable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serializable(v) for v in value]
    if hasattr(value, "tolist"):
        return value.tolist() if value.size <= 32 else {"shape": list(value.shape), "dtype": str(value.dtype)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def symmetric_distance(a, b):
    from scipy.spatial import cKDTree
    if len(a) < MIN_POINTS or len(b) < MIN_POINTS:
        raise ValueError("insufficient finite surface returns")
    return float((cKDTree(a).query(b)[0].mean() + cKDTree(b).query(a)[0].mean()) / 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    faulthandler.enable()
    faulthandler.dump_traceback_later(60, repeat=True)
    identity = verify_official_bundle(args.asset_root, args.cache_dir)
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    result = {"passed": False, "claim": "isolated fixed-root skin sensing; no robot or navigation",
              "asset_identity": identity, "sensor_profile": "Example_Rotary",
              "sensor_position_world_m": [0.0, 0.0, 1.0],
              "sensor_orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
              "actor_root_world_m": [3.0, 0.0, 0.02],
              "acceptance": {"min_points": MIN_POINTS, "min_pose_distance_m": MIN_POSE_DISTANCE_M,
                             "control_multiplier": CONTROL_MULTIPLIER},
              "probe_sha256": file_sha256(__file__)}
    from isaaclab.app import AppLauncher
    app = AppLauncher(headless=True, enable_cameras=True, device="cuda:0", fast_shutdown=False).app
    result = run_scene(args, app, identity, result, started)
    # Release Python-owned sensor/scene handles while their native plugins live.
    gc.collect()
    print("RTX_CLEANUP application_close_after_scene_release", flush=True)
    app.close(wait_for_replicator=False)
    faulthandler.cancel_dump_traceback_later()
    (args.output / "teardown.json").write_text(json.dumps({"state": "teardown_completed"}) + "\n")
    return 0 if result["passed"] else 2


def run_scene(args, app, identity, result, started):
    lidar = None
    rgb = None
    camera_product = None
    sim = None

    def cleanup_marker(stage):
        (args.output / "cleanup_stage.json").write_text(json.dumps({"stage": stage}) + "\n")
        print("RTX_CLEANUP " + stage, flush=True)
    try:
        import imageio.v2 as imageio
        import numpy as np
        from pxr import UsdGeom
        import omni.replicator.core as rep
        import omni.kit.app
        import isaaclab.sim as sim_utils
        manager = omni.kit.app.get_app().get_extension_manager()
        manager.set_extension_enabled_immediate("isaacsim.sensors.rtx", True)
        if not manager.is_extension_enabled("isaacsim.sensors.rtx"):
            raise RuntimeError("RTX extension did not enable")
        from isaacsim.sensors.rtx import LidarRtx
        from lite3_sim_bridge import run_isaac_v12_fallback as v12

        if file_sha256(v12.__file__) != "6104fe686bcd3bc0480c0afc1b41dde84d1a35d45a6dbbe9e51d98e6719ba3e3":
            raise RuntimeError("pinned official animation player changed")
        result["rtx_class_source_sha256"] = file_sha256(inspect.getfile(LidarRtx))
        sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=0.1, render_interval=1, device="cuda:0"))
        wrapper = make_visual_wrapper(args.output / "official_human_visual.usda",
                                      Path(identity["character_usd"]), Path(identity["cache_npz"]), v12)
        result["wrapper"] = wrapper
        cfg = sim_utils.UsdFileCfg(usd_path=wrapper["path"])
        cfg.func(VISUAL_ROOT, cfg, translation=(3.0, 0.0, 0.02))
        light = sim_utils.DomeLightCfg(intensity=2500.0, color=(0.85, 0.90, 1.0))
        light.func("/World/Light", light)
        meshes = sorted(str(p.GetPath()) for p in sim.stage.Traverse() if p.GetTypeName() == "Mesh")
        if len(meshes) != 9 or not all(p.startswith(VISUAL_ROOT + "/") for p in meshes):
            raise RuntimeError("scene must contain only the nine official human mesh prims")
        result["scene_mesh_prims"] = meshes
        camera = rep.create.camera(position=(6.0, -4.0, 2.7), look_at=(3.0, 0.0, 0.9), focal_length=40.0)
        camera_product = rep.create.render_product(camera, (960, 720))
        rgb = rep.AnnotatorRegistry.get_annotator("rgb")
        rgb.attach([camera_product])
        lidar = LidarRtx(prim_path="/World/RtxLidar", translation=np.array([0.0, 0.0, 1.0]),
                         orientation=np.array([1.0, 0.0, 0.0, 0.0]), config_file_name="Example_Rotary")
        lidar.attach_annotator(ANNOTATOR)
        player = v12._OfficialHumanAnimationPlayer(sim.stage, Path(identity["cache_npz"]),
                                                  "phase_conditioned", visual_root_path=VISUAL_ROOT)
        player.update(0.0, "crossing")
        sim.reset()
        lidar.initialize()
        frames_dir = args.output / "frames"
        frames_dir.mkdir()
        sensor_prim = sim.stage.GetPrimAtPath("/World/RtxLidar")
        result["sensor_attributes"] = {a.GetName(): serializable(a.Get()) for a in sensor_prim.GetAttributes()
                                       if a.GetName().startswith("omni:sensor")}
        print("RTX_SENSOR_READY", flush=True)
        for _ in range(30):
            sim.step(render=True)

        captures = []
        clouds = {}
        images = {}
        for name, pose_frame in (("pose0_a", 0), ("pose0_b", 0), ("pose22", 22), ("pose0_return", 0)):
            animation = player.update((pose_frame + 0.001) / 30.0, "crossing")
            for _ in range(20):
                sim.step(render=True)
            data = lidar.get_annotators()[ANNOTATOR].get_data()
            points = np.asarray(data["data"], dtype=np.float32).reshape(-1, 3)
            finite = points[np.isfinite(points).all(axis=1) & (np.linalg.norm(points, axis=1) > 0.1)]
            clouds[name] = finite.copy()
            image = np.asarray(rgb.get_data()).copy()
            if image.ndim != 3 or image.shape[0] != 720 or image.shape[1] != 960:
                raise RuntimeError("RGB render product has no usable frame")
            images[name] = image[:, :, :3]
            imageio.imwrite(frames_dir / (name + ".png"), image)
            transform = UsdGeom.Xformable(sim.stage.GetPrimAtPath(VISUAL_ROOT)).ComputeLocalToWorldTransform(0)
            row = {"name": name, "animation": animation, "sim_time_s": float(sim.current_time),
                   "finite_points": len(finite), "point_min": finite.min(axis=0).tolist() if len(finite) else None,
                   "point_max": finite.max(axis=0).tolist() if len(finite) else None,
                   "actor_transform": [list(r) for r in transform], "raw_metadata": serializable(data.get("info", {}))}
            captures.append(row)
            print(json.dumps(row), flush=True)
        np.savez_compressed(args.output / "pointclouds.npz", **clouds)
        result["captures"] = captures
        control = max(symmetric_distance(clouds["pose0_a"], clouds["pose0_b"]),
                      symmetric_distance(clouds["pose0_b"], clouds["pose0_return"]))
        different = symmetric_distance(clouds["pose0_b"], clouds["pose22"])
        rgb_change = float(np.abs(images["pose0_b"].astype(float) - images["pose22"].astype(float)).mean())
        result.update({"control_distance_m": control, "different_pose_distance_m": different,
                       "rgb_mean_abs_change": rgb_change,
                       "passed": bool(different > max(MIN_POSE_DISTANCE_M, CONTROL_MULTIPLIER * control)
                                      and rgb_change > 0.1
                                      and all(r["actor_transform"] == captures[0]["actor_transform"] for r in captures))})
        writer = imageio.get_writer(args.output / "official_human_rtx.mp4", fps=10,
                                    codec="libx264", quality=8, macro_block_size=2)
        with writer, (args.output / "video_frames.jsonl").open("w") as log:
            for index in range(90):
                animation = player.update(index / 10.0, "crossing")
                sim.step(render=True)
                writer.append_data(np.asarray(rgb.get_data())[:, :, :3].copy())
                log.write(json.dumps({"video_frame": index, "sim_time_s": float(sim.current_time),
                                      "animation": animation}) + "\n")
        result["video"] = {"file": "official_human_rtx.mp4", "frame_count": 90, "fps": 10,
                           "time_basis": "simulation, 0.1 seconds per recorded frame"}
        print(json.dumps({k: result[k] for k in ("passed", "control_distance_m", "different_pose_distance_m")}), flush=True)
    except Exception as exc:
        result.update({"passed": False, "failure_type": type(exc).__name__,
                       "failure_message": str(exc), "traceback": traceback.format_exc()})
        traceback.print_exc()
    finally:
        result["wall_seconds_before_teardown"] = time.monotonic() - started
        (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        cleanup_marker("stop_timeline")
        if sim is not None:
            # Pinned IsaacLab's STOP callback renders until PLAY resumes.
            # A terminal headless stop must disable that interactive loop,
            # as SimulationContext.reset() does around its own STOP event.
            sim._disable_app_control_on_stop_handle = True
            sim.stop()
        cleanup_marker("detach_annotators")
        if lidar is not None:
            lidar.detach_all_annotators()
            lidar.detach_all_writers()
            lidar._acquisition_callback = None
            lidar._stage_open_callback = None
            lidar._timer_reset_callback = None
            if lidar._render_product is not None:
                lidar._render_product.destroy()
                lidar._render_product = None
        if rgb is not None:
            rgb.detach()
        if camera_product is not None:
            camera_product.destroy()
        cleanup_marker("flush_updates")
        for _ in range(3):
            app.update()
        cleanup_marker("clear_simulation_context")
        if sim is not None:
            sim.clear_instance()
    return result


if __name__ == "__main__":
    raise SystemExit(main())

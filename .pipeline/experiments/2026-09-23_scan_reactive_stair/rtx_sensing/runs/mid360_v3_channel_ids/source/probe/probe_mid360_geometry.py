#!/usr/bin/env python3
"""Analytic ray parity, then actual official-human motion through scan_10 core."""
from __future__ import annotations

import argparse
import faulthandler
import gc
import json
from pathlib import Path
import time
import traceback

from official_building_human import VISUAL_ROOT, file_sha256, make_visual_wrapper, verify_official_bundle
from probe_animated_human import serializable
from rtx_mid360 import RtxMid360, release_scene


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--asset-root", type=Path, required=True)
    p.add_argument("--cache-dir", type=Path, required=True)
    p.add_argument("--pattern-csv", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    faulthandler.enable()
    faulthandler.dump_traceback_later(60, repeat=True)
    identity = verify_official_bundle(args.asset_root, args.cache_dir)
    from isaaclab.app import AppLauncher
    app = AppLauncher(headless=True, enable_cameras=True, device="cuda:0", fast_shutdown=True).app
    result = {"passed": False, "claim": "MID-360 geometric snapshot and isolated temporal tracking; no Building or ROS",
              "asset_identity": identity, "source_sha256": file_sha256(__file__),
              "acceptance": {"parity_points": 20000, "parity_max_error_m": 0.005,
                             "minimum_tracked_frames": 25, "motion_frames": 40,
                             "max_direction_vector_error": 0.0001}}
    result = run_scene(args, app, identity, result)
    gc.collect()
    (args.output / "teardown.json").write_text(json.dumps({
        "state": "resources_released_close_requested", "mode": "isaacsim_default_fast_shutdown",
        "claim": "Parent must verify zero process exit and GPU release; not full extension teardown"}) + "\n")
    app.close(wait_for_replicator=False)
    faulthandler.cancel_dump_traceback_later()
    (args.output / "teardown.json").write_text('{"state":"teardown_completed"}\n')
    return 0 if result["passed"] else 2


def run_scene(args, app, identity, result):
    sim = lidar = rgb = product = None
    try:
        import numpy as np
        import imageio.v2 as imageio
        from scipy.spatial import cKDTree
        import omni.kit.app
        import omni.replicator.core as rep
        from pxr import UsdGeom
        import isaaclab.sim as sim_utils
        from lite3_sim_bridge import run_isaac_v12_fallback as v12
        from lite3_sim_bridge.mid360_pattern import load_mid360_pattern
        import moving_cluster_core as core
        if file_sha256(core.__file__) != "2051acc08d22acc4ed681486412d7aa78817d68a917123cc58013490173ebc53":
            raise RuntimeError("scan_10 tracker core source changed")
        manager = omni.kit.app.get_app().get_extension_manager()
        manager.set_extension_enabled_immediate("isaacsim.sensors.rtx", True)
        pattern = load_mid360_pattern(args.pattern_csv)
        result["pattern_identity"] = pattern.identity()
        sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=0.1, render_interval=1, device="cuda:0"))
        cube = UsdGeom.Cube.Define(sim.stage, "/World/ParityCube")
        cube.CreateSizeAttr(12.0)
        cube.CreateDoubleSidedAttr(True)
        cube.AddTranslateOp().Set((0.0, 0.0, 1.0))
        lidar = RtxMid360(sim.stage, "/World/Mid360Geometry", pattern)
        sim.reset()
        lidar.sensor.initialize()
        parity = []
        for window_index in (0, 1):
            directions = lidar.set_window(window_index)
            for _ in range(12):
                sim.step(render=True)
            points, data = lidar.points()
            expected = directions * (6.0 / np.max(np.abs(directions), axis=1))[:, None]
            if len(points) != len(expected):
                raise RuntimeError(f"parity return count {len(points)} != {len(expected)}")
            errors, _ = cKDTree(expected).query(points)
            reverse_errors, _ = cKDTree(points).query(expected)
            maximum = float(max(errors.max(), reverse_errors.max()))
            row = {"window": window_index, "count": len(points), "max_error_m": maximum,
                   "mean_error_m": float(errors.mean()), "metadata": serializable(data.get("info", {}))}
            parity.append(row)
            np.savez_compressed(args.output / f"parity_{window_index}.npz", actual=points, expected=expected)
            print("MID360_PARITY " + json.dumps(row), flush=True)
            if maximum > 0.005:
                raise RuntimeError("RTX ray directions/ranges differ from analytic Livox snapshot")
        result["parity"] = parity
        sim.stage.RemovePrim("/World/ParityCube")
        wrapper = make_visual_wrapper(args.output / "official_human_visual.usda",
                                      Path(identity["character_usd"]), Path(identity["cache_npz"]), v12)
        cfg = sim_utils.UsdFileCfg(usd_path=wrapper["path"])
        cfg.func(VISUAL_ROOT, cfg, translation=(3.0, 0.6, 0.02))
        light = sim_utils.DomeLightCfg(intensity=2000.0)
        light.func("/World/Light", light)
        camera = rep.create.camera(position=(6.0, -4.0, 2.7), look_at=(3.0, 0.0, 0.9), focal_length=35.0)
        product = rep.create.render_product(camera, (960, 720))
        rgb = rep.AnnotatorRegistry.get_annotator("rgb")
        rgb.attach([product])
        player = v12._OfficialHumanAnimationPlayer(sim.stage, Path(identity["cache_npz"]),
                                                  "phase_conditioned", visual_root_path=VISUAL_ROOT)
        player.update(0.0, "crossing")
        for _ in range(15):
            sim.step(render=True)
        tracker = core.MovingClusterTracker()
        terrain = core.TerrainSupport("world", 1, "explicit_synthetic_flat_support", 0.1, 0.0, 0.0,
                                      {(i, j): (0.0,) for i in range(-100, 101) for j in range(-100, 101)})
        rows = []
        clouds = {}
        writer = imageio.get_writer(args.output / "mid360_human_tracking.mp4", fps=10, codec="libx264", quality=8, macro_block_size=2)
        with writer, (args.output / "observations.jsonl").open("w") as log:
            for index in range(40):
                # The unrotated official character faces -Y.
                root = (3.0, 0.6 - index * 0.03, 0.02)
                v12._set_official_human_visual_pose(sim.stage, {
                    "visual_root_xyz_m": root, "visual_quaternion_wxyz": (1.0, 0.0, 0.0, 0.0),
                    "visual_foot_world_z_m": 0.02, "visual_top_world_z_m": 1.7557525825500488,
                    "capsule_bottom_world_z_m": None, "foot_to_capsule_bottom_error_m": None,
                    "visual_yaw_radians": 0.0}, visual_root_path=VISUAL_ROOT)
                animation = player.update(index / 10.0, "crossing")
                before = time.monotonic()
                directions = lidar.set_window(index)
                sim.step(render=True)
                points, metadata = lidar.points()
                direction_error = (float(cKDTree(directions).query(
                    points / np.linalg.norm(points, axis=1)[:, None])[0].max()) if len(points) else None)
                current_window = direction_error is not None and direction_error <= 0.0001
                stamp = int(sim.current_time * 1e9)
                pose = core.PoseObservation(stamp, "world", "mid360_scan_frame", (0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0))
                # Actor truth below is logged after inference, never fed to the tracker.
                snapshot = tracker.process(core.CloudFrame(stamp, "mid360_scan_frame", points,
                                                            complete=current_window), pose, terrain, stamp)
                duration = time.monotonic() - before
                tracks = [{"id": t.id, "stamp_ns": t.stamp_ns, "center": [float(v) for v in t.center],
                           "radius_m": float(t.radius_m)} for t in snapshot.tracks]
                row = {"index": index, "stamp_ns": stamp, "points": len(points), "complete": snapshot.complete,
                       "reason": snapshot.reason, "tracks": tracks, "source_id": snapshot.source_id,
                       "actor_truth_root_world_m": root, "animation": animation,
                       "max_direction_vector_error": direction_error, "matches_current_window": current_window,
                       "sensor_to_core_wall_s": duration, "scan_window": lidar.window.as_dict()}
                rows.append(row)
                clouds[f"cloud_{index:03d}"] = points
                log.write(json.dumps(row) + "\n"); log.flush()
                writer.append_data(np.asarray(rgb.get_data())[:, :, :3].copy())
        np.savez_compressed(args.output / "motion_clouds.npz", **clouds)
        tracked = [r for r in rows if r["complete"] and len(r["tracks"]) == 1]
        ids = sorted({r["tracks"][0]["id"] for r in tracked})
        result.update({"tracked_frame_count": len(tracked), "track_ids": ids,
                       "frames": len(rows), "passed": len(tracked) >= 25 and len(ids) == 1
                       and all(r["matches_current_window"] for r in rows),
                       "video": "mid360_human_tracking.mp4"})
    except Exception as exc:
        result.update({"passed": False, "failure_type": type(exc).__name__, "failure_message": str(exc),
                       "traceback": traceback.format_exc()})
        traceback.print_exc()
    finally:
        (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        release_scene(app, sim, [lidar.sensor] if lidar else [], [rgb] if rgb else [], [product] if product else [])
    return result


if __name__ == "__main__":
    raise SystemExit(main())

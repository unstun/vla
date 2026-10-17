#!/usr/bin/env python3
"""Create a separate RTX Building runner from the preserved official candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "isaac_candidate/building_official_mesh_source/run_pct_scan_building.py"
BASE_SHA = "1a0c9a688ac6528460354b7adcd3ea1f9e20d2c23c80748cc9c5645bedd6fe62"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("RTX runner anchor count changed: " + old[:80])
    return source.replace(old, new, 1)


def materialize(output, actor_route, locomotion_height_contract=False):
    if sha(BASE) != BASE_SHA or output.exists():
        raise ValueError("base source changed or output already exists")
    route = json.loads(actor_route.read_text())
    if route.get("geometry_reviewed") is not True:
        raise ValueError("actor route geometry screen has not passed")
    source = BASE.read_text()
    source = once(source, '    parser.add_argument("--seed", type=int, default=42)\n',
                  '    parser.add_argument("--review-camera-focal-length-mm", type=float, default=8.0)\n'
                  '    parser.add_argument("--seed", type=int, default=42)\n')
    source = once(source, '    _livox_mid360_validate_args(args)\n',
                  '    _livox_mid360_validate_args(args)\n'
                  '    if args.lidar_pattern_mode != "livox_mid360":\n'
                  '        raise ValueError("RTX candidate requires the pinned Livox CSV")\n')
    source = once(source, '    finally:\n        app.close()\n',
                  '    finally:\n'
                  '        from isaaclab.sim import SimulationContext\n'
                  '        context = SimulationContext.instance()\n'
                  '        if context is not None:\n'
                  '            context._disable_app_control_on_stop_handle = True\n'
                  '        app.close(wait_for_replicator=False)\n')
    source = once(source, '    import isaaclab.sim as sim_utils\n',
                  '    import isaaclab.sim as sim_utils\n'
                  '    import omni.kit.app\n'
                  '    omni.kit.app.get_app().get_extension_manager().set_extension_enabled_immediate(\n'
                  '        "isaacsim.sensors.rtx", True)\n'
                  '    from .rtx_mid360 import RtxMid360\n'
                  '    from .rtx_runner_sensor import capture_sweep\n')
    source = once(source,
        '    cfg.scene.navigation_lidar.mesh_prim_paths.append(\n'
        '        MultiMeshRayCasterCfg.RaycastTargetCfg(\n'
        '            prim_expr=VISUAL_ROOT, merge_prim_meshes=True,\n'
        '            track_mesh_transforms=True))\n'
        '    cfg.scene.navigation_lidar.update_mesh_ids = True\n',
        '    # Warp remains a static Building preflight and attachment-pose source.\n'
        '    # Actual published sweeps below come only from the RTX renderer.\n'
        '    cfg.scene.navigation_lidar.update_mesh_ids = False\n')
    source = once(source,
        '        "sensor_geometry": "official USD mesh, frozen vertices at raycaster initialization",\n',
        '        "sensor_geometry": "actual RTX renderer geometry with official walk skinning",\n')
    source = once(source, '    camera_intrinsics = _read_viewer_camera_intrinsics(\n',
                  '    # Wider observer camera: include the robot and the person in one frame.\n'
                  '    # This camera is not an input to navigation or locomotion.\n'
                  '    from pxr import Usd\n'
                  '    review_camera = UsdGeom.Camera(env.sim.stage.GetPrimAtPath(cfg.viewer.cam_prim_path))\n'
                  '    with Usd.EditContext(env.sim.stage, env.sim.stage.GetSessionLayer()):\n'
                  '        review_camera.GetFocalLengthAttr().Set(float(args.review_camera_focal_length_mm))\n'
                  '    if abs(float(review_camera.GetFocalLengthAttr().Get()) - args.review_camera_focal_length_mm) > 0.001:\n'
                  '        raise AdapterFailure("observer camera focal length override did not apply")\n'
                  '    camera_intrinsics = _read_viewer_camera_intrinsics(\n')
    source = once(source,
        '    limits = CommandLimits(\n',
        '    rtx_lidar = RtxMid360(env.sim.stage, "/World/VlaRtxMid360",\n'
        '                            helper_args.mid360_pattern_table)\n'
        '    rtx_lidar.sensor.initialize()\n'
        '    write_json(args.output / "rtx_sensor_identity.json", {\n'
        '        "pattern": helper_args.mid360_pattern_table.identity(),\n'
        '        "adapter": "RTX pinned Livox CSV geometric snapshot",\n'
        '        "static_first_hit_check": "Warp Building only; not published to navigation",\n'
        '        "self_return_filter": "none; current actual returns retained",\n'
        '    })\n'
        '    limits = CommandLimits(\n')
    source = once(source,
        '                    if v12._official_mid360_enabled(helper_args):\n'
        '                        v12._set_mid360_scan_window(\n'
        '                            lidar, helper_args.mid360_pattern_table, scan_index, torch)\n'
        '                    else:\n'
        '                        lidar.update(dt=0.0, force_recompute=True)\n'
        '                    hits = lidar.data.ray_hits_w[0]\n'
        '                    sensor_position_values, sensor_quaternion_values = mounted_sensor_pose(\n'
        '                        lidar.data.pos_w[0].detach().cpu().tolist(),\n'
        '                        lidar.data.quat_w[0].detach().cpu().tolist(),\n'
        '                        lidar.cfg.offset.pos, lidar.cfg.offset.rot)\n',
        '                    hits, sensor_position_values, sensor_quaternion_values, rtx_capture = capture_sweep(\n'
        '                        env.sim, lidar, rtx_lidar, scan_index, torch)\n')
    source = once(source, '                        "filter_stats": dict(filter_stats),\n',
                  '                        "filter_stats": dict(filter_stats),\n'
                  '                        "rtx_capture": rtx_capture,\n')
    source = once(source, '        raw_env.close()\n',
                  '        env.sim._disable_app_control_on_stop_handle = True\n'
                  '        rtx_lidar.sensor.detach_all_annotators()\n'
                  '        rtx_lidar.sensor.detach_all_writers()\n'
                  '        raw_env.close()\n')
    compile(source, "run_pct_scan_building.py", "exec")
    if locomotion_height_contract:
        source = once(source, '    body_height = float(segment["nominal_body_height_m"])',
                      '    body_height = float(segment["spawn_body_height_m"])\n'
                      '    locomotion_reference_height = float(segment["locomotion_reference_height_m"])')
        source = once(source, '    contract = v12._capture_v12_task_contract(cfg)',
                      '    contract = v12._capture_v12_task_contract(cfg)\n'
                      '    from .height_reference_contract import verify_runtime_height_contract\n'
                      '    contract["height_reference_contract"] = verify_runtime_height_contract(\n'
                      '        cfg, args.runtime, body_height, locomotion_reference_height)')
        source = once(source, '        "nominal_body_height_m": body_height,',
                      '        "nominal_body_height_m": body_height,\n'
                      '        "spawn_body_height_m": body_height,\n'
                      '        "locomotion_reference_height_m": locomotion_reference_height,')
        source = once(source, 'abs((position[2] - body_height) - goal_ground[2])',
                      'abs((position[2] - locomotion_reference_height) - goal_ground[2])')
    helper = (HERE.parent / "isaac_candidate/official_building_human.py").read_text()
    helper = once(helper, "APPROVED_ROUTE_SHA256 = None", "APPROVED_ROUTE_SHA256 = " + repr(sha(actor_route)))
    output.mkdir(parents=True)
    (output / "run_pct_scan_building.py").write_text(source)
    (output / "official_building_human.py").write_text(helper)
    shutil.copy2(HERE / "rtx_runner_sensor.py", output / "rtx_runner_sensor.py")
    shutil.copy2(HERE.parent / "rtx_sensing/rtx_mid360.py", output / "rtx_mid360.py")
    if locomotion_height_contract:
        shutil.copy2(HERE / "height_reference_contract.py", output / "height_reference_contract.py")
    manifest = {"base_sha256": BASE_SHA, "actor_route_sha256": sha(actor_route),
                "files": {p.name: sha(p) for p in output.glob("*.py")},
                "claim": "prepared RTX Building candidate; requires standing and live SCAN episode checks"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--actor-route", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(materialize(args.output, args.actor_route), indent=2))

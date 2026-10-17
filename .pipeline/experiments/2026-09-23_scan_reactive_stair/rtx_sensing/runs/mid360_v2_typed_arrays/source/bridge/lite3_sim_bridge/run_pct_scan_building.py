"""Building-specific PCT-to-SCAN-to-V12 closed loop on one platform segment.

This entry point owns nothing that the Office/Forest runner owns. It reuses the
pinned V12 loading, task contract capture, transport, dual-cloud conversion and
command-state helpers, and it builds the Building scene the same way the
PCT-only `run_dynamics.py` reference does. The differences from that reference
are deliberate and bounded:

  * navigation LiDAR is restored and retargeted at the Building USD terrain, so
    the planner consumes actual ray hits instead of an offline map;
  * the PCT lookahead follower is gone. Motion comes only from SCAN over TCP;
  * simulation time, body twist and scan identity are published so the planner
    and controller can run on simulation time with real velocity feedback.

Command ownership: `/planning/bspline` -> SCAN `closed_loop_controller` ->
`/quad_0/cmd_vel` -> `CMD_VEL_V1` -> V12 `base_velocity` -> policy -> PD/PhysX.
Nothing in this file generates a motion command.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import shutil
import time
import traceback
from contextlib import ExitStack
from pathlib import Path

CASES = ("stand_probe", "flat_nominal", "full_nominal", "native_nominal")
GROUND_MESH_PRIM = "/World/ground"
TERRAIN_MESH_PRIM = "/World/ground/terrain/Mesh"
BUILDING_TRIANGLE_COUNT = 16448


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, payload) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_viewer_camera_intrinsics(stage, cam_prim_path: str, resolution) -> dict:
    """Read the recording camera's aperture so an overlay can be projected offline.

    Display-only. The horizontal aperture is authored on the prim; Omniverse fits
    the render product to the horizontal extent, so the vertical half-angle is
    derived from the render aspect rather than from the authored vertical
    aperture, which does not follow the requested resolution.
    """
    from pxr import UsdGeom

    prim = stage.GetPrimAtPath(cam_prim_path)
    if not prim or not prim.IsValid():
        raise AdapterFailure(f"recording camera prim is missing: {cam_prim_path}")
    camera = UsdGeom.Camera(prim)
    focal_length = camera.GetFocalLengthAttr().Get()
    horizontal_aperture = camera.GetHorizontalApertureAttr().Get()
    vertical_aperture = camera.GetVerticalApertureAttr().Get()
    if not focal_length or not horizontal_aperture:
        raise AdapterFailure(
            "recording camera has no usable focal length or horizontal aperture; "
            "refusing to guess a field of view for the overlay"
        )
    width, height = int(resolution[0]), int(resolution[1])
    half_horizontal = math.atan(float(horizontal_aperture) / (2.0 * float(focal_length)))
    return {
        "cam_prim_path": cam_prim_path,
        "render_width": width,
        "render_height": height,
        "focal_length": float(focal_length),
        "horizontal_aperture": float(horizontal_aperture),
        "authored_vertical_aperture": (
            None if vertical_aperture is None else float(vertical_aperture)
        ),
        "horizontal_fov_rad": 2.0 * half_horizontal,
        "aperture_fit": "horizontal",
        "source": "usd_camera_prim",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True, help="pinned building.usda")
    parser.add_argument("--runtime", type=Path, required=True, help="pinned V12 runtime root")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--route-artifact", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True, help="contracts/run_scope.json")
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new immutable run directory")
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--telemetry-host", default="127.0.0.1")
    parser.add_argument("--telemetry-port", type=int, default=46010)
    parser.add_argument("--command-host", default="127.0.0.1")
    parser.add_argument("--command-port", type=int, default=46011)
    parser.add_argument("--max-vx", type=float, default=0.30)
    parser.add_argument("--max-vy", type=float, default=0.30)
    parser.add_argument("--max-wz", type=float, default=0.8)
    parser.add_argument("--max-horizontal-norm", type=float, default=0.30)
    parser.add_argument("--speed-profile", choices=("conservative_0p3", "speed_1p0"), default="conservative_0p3")
    parser.add_argument("--robot-visual-style", choices=("native", "black_review"), default="native")
    parser.add_argument("--watchdog-seconds", type=float, default=0.25)
    parser.add_argument("--sensor-period", type=float, default=0.10)
    parser.add_argument("--sensor-translation", type=float, nargs=3,
                        default=(0.182399336, 0.0, 0.108541081))
    parser.add_argument("--sensor-pitch-degrees", type=float, default=15.0)
    parser.add_argument("--lidar-channels", type=int, default=16)
    parser.add_argument("--lidar-vertical-min", type=float, default=-7.0)
    parser.add_argument("--lidar-vertical-max", type=float, default=52.0)
    parser.add_argument("--lidar-horizontal-resolution", type=float, default=2.0)
    parser.add_argument("--lidar-min-range", type=float, default=0.10)
    parser.add_argument("--lidar-max-range", type=float, default=12.0)
    parser.add_argument("--terrain-filter-cell-size", type=float, default=0.30)
    parser.add_argument("--terrain-filter-height-threshold", type=float, default=0.12)
    parser.add_argument("--terrain-filter-neighbor-cells", type=int, default=1)
    parser.add_argument("--terrain-filter-minimum-neighbor-cells", type=int, default=1)
    parser.add_argument("--contact-force-threshold", type=float, default=5.0)
    parser.add_argument("--nonfoot-contact-threshold", type=float, default=5.0)
    parser.add_argument("--contact-policy", choices=("nonfoot_fatal", "native_v12"),
                        default="nonfoot_fatal",
                        help="native_v12 records non-foot contact without an added termination")
    parser.add_argument("--unfiltered-planner-cloud", action="store_true",
                        help="Send measured returns to the upstream map without the project terrain filter")
    parser.add_argument("--goal-tolerance-m", type=float, default=0.25)
    parser.add_argument("--terminal-window-seconds", type=float, default=2.0)
    parser.add_argument("--terminal-command-norm", type=float, default=0.01)
    parser.add_argument("--terminal-speed-mps", type=float, default=0.10)
    parser.add_argument("--terminal-yaw-rate-radps", type=float, default=0.15)
    parser.add_argument("--connection-ready-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--max-wall-seconds", type=float, default=900.0)
    parser.add_argument("--video-fps", type=float, default=12.5)
    # Capture stride in control steps. Offline three-view composition spends the
    # fixed delivery byte ceiling on fewer, sharper frames, so the default
    # halves the previous 25 fps capture. Recording rate only: nothing in
    # planning, control or termination reads this.
    parser.add_argument("--camera-capture-stride", type=int, default=4)
    # World-side follow camera. It only observes: no robot state is changed.
    # A lateral offset large enough to cross a corridor wall renders a
    # featureless view, so the default keeps the camera on the route centre.
    parser.add_argument("--camera-trail-m", type=float, default=2.0)
    parser.add_argument("--camera-lateral-m", type=float, default=0.0)
    parser.add_argument("--camera-height-m", type=float, default=0.55)
    parser.add_argument("--camera-look-ahead-m", type=float, default=0.6)
    parser.add_argument("--camera-look-down-m", type=float, default=0.25)
    parser.add_argument("--video-resolution", type=int, nargs=2, default=(1920, 1080))
    parser.add_argument("--cloud-record-stride", type=int, default=1)
    # Complete body state at every control step, independent of the point-cloud
    # batch. Off by default so a legacy scope reproduces byte for byte.
    parser.add_argument("--complete-body-state", dest="complete_body_state",
                        action="store_true", default=False)
    parser.add_argument("--no-complete-body-state", dest="complete_body_state",
                        action="store_false")
    # Priority telemetry sending and asynchronous recording. Both default off.
    parser.add_argument("--priority-telemetry", dest="priority_telemetry",
                        action="store_true", default=False)
    parser.add_argument("--no-priority-telemetry", dest="priority_telemetry",
                        action="store_false")
    parser.add_argument("--async-recording", dest="async_recording",
                        action="store_true", default=False)
    parser.add_argument("--no-async-recording", dest="async_recording",
                        action="store_false")
    parser.add_argument("--freeze-gc", dest="freeze_gc",
                        action="store_true", default=False)
    parser.add_argument("--no-freeze-gc", dest="freeze_gc", action="store_false")
    parser.add_argument("--feedback-dropout-start-s", type=float, default=-1.0)
    parser.add_argument("--feedback-dropout-wall-s", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda:0")
    return parser


class AdapterFailure(RuntimeError):
    """Raised when a declared invariant of this run is violated."""


class TrialTermination(RuntimeError):
    """Raised instead of letting the environment silently auto-reset."""


def validate_motion_profile(args):
    cap = {"conservative_0p3": 0.30, "speed_1p0": 1.0}[args.speed_profile]
    limits = (args.max_vx, args.max_vy, args.max_horizontal_norm)
    if any(not math.isfinite(value) or value <= 0 or value > cap + 1e-12 for value in limits):
        raise ValueError(f"horizontal limits must be positive and at most {cap} m/s for {args.speed_profile}")
    if not math.isfinite(args.max_wz) or not 0 < args.max_wz <= 1.0 + 1e-12:
        raise ValueError("yaw limit must remain within the upstream controller's (0, 1.0] rad/s range")


def validate_run_duration(case, duration):
    """Long runs require their own case; old dispatch bounds stay unchanged."""
    maximum = {"full_nominal": 180.0, "native_nominal": 600.0}.get(case, 45.0)
    if case not in CASES or not math.isfinite(duration) or not 0 < duration <= maximum:
        raise ValueError(f"duration-seconds must be within (0, {maximum:g}] for {case}")


def route_scope(case, scope):
    """A full-course dispatch cannot accidentally inherit a platform scope."""
    if case in ("full_nominal", "native_nominal") and "full_route" not in scope:
        raise ValueError(f"{case} requires an explicit full_route scope")
    return scope["full_route"] if "full_route" in scope else scope["platform_segment"]


def execution_configuration(args):
    """Freeze every runner setting independently of host/artifact paths."""
    paths = {"scene", "runtime", "checkpoint", "route_artifact", "scope", "output",
             "execution_manifest"}
    # Round-trip normalizes argparse tuples and JSON lists identically.
    return json.loads(json.dumps({key: value for key, value in vars(args).items() if key not in paths}))


def verify_execution_inputs(args):
    """Check the frozen local-source manifest before initializing Isaac."""
    scope = json.loads(args.scope.read_text())
    if scope.get("execution_source_sha256") != sha256(__file__):
        raise AdapterFailure("runner source differs from frozen execution contract")
    if scope.get("execution_configuration") != execution_configuration(args):
        raise AdapterFailure("runner configuration differs from frozen execution contract")
    if scope.get("execution_manifest_sha256") != sha256(args.execution_manifest):
        raise AdapterFailure("execution manifest differs from frozen execution contract")
    manifest = json.loads(args.execution_manifest.read_text())
    root = Path(manifest["root"]).resolve()
    if not manifest.get("files"):
        raise AdapterFailure("empty execution source manifest")
    for entry in manifest["files"]:
        path = (root / entry["path"]).resolve()
        if root not in path.parents or sha256(path) != entry["sha256"]:
            raise AdapterFailure("execution source mismatch: " + entry["path"])


def main(argv=None) -> int:
    """Validate the request, start Isaac, then run the bounded trial.

    Argument parsing and the Isaac app launch live here rather than at module
    scope so the module stays importable: the run script imports it purely to
    prove which copy of this source the interpreter actually loaded.
    """
    args = build_parser().parse_args(argv)
    if args.case == "native_nominal" and args.contact_policy != "native_v12":
        raise SystemExit("native_nominal records contact and preserves native V12 termination")
    from .feedback_dropout import FeedbackDropout
    dropout = FeedbackDropout(args.feedback_dropout_start_s, args.feedback_dropout_wall_s)
    if dropout.enabled and (not args.complete_body_state or args.case != "flat_nominal"):
        raise SystemExit("feedback dropout requires complete state and the flat_nominal case")
    validate_run_duration(args.case, args.duration_seconds)
    validate_motion_profile(args)
    verify_execution_inputs(args)
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, args.output / "executed_run_pct_scan_building.py")

    # Isaac requires the app launcher before any isaaclab module import.
    from isaaclab.app import AppLauncher

    app = AppLauncher(headless=True, enable_cameras=True, device=args.device).app
    try:
        status = _run(args)
    except Exception as exc:  # noqa: BLE001 - the failure must survive as evidence
        write_json(args.output / "runtime_error.json", {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        })
        raise
    finally:
        app.close()
    return int(status)


def _run(args) -> int:
    import gymnasium as gym
    import imageio.v2 as imageio
    import numpy as np
    import torch
    from pxr import UsdGeom, UsdPhysics

    import isaaclab.sim as sim_utils
    from isaaclab.assets import AssetBaseCfg
    from isaaclab.sensors.ray_caster import MultiMeshRayCasterCfg
    from isaaclab.terrains import TerrainImporterCfg
    from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry

    from lite3_sim_bridge import run_isaac_v12_fallback as v12
    from lite3_sim_bridge.command_state import CommandLimits, LatestCommandState
    from lite3_sim_bridge.contact_guard import (
        ContactHistoryError,
        SubstepContactMonitor,
        SubstepContactStop,
        required_substeps_for,
    )
    from lite3_sim_bridge.trial_events import TrialEvents, TrialStateMutation, trial_exit_code
    from lite3_sim_bridge.isaac_adapter_core import (
        canonical_config_sha256,
        mounted_sensor_pose,
        quaternion_wxyz_to_xyzw,
        split_geometry_cloud_points,
        world_hits_to_sensor_points,
    )
    from lite3_sim_bridge.protocol import (
        BodyStateV1,
        BodyStateV2,
        DualCloudSensorFrameV1,
        JointStateV1,
        MessageType,
        StatusFlag,
        StatusV1,
        encode_body_state_payload,
        encode_body_state_v2_payload,
        encode_dual_cloud_sensor_payload,
        encode_frame,
        encode_joint_state_payload,
        encode_status_payload,
        pack_xyz_points,
    )
    from lite3_sim_bridge.recording_load import AsyncRecorder
    from lite3_sim_bridge.transport import CommandReceiverServer, TelemetryPublisherServer

    v12._activate_vendored_rsl_rl(args.runtime / "source/rsl_rl")
    from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper  # noqa: E402

    __import__("robot_lab.tasks")

    # ---- identity gates before anything physical happens -------------------
    scope = json.loads(args.scope.read_text(encoding="utf-8"))
    frozen = scope["frozen_assets"]
    if sha256(args.checkpoint) != v12.PINNED_CHECKPOINT_SHA256:
        raise AdapterFailure("checkpoint SHA-256 does not match the pinned V12 weights")
    if sha256(args.checkpoint) != frozen["checkpoint"]["sha256"]:
        raise AdapterFailure("checkpoint SHA-256 does not match the frozen run scope")
    if sha256(args.scene) != frozen["building_usda"]["sha256"]:
        raise AdapterFailure("Building USD SHA-256 does not match the frozen run scope")
    urdf_path = args.runtime / "resources/lite3/urdf/lite3.urdf"
    if sha256(urdf_path) != frozen["original_urdf"]["sha256"]:
        raise AdapterFailure("runtime URDF is not the pinned original V12 URDF")

    artifact = json.loads(args.route_artifact.read_text(encoding="utf-8"))
    route = np.asarray(artifact["points_xyz_m"], dtype=np.float64)
    if route.shape[1] != 3 or len(route) < 2 or not np.isfinite(route).all():
        raise AdapterFailure("route artifact geometry is unusable")
    segment = route_scope(args.case, scope)
    if artifact["semantics"] == "terrain_ground_xyz_m" and not artifact["body_height_applied"]:
        start_ground = route[0].copy()
        goal_ground = route[-1].copy()
        if not np.allclose(start_ground, segment["start_ground_xyz_m"], atol=1e-9):
            raise AdapterFailure("route artifact start disagrees with the frozen segment")
        if not np.allclose(goal_ground, segment["goal_ground_xyz_m"], atol=1e-9):
            raise AdapterFailure("route artifact goal disagrees with the frozen segment")
    elif artifact["semantics"] == "body_reference_xyz_m" and artifact["body_height_applied"]:
        # Native PCT body-reference samples are not physical ground heights.
        # Keep the requested spawn/goal independent; do not move the spawn to
        # the first optimizer sample or rewrite its Z against the scene mesh.
        start_ground = np.asarray(segment["start_ground_xyz_m"], dtype=np.float64)
        goal_ground = np.asarray(segment["goal_ground_xyz_m"], dtype=np.float64)
        if start_ground.shape != (3,) or goal_ground.shape != (3,) or not (
                np.isfinite(start_ground).all() and np.isfinite(goal_ground).all()):
            raise AdapterFailure("native route requires finite frozen physical endpoints")
    else:
        raise AdapterFailure("route representation and body-height declaration disagree")
    body_height = float(segment["nominal_body_height_m"])
    start_yaw = float(segment["start_tangent_yaw_radians"])

    # ---- scene, policy and sensor configuration ---------------------------
    cfg = load_cfg_from_registry(v12.DEFAULT_TASK, "env_cfg_entry_point")
    agent = load_cfg_from_registry(v12.DEFAULT_TASK, "rsl_rl_cfg_entry_point")
    contract = v12._capture_v12_task_contract(cfg)
    if contract["policy_observation_dimension"] != 450 or contract["action_dimension"] != 12:
        raise AdapterFailure("pinned V12 observation/action contract changed")

    helper_args = v12._parser().parse_args([
        "--output-dir", str(args.output),
        "--checkpoint", str(args.checkpoint),
        "--vendored-rsl-rl", str(args.runtime / "source/rsl_rl"),
        "--mode", "external",
        "--duration-seconds", str(args.duration_seconds),
        "--seed", str(args.seed),
        "--device", args.device,
        "--sensor-period", str(args.sensor_period),
        "--sensor-translation", *[str(value) for value in args.sensor_translation],
        "--sensor-pitch-degrees", str(args.sensor_pitch_degrees),
        "--lidar-channels", str(args.lidar_channels),
        "--lidar-vertical-min", str(args.lidar_vertical_min),
        "--lidar-vertical-max", str(args.lidar_vertical_max),
        "--lidar-horizontal-resolution", str(args.lidar_horizontal_resolution),
        "--lidar-min-range", str(args.lidar_min_range),
        "--lidar-max-range", str(args.lidar_max_range),
        "--max-vx", str(args.max_vx),
        "--max-vy", str(args.max_vy),
        "--max-wz", str(args.max_wz),
        "--watchdog-seconds", str(args.watchdog_seconds),
    ])
    # Reuse the pinned environment configuration path: zero command ranges, no
    # domain randomization, external-mode episode length, and the existing
    # navigation LiDAR construction with its audited mount transform.
    v12._configure_environment(cfg, helper_args)
    if cfg.scene.navigation_lidar is None:
        raise AdapterFailure("navigation LiDAR was not configured; real sensing is required")

    # Inspect each substep without changing the policy's contact history.
    # V12 privileged observations flatten (history_length + 1) * four feet;
    # increasing history from three to four changes checkpoint input shapes.
    contact_substeps = required_substeps_for(
        float(cfg.decimation) * float(cfg.sim.dt), float(cfg.sim.dt)
    )
    inherited_contact_history = int(cfg.scene.contact_forces.history_length)

    source_terrain = cfg.scene.terrain
    cfg.scene.terrain = TerrainImporterCfg(
        prim_path=GROUND_MESH_PRIM,
        terrain_type="usd",
        usd_path=str(args.scene.resolve()),
        terrain_generator=source_terrain.terrain_generator,
        physics_material=source_terrain.physics_material,
        env_spacing=1.0,
        use_terrain_origins=False,
        debug_vis=False,
    )
    cfg.scene.terrain.max_init_terrain_level = 0
    # The USD import places the Building triangles under /World/ground/terrain,
    # so the raycaster needs that merged mesh as an explicit target. Without it
    # the sensor silently reuses a terrain-only Warp mesh and sees nothing.
    cfg.scene.navigation_lidar.mesh_prim_paths = [
        GROUND_MESH_PRIM,
        MultiMeshRayCasterCfg.RaycastTargetCfg(
            prim_expr=f"{GROUND_MESH_PRIM}/terrain",
            merge_prim_meshes=True,
            track_mesh_transforms=False,
        ),
    ]
    # Diagnostic height scanners only; they never reach the 450-D actor input.
    for scan in (cfg.scene.height_scanner, cfg.scene.height_scanner_small):
        scan.offset.pos = (0.0, 0.0, 0.20)
        scan.mesh_prim_paths = [TERRAIN_MESH_PRIM]

    cfg.scene.robot.init_state.pos = (
        float(start_ground[0]), float(start_ground[1]), float(start_ground[2] + body_height)
    )
    cfg.scene.robot.init_state.rot = (
        math.cos(start_yaw / 2.0), 0.0, 0.0, math.sin(start_yaw / 2.0)
    )
    cfg.scene.sky_light = AssetBaseCfg(
        prim_path="/World/skyLight", spawn=sim_utils.DomeLightCfg(intensity=1100)
    )
    cfg.viewer.origin_type = "world"
    cfg.viewer.resolution = tuple(int(value) for value in args.video_resolution)
    cfg.viewer.eye = (float(start_ground[0] - 3.0), float(start_ground[1] + 1.5),
                      float(start_ground[2] + 2.0))
    cfg.viewer.lookat = (float(start_ground[0] + 1.0), float(start_ground[1]),
                         float(start_ground[2] + 0.3))
    agent.device = args.device
    agent.seed = helper_args.seed

    raw_env = gym.make(v12.DEFAULT_TASK, cfg=cfg, render_mode="rgb_array")
    env = raw_env.unwrapped
    wrapped = RslRlVecEnvWrapper(raw_env, clip_actions=agent.clip_actions)
    policy, policy_state, observation, policy_source = v12._load_inference_policy(
        wrapped, agent, args.checkpoint, agent.device
    )
    robot = env.scene["robot"]
    from .robot_visual import apply_robot_visual
    robot_visual = apply_robot_visual(env.sim.stage, args.robot_visual_style)
    write_json(args.output / "robot_visual_identity.json", robot_visual)
    # Display-only: the render product is built from cfg.viewer.cam_prim_path at
    # cfg.viewer.resolution, so an offline overlay must project with that exact
    # camera's aperture. Reading it here keeps the value measured rather than
    # assumed; a wrong field of view produces a plausible but false overlay, so
    # a missing attribute stops the run instead of falling back to a guess.
    camera_intrinsics = _read_viewer_camera_intrinsics(
        env.sim.stage, cfg.viewer.cam_prim_path, cfg.viewer.resolution
    )
    write_json(args.output / "camera_intrinsics.json", camera_intrinsics)
    contact = env.scene.sensors["contact_forces"]
    lidar = env.scene.sensors["navigation_lidar"]
    foot_ids, foot_names = contact.find_bodies(
        ["FL_FOOT", "FR_FOOT", "HL_FOOT", "HR_FOOT"], preserve_order=True
    )
    if len(foot_ids) != 4:
        raise AdapterFailure("expected four foot contact bodies")
    nonfoot_ids = [index for index in range(len(contact.body_names)) if index not in foot_ids]
    body_foot_ids, _ = robot.find_bodies(foot_names, preserve_order=True)

    # Contact data is consumed after every physics scene update below. History
    # ordering is no longer used to infer when the case should have stopped.
    contact.update(dt=0.0, force_recompute=True)
    contact_history = contact.data.net_forces_w_history

    stage = env.sim.stage
    collision_prims = [
        str(prim.GetPath())
        for prim in stage.Traverse()
        if prim.HasAPI(UsdPhysics.CollisionAPI) and str(prim.GetPath()).startswith(GROUND_MESH_PRIM)
    ]
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath(TERRAIN_MESH_PRIM))
    triangle_count = len(mesh.GetFaceVertexCountsAttr().Get()) if mesh else 0
    if triangle_count != BUILDING_TRIANGLE_COUNT:
        raise AdapterFailure(
            f"Building collision mesh has {triangle_count} triangles, expected "
            f"{BUILDING_TRIANGLE_COUNT}"
        )

    # Prove the raycaster actually loaded meshes rather than only being
    # configured. The warp mesh container is not a plain mapping, so it is
    # inspected defensively; the authoritative proof is the hit evidence below.
    configured_targets = [
        target if isinstance(target, str) else str(getattr(target, "prim_expr", target))
        for target in lidar.cfg.mesh_prim_paths
    ]
    loaded_mesh_count = None
    for attribute in ("_mesh_ids_wp", "meshes", "_meshes"):
        container = getattr(lidar, attribute, None)
        if container is None:
            continue
        try:
            loaded_mesh_count = int(len(container))
        except TypeError:
            continue
        if loaded_mesh_count:
            break
    resolved_target_prims = sorted(
        str(prim.GetPath())
        for prim in env.sim.stage.Traverse()
        if str(prim.GetPath()).startswith(f"{GROUND_MESH_PRIM}/terrain")
    )
    lidar.update(dt=0.0, force_recompute=True)
    first_hits = lidar.data.ray_hits_w[0]
    finite_first = torch.isfinite(first_hits).all(dim=-1)
    if int(finite_first.sum().item()) == 0:
        raise AdapterFailure("navigation LiDAR returned no finite hits on the Building mesh")
    first_origin, _ = mounted_sensor_pose(
        lidar.data.pos_w[0].detach().cpu().tolist(), lidar.data.quat_w[0].detach().cpu().tolist(),
        lidar.cfg.offset.pos, lidar.cfg.offset.rot)
    first_ranges = torch.linalg.vector_norm(
        first_hits[finite_first] - first_hits.new_tensor(first_origin).unsqueeze(0), dim=-1
    )
    non_ground_first = int(
        (first_hits[finite_first][:, 2] > float(start_ground[2]) + 0.25).sum().item()
    )
    if non_ground_first == 0:
        raise AdapterFailure("no non-ground LiDAR returns at the frozen start pose")

    limits = CommandLimits(
        args.max_vx, args.max_vy, args.max_wz,
        max_horizontal_norm=args.max_horizontal_norm,
    )
    state = LatestCommandState(
        limits,
        timeout_ns=int(args.watchdog_seconds * 1.0e9),
        max_source_age_ns=int(args.watchdog_seconds * 1.0e9),
        max_future_skew_ns=25_000_000,
    )
    command_server = CommandReceiverServer(state, args.command_host, args.command_port)
    telemetry_server = TelemetryPublisherServer(
        args.telemetry_host,
        args.telemetry_port,
        priority_send=args.priority_telemetry,
    )

    identity = {
        "claim": scope["claim"] if "full_route" in scope else (
            "Frozen PCT ground-route segment consumed by Foxy SCAN mode 3, with the "
            "existing SCAN trajectory controller driving V12 over TCP. Bounded "
            "simulation preflight on one same-level Building platform segment."
        ),
        "case": args.case,
        "task": v12.DEFAULT_TASK,
        "robot_visual": robot_visual,
        "v12_contract": contract,
        "checkpoint_sha256": sha256(args.checkpoint),
        "original_urdf_path": str(urdf_path),
        "original_urdf_sha256": sha256(urdf_path),
        "scene_path": str(args.scene.resolve()),
        "scene_sha256": sha256(args.scene),
        "route_artifact_path": str(args.route_artifact.resolve()),
        "route_artifact_sha256": sha256(args.route_artifact),
        "route_id": artifact["route_id"],
        "route_semantics": artifact["semantics"],
        "route_geometry_sha256": artifact["geometry_sha256"],
        "route_point_count": int(len(route)),
        "route_arc_length_xy_m": float(artifact["statistics"]["arc_length_xy_m"]),
        "scope_path": str(args.scope.resolve()),
        "scope_sha256": sha256(args.scope),
        "execution_source_sha256": sha256(__file__),
        "execution_manifest_sha256": sha256(args.execution_manifest),
        "execution_configuration": execution_configuration(args),
        "bridge_module_file": str(Path(v12.__file__).resolve()),
        "bridge_module_sha256": sha256(v12.__file__),
        "policy_source": str(policy_source),
        "source_commit": v12.PINNED_SOURCE_COMMIT,
        "spawn_xyz": list(cfg.scene.robot.init_state.pos),
        "spawn_quat_wxyz": list(cfg.scene.robot.init_state.rot),
        "spawn_yaw_radians": start_yaw,
        "nominal_body_height_m": body_height,
        "goal_ground_xyz_m": [float(value) for value in goal_ground],
        "joint_names": list(robot.joint_names),
        "body_names": list(robot.body_names),
        "contact_body_names": list(contact.body_names),
        "collision_prims": collision_prims,
        "terrain_triangle_count": triangle_count,
        "physics_dt": float(env.physics_dt),
        "policy_dt": float(env.step_dt),
        "contact_evidence": {
            "contact_policy": args.contact_policy,
            "nonfoot_threshold_n": args.nonfoot_contact_threshold,
            "required_substeps_per_control_period": contact_substeps,
            "inherited_contact_history_length": inherited_contact_history,
            "effective_contact_history_length": int(contact_history.shape[1]),
            "history_newest_first_verified": None,
            "acquisition": "after_each_physics_substep_scene_update",
            "vendored_torso_termination_preserved": True,
            "note": (
                "Every physics substep inside each control period is inspected. "
                + ("Non-foot contact is recorded without added termination. "
                   if args.contact_policy == "native_v12" else
                   "Non-foot contact at the threshold latches case failure. ")
                + "The vendored V12 TORSO-only 1 N termination remains unchanged."
            ),
        },
        "sensor_period_s": args.sensor_period,
        "lidar_prim_path": lidar.cfg.prim_path,
        "lidar_offset_pos": list(lidar.cfg.offset.pos),
        "lidar_offset_rot_wxyz": list(lidar.cfg.offset.rot),
        "lidar_ray_count": int(first_hits.shape[0]),
        "lidar_configured_targets": configured_targets,
        "lidar_loaded_mesh_count": loaded_mesh_count,
        "lidar_resolved_terrain_prims": resolved_target_prims,
        "lidar_first_scan_finite_hits": int(finite_first.sum().item()),
        "lidar_first_scan_non_ground_hits": non_ground_first,
        "lidar_first_scan_range_min_m": float(first_ranges.min().item()),
        "lidar_first_scan_range_max_m": float(first_ranges.max().item()),
        "command_limits": {
            "max_vx_mps": args.max_vx, "max_vy_mps": args.max_vy,
            "max_wz_radps": args.max_wz,
            "max_horizontal_norm_mps": args.max_horizontal_norm,
            "watchdog_seconds": args.watchdog_seconds,
        },
        "command_ownership": (
            "SCAN closed_loop_controller only. No PCT lookahead follower exists in "
            "this entry point; the route is a planner input, never a command source."
        ),
        "clock_domains": {
            "telemetry_timestamp": "Isaac simulation time in nanoseconds",
            "command_freshness": "local monotonic wall time at both ends",
        },
        "terrain_filter": {
            "enabled": not args.unfiltered_planner_cloud,
            "cell_size_m": args.terrain_filter_cell_size,
            "height_threshold_m": args.terrain_filter_height_threshold,
            "neighbor_cells": args.terrain_filter_neighbor_cells,
            "minimum_neighbor_cells": args.terrain_filter_minimum_neighbor_cells,
            "method": ("measured returns, frame/range conversion only"
                       if args.unfiltered_planner_cloud else
                       "split_geometry_cloud_points local same-level separation"),
        },
        "telemetry_port": args.telemetry_port,
        "command_port": args.command_port,
        "seed": helper_args.seed,
        "autoreset_allowed": False,
        "duration_seconds": args.duration_seconds,
        "actor_obs_shape": list(observation["policy"].shape),
    }
    config_sha256 = canonical_config_sha256(identity)
    identity["config_sha256"] = config_sha256.hex()
    write_json(args.output / "runtime_identity.json", identity)

    events = TrialEvents()
    events.install(env, robot)

    video_path = args.output / "third_person_master.mp4"
    capture_stride = max(1, int(args.camera_capture_stride))
    # Real-time playback requires the container rate to match the capture rate.
    # A silent mismatch would make the delivered video a different length from
    # the episode it claims to show.
    capture_fps = 1.0 / (float(env.step_dt) * capture_stride)
    if abs(capture_fps - float(args.video_fps)) > 1e-6:
        raise AdapterFailure(
            f"--video-fps {args.video_fps} does not match the capture rate "
            f"{capture_fps} implied by step_dt {float(env.step_dt)} and stride "
            f"{capture_stride}"
        )
    writer = imageio.get_writer(
        str(video_path), fps=args.video_fps, codec="libx264", quality=8, macro_block_size=None
    )
    # One constant identity for this process. A consumer latches the first epoch
    # it sees, so a packet replayed from an earlier run can never be mistaken
    # for current state.
    run_epoch_ns = time.time_ns()
    recorder = AsyncRecorder(max_pending=64) if args.async_recording else None
    metrics_path = args.output / "metrics.jsonl"
    sensor_path = args.output / "sensor_metrics.jsonl"
    cloud_path = args.output / "clouds.jsonl"
    camera_frames_path = args.output / "camera_frames.jsonl"

    status = "DURATION_REACHED"
    records: list[dict] = []
    previous_actions = torch.zeros((1, 12), device=env.device)
    telemetry_sequence = 0
    state_sequence = 0
    complete_state_frames = 0
    complete_state_dropped = 0
    scan_index = 0
    dropped_frames = 0
    first_nonzero_command_s = None
    goal_reached_s = None
    terminal_window_start_s = None
    terminal_window_satisfied_s = None
    max_command_obs_error = 0.0
    nonfoot_events: list[dict] = []
    frame_luminance_std: list[float] = []
    camera_frame_index = 0
    wall_start = time.monotonic()

    command_server.start()
    telemetry_server.start()
    connection_deadline = time.monotonic() + args.connection_ready_timeout_seconds
    while time.monotonic() < connection_deadline:
        if (
            command_server.stats().accepted_connections > 0
            and telemetry_server.stats().accepted_connections > 0
        ):
            break
        time.sleep(0.01)
    else:
        raise AdapterFailure("Foxy bridge did not connect before the ready timeout")
    connected_wall_s = time.monotonic() - wall_start

    for _ in range(8):
        env.sim.render()

    initial_sim_time = float(env.sim.current_time)
    # F8: the run's absolute simulation origin is recorded rather than inferred
    # later from the first published plan. It is written to its own file so the
    # pre-run `runtime_identity.json` and the `config_sha256` computed over it
    # both stay exactly as transmitted.
    write_json(args.output / "run_clock.json", {
        "schema_version": 2,
        "simulation_origin_s": initial_sim_time,
        "simulation_origin_ns": int(round(initial_sim_time * 1.0e9)),
        "run_epoch_ns": run_epoch_ns,
        "complete_body_state": bool(args.complete_body_state),
        "complete_body_state_period_s": float(env.step_dt) if args.complete_body_state else None,
        "physics_dt_s": float(env.physics_dt),
        "policy_dt_s": float(env.step_dt),
        "semantics": (
            "metrics.jsonl sim_time_s = Isaac absolute simulation time - "
            "simulation_origin_s. Telemetry timestamp_ns, /clock and B-spline "
            "start stamps are absolute simulation time. The command freshness "
            "domain is local monotonic wall time at both ends and is never "
            "compared against either of these."
        ),
    })
    # Measured on `recovery_stand_probe01`: the control loop stalled ~266 ms
    # every 120 control steps, exactly periodically, and each stall crossed the
    # unchanged 0.25 s feedback deadline and stopped the robot. The period is a
    # fixed allocation count per step, which is a generation-2 collection over
    # Isaac's very large static heap. `gc.freeze()` moves everything allocated
    # during setup into the permanent generation so gen-2 stops rescanning it.
    # Automatic collection stays enabled; only what it has to walk changes. The
    # before/after counters are recorded so the effect is measured, not claimed.
    gc_before = gc.get_stats()
    gc_frozen = 0
    if args.freeze_gc:
        gc.collect()
        gc.freeze()
        gc_frozen = gc.get_freeze_count()
    from .feedback_dropout import FeedbackDropout
    dropout = FeedbackDropout(args.feedback_dropout_start_s, args.feedback_dropout_wall_s)
    case_failure = None
    contact_guard = SubstepContactMonitor(
        stop_on_contact=args.contact_policy == "nonfoot_fatal",
        read_forces=lambda: torch.linalg.vector_norm(
            contact.data.net_forces_w[0], dim=-1).detach().cpu().tolist(),
        clock=lambda: float(env.sim.current_time) - initial_sim_time,
        on_failure=state.latch_case_failure,
        required_substeps=contact_substeps,
        threshold_n=args.nonfoot_contact_threshold,
        nonfoot_indices=nonfoot_ids,
        body_names=list(contact.body_names),
        physics_dt_s=float(env.physics_dt),
    )
    contact_guard.install(env.scene)
    try:
        with metrics_path.open("w", encoding="utf-8") as metrics_file, \
                sensor_path.open("w", encoding="utf-8") as sensor_file, \
                cloud_path.open("w", encoding="utf-8") as cloud_file, \
                camera_frames_path.open("w", encoding="utf-8") as camera_frames_file, \
                ExitStack() as recording_cleanup:
            if recorder is not None:
                # This context exits before the files, including on a physics
                # exception. Pending cloud writes must still have open handles.
                recording_cleanup.callback(recorder.close, timeout_seconds=300.0)
            sensor_stride = max(1, int(round(args.sensor_period / float(env.step_dt))))
            total_steps = int(round(args.duration_seconds / float(env.step_dt)))
            for step in range(total_steps):
                if time.monotonic() - wall_start > args.max_wall_seconds:
                    status = "WALL_TIMEOUT"
                    break
                sim_time = float(env.sim.current_time) - initial_sim_time
                snapshot = command_server.snapshot(time.monotonic_ns())
                command = (snapshot.command.vx, snapshot.command.vy, snapshot.command.wz)
                if args.case == "stand_probe":
                    # A standing qualification probe never forwards motion.
                    command = (0.0, 0.0, 0.0)
                horizontal_norm = math.hypot(command[0], command[1])
                if horizontal_norm > args.max_horizontal_norm + 1e-9:
                    raise AdapterFailure(
                        f"admitted horizontal command norm {horizontal_norm} exceeds the limit"
                    )
                if first_nonzero_command_s is None and max(abs(v) for v in command) > 1e-6:
                    first_nonzero_command_s = sim_time

                term = env.command_manager.get_term("base_velocity")
                term.commands[:, 0] = command[0]
                term.commands[:, 1] = command[1]
                term.commands[:, 2] = command[2]
                contact_guard.begin(step)
                try:
                    observation, _, dones, _ = wrapped.step(previous_actions)
                    contact_guard.end()
                except SubstepContactStop as exc:
                    case_failure = exc.failure
                    sim_time = float(env.sim.current_time) - initial_sim_time
                    position = robot.data.root_pos_w[0].detach().cpu().numpy().copy()
                    quaternion = robot.data.root_quat_w[0].detach().cpu().tolist()
                    # The guard raises from inside the scene update that already
                    # completed the offending substep, so the simulator state read
                    # here IS that substep's state. Reading tensors advances
                    # nothing; no step, render, reset or write is performed. The
                    # last guard sample is the force row that latched the failure.
                    fatal_state = {
                        "note": (
                            "Actual state at the latched fatal substep, read "
                            "without advancing physics. Not a later sample and "
                            "not an interpolation."
                        ),
                        "substep_sim_time_s": case_failure.substep_sim_time_s,
                        "joint_names": list(robot.joint_names),
                        "joint_pos": robot.data.joint_pos[0].detach().cpu().tolist(),
                        "joint_vel": robot.data.joint_vel[0].detach().cpu().tolist(),
                        "applied_torque": robot.data.applied_torque[0].detach().cpu().tolist(),
                        "base_linear_velocity_world": robot.data.root_lin_vel_w[0].detach().cpu().tolist(),
                        "base_angular_velocity_world": robot.data.root_ang_vel_w[0].detach().cpu().tolist(),
                        "base_linear_velocity_body": robot.data.root_lin_vel_b[0].detach().cpu().tolist(),
                        "base_angular_velocity_body": robot.data.root_ang_vel_b[0].detach().cpu().tolist(),
                        "gravity_b": robot.data.projected_gravity_b[0].detach().cpu().tolist(),
                        "foot_names": list(foot_names),
                        "foot_positions": robot.data.body_pos_w[0, body_foot_ids].detach().cpu().tolist(),
                        "contact_body_names": list(contact.body_names),
                        "contact_force_norms_at_fatal_substep": (
                            list(contact_guard.samples[-1]) if contact_guard.samples else None
                        ),
                        "contact_force_norms_post_update": torch.linalg.vector_norm(
                            contact.data.net_forces_w[0], dim=-1
                        ).detach().cpu().tolist(),
                        "substep_force_rows_this_control_step": [
                            list(sample) for sample in contact_guard.samples
                        ],
                    }
                    # A latched physical failure ends the trial. State and error
                    # evidence are preserved, no pose reset or retry happens,
                    # and the consumer is told through the existing status
                    # fields before the transport is closed.
                    status = "CASE_FAILED_NONFOOT_CONTACT"
                    metrics_file.flush()
                    write_json(args.output / "case_failure.json", {
                        "schema_version": 1,
                        "case": args.case,
                        "reason": "nonfoot_contact_above_threshold",
                        "termination_code": case_failure.termination_code,
                        "contact": case_failure.as_record(),
                        "guard": contact_guard.as_record(),
                        "sim_time_s": sim_time,
                        "physics_steps_after_failure": 0,
                        "contact_substeps_inspected": len(contact_guard.samples),
                        "base_xyz": position.tolist(),
                        "base_quat_wxyz": quaternion,
                        "fatal_substep_state": fatal_state,
                        "admitted_command_at_failure": list(command),
                        "command_state_reason": state.snapshot(
                            time.monotonic_ns()
                        ).reason,
                        "reset_performed": False,
                        "note": (
                            "The simulation case is latched failed. Command "
                            "admission is disabled for the rest of this process "
                            "and no further physics step is taken."
                        ),
                    })
                    telemetry_sequence += 1
                    dropped_frames += int(not telemetry_server.publish(encode_frame(
                        MessageType.STATUS_V1,
                        telemetry_sequence,
                        int(float(env.sim.current_time) * 1.0e9),
                        encode_status_payload(StatusV1(
                            physics_hz=1.0 / float(env.physics_dt),
                            policy_hz=1.0 / float(env.step_dt),
                            sensor_hz=1.0 / args.sensor_period,
                            bridge_latency_ms=0.0,
                            contact_count=0,
                            dropped_frames=dropped_frames,
                            watchdog_events=snapshot.watchdog_events,
                            flags=int(StatusFlag.COLLISION) | int(StatusFlag.TERMINATED),
                            termination_code=case_failure.termination_code,
                        )),
                    )))
                    break

                except TrialStateMutation as exc:
                    status = "TERMINATED"
                    sim_time = float(env.sim.current_time) - initial_sim_time
                    write_json(args.output / "termination.json", {
                        "sim_time_s": sim_time,
                        "reason": str(exc),
                        "base_xyz": robot.data.root_pos_w[0].detach().cpu().tolist(),
                        "terms": env.termination_manager._term_dones.detach().cpu().tolist(),
                        "contact_body_names": list(contact.body_names),
                        "contact_force_rows": [list(row) for row in contact_guard.samples],
                        "guard": contact_guard.as_record(),
                    })
                    break
                policy_state.reset(dones)
                if bool(dones.any()):
                    status = "TERMINATED"
                    break
                actual_command = env.command_manager.get_command("base_velocity")
                expected_command = actual_command.new_tensor([command])
                if not torch.allclose(actual_command, expected_command, atol=1e-6, rtol=0.0):
                    raise AdapterFailure("V12 command drifted after the physics step")
                _, command_obs_error, _ = v12._policy_command_evidence(observation, command)
                max_command_obs_error = max(max_command_obs_error, command_obs_error)
                with torch.inference_mode():
                    actions = policy(observation)
                if tuple(actions.shape) != (1, 12):
                    raise AdapterFailure(f"V12 action shape {tuple(actions.shape)} != (1, 12)")
                if not torch.isfinite(actions).all() or not torch.isfinite(observation["policy"]).all():
                    status = "NONFINITE"
                    break
                previous_actions = actions

                sim_time = float(env.sim.current_time) - initial_sim_time
                position = robot.data.root_pos_w[0].detach().cpu().numpy().copy()
                quaternion = robot.data.root_quat_w[0].detach().cpu().numpy()
                qw, qx, qy, qz = (float(value) for value in quaternion)
                yaw = math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
                roll = math.atan2(2 * (qw * qx + qy * qz), 1 - 2 * (qx * qx + qy * qy))
                pitch = math.asin(max(-1.0, min(1.0, 2 * (qw * qy - qz * qx))))
                linear_body = robot.data.root_lin_vel_b[0].detach().cpu().numpy()
                angular_body = robot.data.root_ang_vel_b[0].detach().cpu().numpy()
                linear_world = robot.data.root_lin_vel_w[0].detach().cpu().numpy()
                angular_world = robot.data.root_ang_vel_w[0].detach().cpu().numpy()
                forces = torch.linalg.vector_norm(contact.data.net_forces_w[0], dim=-1)
                nonfoot_max = float(forces[nonfoot_ids].max().item()) if nonfoot_ids else 0.0
                nonfoot_substep_max = max(
                    (sample[index] for sample in contact_guard.samples for index in nonfoot_ids),
                    default=0.0,
                )
                horizontal_speed = float(math.hypot(linear_world[0], linear_world[1]))
                goal_error_xy = float(np.linalg.norm(position[:2] - goal_ground[:2]))
                goal_layer_error = float(
                    abs((position[2] - body_height) - goal_ground[2])
                )

                for substep_index, sample in enumerate(contact_guard.samples):
                    if not nonfoot_ids:
                        continue
                    body_index = max(nonfoot_ids, key=lambda index: sample[index])
                    if sample[body_index] >= args.nonfoot_contact_threshold:
                        nonfoot_events.append({
                            "sim_time_s": sim_time - (len(contact_guard.samples) - 1 - substep_index) * float(env.physics_dt),
                            "force_n": sample[body_index],
                            "body": contact.body_names[body_index],
                            "step": step,
                            "substep_index": substep_index,
                            "contact_policy": args.contact_policy,
                        })

                row = {
                    "step": step,
                    "sim_time_s": sim_time,
                    "monotonic_s": time.monotonic() - wall_start,
                    "base_xyz": position.tolist(),
                    "base_quat_wxyz": [qw, qx, qy, qz],
                    "base_rpy_rad": [roll, pitch, yaw],
                    "base_linear_velocity_body": linear_body.tolist(),
                    "base_angular_velocity_body": angular_body.tolist(),
                    "base_linear_velocity_world": linear_world.tolist(),
                    "base_angular_velocity_world": angular_world.tolist(),
                    "horizontal_speed_mps": horizontal_speed,
                    "yaw_rate_radps": float(angular_world[2]),
                    "raw_command": [snapshot.command.vx, snapshot.command.vy, snapshot.command.wz],
                    "admitted_command": list(command),
                    "command_horizontal_norm_mps": horizontal_norm,
                    "command_sequence": snapshot.sequence,
                    "command_stale": snapshot.stale,
                    "command_reason": snapshot.reason,
                    "command_watchdog_events": snapshot.watchdog_events,
                    "command_sequence_gaps": snapshot.sequence_gaps,
                    "command_obs_error": command_obs_error,
                    "joint_pos": robot.data.joint_pos[0].detach().cpu().tolist(),
                    "joint_vel": robot.data.joint_vel[0].detach().cpu().tolist(),
                    "applied_torque": robot.data.applied_torque[0].detach().cpu().tolist(),
                    "foot_force_norms": forces[foot_ids].detach().cpu().tolist(),
                    "nonfoot_force_max_n": nonfoot_max,
                    "nonfoot_force_substep_max_n": nonfoot_substep_max,
                    "contact_substeps_inspected": len(contact_guard.samples),
                    "substep_contact_force_norms_n": contact_guard.samples,
                    "foot_positions": robot.data.body_pos_w[0, body_foot_ids].detach().cpu().tolist(),
                    "action_max": float(actions.abs().max()),
                    "gravity_b": robot.data.projected_gravity_b[0].detach().cpu().tolist(),
                    "goal_error_xy_m": goal_error_xy,
                    "goal_layer_error_m": goal_layer_error,
                }
                # ---- complete body state, every control step ---------------
                # Position, orientation and both twist representations all come
                # from the physics update that has just completed, so a consumer
                # never has to pair a fresh velocity with an older pose. This is
                # deliberately outside the sensor-stride branch below: odometry
                # freshness must not inherit the point-cloud cadence.
                if args.complete_body_state:
                    state_sequence += 1
                    state_sample_ns = time.monotonic_ns()
                    withheld = dropout.suppress(sim_time, state_sample_ns, state_sequence)
                    row.update({"state_sequence": state_sequence,
                                "state_sample_monotonic_ns": state_sample_ns,
                                "state_withheld_by_probe": withheld})
                    if not withheld:
                        telemetry_sequence += 1
                    control_state_timestamp_ns = int(float(env.sim.current_time) * 1.0e9)
                    frame = encode_frame(
                        MessageType.BODY_STATE_V2,
                        telemetry_sequence,
                        control_state_timestamp_ns,
                        encode_body_state_v2_payload(BodyStateV2(
                            position_world=tuple(float(v) for v in position),
                            orientation_world_xyzw=quaternion_wxyz_to_xyzw(
                                [qw, qx, qy, qz]
                            ),
                            linear_velocity_world=tuple(float(v) for v in linear_world),
                            angular_velocity_world=tuple(float(v) for v in angular_world),
                            linear_velocity_body=tuple(float(v) for v in linear_body),
                            angular_velocity_body=tuple(float(v) for v in angular_body),
                            simulation_time_ns=control_state_timestamp_ns,
                            state_sequence=state_sequence,
                            run_epoch_ns=run_epoch_ns,
                        )),
                    )
                    if not withheld:
                        published = telemetry_server.publish(frame)
                        dropped_frames += int(not published)
                        complete_state_frames += 1
                        complete_state_dropped += int(not published)

                records.append(row)
                metrics_file.write(json.dumps(row, sort_keys=True) + "\n")

                # ---- terminal-window bookkeeping (observation only) --------
                if goal_reached_s is None and goal_error_xy <= args.goal_tolerance_m:
                    goal_reached_s = sim_time
                terminal_ok = (
                    horizontal_norm <= args.terminal_command_norm
                    and abs(command[2]) <= args.terminal_command_norm
                    and horizontal_speed <= args.terminal_speed_mps
                    and abs(float(angular_world[2])) <= args.terminal_yaw_rate_radps
                    and goal_error_xy <= args.goal_tolerance_m
                )
                if terminal_ok:
                    if terminal_window_start_s is None:
                        terminal_window_start_s = sim_time
                    elif (
                        terminal_window_satisfied_s is None
                        and sim_time - terminal_window_start_s >= args.terminal_window_seconds
                    ):
                        terminal_window_satisfied_s = sim_time
                else:
                    terminal_window_start_s = None

                # ---- sensing and telemetry --------------------------------
                if step % sensor_stride == 0:
                    lidar.update(dt=0.0, force_recompute=True)
                    hits = lidar.data.ray_hits_w[0]
                    sensor_position_values, sensor_quaternion_values = mounted_sensor_pose(
                        lidar.data.pos_w[0].detach().cpu().tolist(),
                        lidar.data.quat_w[0].detach().cpu().tolist(),
                        lidar.cfg.offset.pos, lidar.cfg.offset.rot)
                    sensor_position = hits.new_tensor(sensor_position_values)
                    timestamp_ns = int(float(env.sim.current_time) * 1.0e9)
                    world_hits = hits.detach().cpu().tolist()
                    if args.unfiltered_planner_cloud:
                        raw_points = world_hits_to_sensor_points(
                            world_hits, sensor_position_values, sensor_quaternion_values,
                            args.lidar_min_range, args.lidar_max_range,
                            minimum_world_z=None)
                        planner_points = raw_points
                        filter_stats = {
                            "input_hit_count": len(world_hits),
                            "finite_in_range_hit_count": len(raw_points),
                            "obstacle_hit_count": len(raw_points),
                            "filtered_ground_hit_count": 0,
                            "sparse_retained_hit_count": 0,
                            "terrain_filter_enabled": False,
                        }
                    else:
                        raw_points, planner_points, filter_stats = split_geometry_cloud_points(
                            world_hits,
                            sensor_position_values,
                            sensor_quaternion_values,
                            args.lidar_min_range,
                            args.lidar_max_range,
                            args.terrain_filter_cell_size,
                            args.terrain_filter_height_threshold,
                            args.terrain_filter_neighbor_cells,
                            args.terrain_filter_minimum_neighbor_cells,
                        )
                    raw_count, raw_bytes = pack_xyz_points(raw_points)
                    planner_count, planner_bytes = pack_xyz_points(planner_points)
                    scan_index += 1
                    finite = torch.isfinite(hits).all(dim=-1)
                    ranges = torch.linalg.vector_norm(
                        hits - sensor_position.unsqueeze(0), dim=-1
                    )
                    environment = finite & (ranges >= args.lidar_min_range)
                    sensor_row = {
                        "scan_id": scan_index,
                        "sim_time_s": sim_time,
                        "timestamp_ns": timestamp_ns,
                        "sensor_position": sensor_position_values,
                        "sensor_quaternion_wxyz": sensor_quaternion_values,
                        "body_position": position.tolist(),
                        "ray_count": int(hits.shape[0]),
                        "finite_hit_count": int(finite.sum().item()),
                        "environment_hit_count": int(environment.sum().item()),
                        "raw_point_count": raw_count,
                        "planner_point_count": planner_count,
                        "non_ground_hit_count": int(
                            (hits[finite][:, 2] > float(start_ground[2]) + 0.25).sum().item()
                        ),
                        "environment_range_min_m": (
                            float(ranges[environment].min().item())
                            if int(environment.sum().item()) else None
                        ),
                        "environment_range_max_m": (
                            float(ranges[environment].max().item())
                            if int(environment.sum().item()) else None
                        ),
                        "filter_stats": dict(filter_stats),
                    }
                    sensor_file.write(json.dumps(sensor_row, sort_keys=True) + "\n")
                    if scan_index % max(1, args.cloud_record_stride) == 0:
                        cloud_row = {
                            "scan_id": scan_index,
                            "sim_time_s": sim_time,
                            "sensor_position": sensor_position_values,
                            "sensor_quaternion_wxyz": sensor_quaternion_values,
                            "raw_points_sensor_frame": raw_points,
                            "planner_points_sensor_frame": planner_points,
                        }
                        # Serialising ~125 kB of points per scan is the second
                        # largest recording cost after encoding. It carries no
                        # ordering relationship to physics, so it is queued.
                        def _write_cloud(row=cloud_row, handle=cloud_file):
                            row["raw_points_sensor_frame"] = [
                                [round(float(v), 4) for v in point]
                                for point in row["raw_points_sensor_frame"]
                            ]
                            row["planner_points_sensor_frame"] = [
                                [round(float(v), 4) for v in point]
                                for point in row["planner_points_sensor_frame"]
                            ]
                            handle.write(json.dumps(row, sort_keys=True) + "\n")

                        if recorder is not None:
                            recorder.submit(_write_cloud)
                        else:
                            _write_cloud()

                    telemetry_sequence += 1
                    dropped_frames += int(not telemetry_server.publish(encode_frame(
                        MessageType.SENSOR_FRAME_DUAL_CLOUD_V1,
                        telemetry_sequence,
                        timestamp_ns,
                        encode_dual_cloud_sensor_payload(DualCloudSensorFrameV1(
                            body_position=tuple(float(v) for v in position),
                            body_quaternion_xyzw=quaternion_wxyz_to_xyzw([qw, qx, qy, qz]),
                            sensor_position=tuple(float(v) for v in sensor_position_values),
                            sensor_quaternion_xyzw=quaternion_wxyz_to_xyzw(
                                sensor_quaternion_values
                            ),
                            config_sha256=config_sha256,
                            scan_id=scan_index,
                            raw_point_count=raw_count,
                            raw_points_xyz_f32_be=raw_bytes,
                            planner_point_count=planner_count,
                            planner_points_xyz_f32_be=planner_bytes,
                            filtered_ground_point_count=filter_stats["filtered_ground_hit_count"],
                            conservative_retained_point_count=filter_stats[
                                "sparse_retained_hit_count"
                            ],
                        )),
                    )))

                    # Legacy velocity-only state keeps the sensor cadence. It
                    # is superseded by BODY_STATE_V2 above, so it is emitted
                    # only when the complete channel is off; a legacy scope is
                    # then byte-identical to the previous runner.
                    if not args.complete_body_state:
                        state_sequence += 1
                        telemetry_sequence += 1
                        dropped_frames += int(not telemetry_server.publish(encode_frame(
                            MessageType.BODY_STATE_V1,
                            telemetry_sequence,
                            timestamp_ns,
                            encode_body_state_payload(BodyStateV1(
                                linear_velocity_world=tuple(
                                    float(v) for v in linear_world
                                ),
                                angular_velocity_world=tuple(
                                    float(v) for v in angular_world
                                ),
                                linear_velocity_body=tuple(
                                    float(v) for v in linear_body
                                ),
                                angular_velocity_body=tuple(
                                    float(v) for v in angular_body
                                ),
                                simulation_time_ns=timestamp_ns,
                                state_sequence=state_sequence,
                            )),
                        )))

                    telemetry_sequence += 1
                    dropped_frames += int(not telemetry_server.publish(encode_frame(
                        MessageType.JOINT_STATE_V1,
                        telemetry_sequence,
                        timestamp_ns,
                        encode_joint_state_payload(JointStateV1(
                            names=tuple(str(name) for name in robot.joint_names),
                            positions=tuple(
                                float(v) for v in robot.data.joint_pos[0].detach().cpu().tolist()
                            ),
                            velocities=tuple(
                                float(v) for v in robot.data.joint_vel[0].detach().cpu().tolist()
                            ),
                        )),
                    )))

                    flags = 0
                    contact_count = int(
                        (forces[foot_ids] >= args.contact_force_threshold).sum().item()
                    )
                    if contact_count >= 2:
                        flags |= int(StatusFlag.CONTACT_SUPPORTED)
                    if nonfoot_max >= args.nonfoot_contact_threshold:
                        flags |= int(StatusFlag.COLLISION)
                    telemetry_sequence += 1
                    dropped_frames += int(not telemetry_server.publish(encode_frame(
                        MessageType.STATUS_V1,
                        telemetry_sequence,
                        timestamp_ns,
                        encode_status_payload(StatusV1(
                            physics_hz=1.0 / float(env.physics_dt),
                            policy_hz=1.0 / float(env.step_dt),
                            sensor_hz=1.0 / args.sensor_period,
                            bridge_latency_ms=0.0 if snapshot.source_timestamp_ns is None else
                            max(0.0, (time.monotonic_ns() - snapshot.source_timestamp_ns) / 1.0e6),
                            contact_count=contact_count,
                            dropped_frames=dropped_frames,
                            watchdog_events=snapshot.watchdog_events,
                            flags=flags,
                            termination_code=0,
                        )),
                    )))

                # ---- third-person capture, world-side camera only ---------
                if step % capture_stride == 0:
                    heading = np.array([math.cos(yaw), math.sin(yaw), 0.0])
                    side = np.array([-math.sin(yaw), math.cos(yaw), 0.0])
                    camera_eye = (
                        position
                        - args.camera_trail_m * heading
                        + args.camera_lateral_m * side
                        + np.array([0.0, 0.0, args.camera_height_m])
                    )
                    camera_target = (
                        position
                        + args.camera_look_ahead_m * heading
                        - np.array([0.0, 0.0, args.camera_look_down_m])
                    )
                    env.sim.set_camera_view(eye=camera_eye, target=camera_target)
                    # Isaac owns the rendering API, so render() stays on this
                    # thread. Only the H.264 encode and the contrast statistic
                    # are queued; frames therefore still reach the writer in
                    # capture order because the recorder is a single worker.
                    frame = raw_env.render()
                    # Display-only pose log, written on this thread in capture
                    # order so row N describes master frame N. Offline
                    # composition pairs each frame to telemetry by this
                    # simulation stamp instead of by wall time, and projects the
                    # overlay with this exact eye/target pair.
                    camera_frames_file.write(json.dumps({
                        "frame_index": camera_frame_index,
                        "step": step,
                        "sim_time_s": sim_time,
                        "eye_xyz": [float(v) for v in camera_eye],
                        "target_xyz": [float(v) for v in camera_target],
                        "up_axis": [0.0, 0.0, 1.0],
                        "base_xyz": [float(v) for v in position],
                        "yaw_rad": float(yaw),
                    }) + "\n")
                    camera_frame_index += 1

                    def _encode_frame(captured=frame):
                        writer.append_data(captured)
                        # A camera that ends up behind a wall renders a flat
                        # field. Record the per-frame contrast so an unusable
                        # capture is detected from the run's own evidence, not
                        # after delivery.
                        luminance = np.asarray(captured, dtype=np.float32)
                        if luminance.ndim == 3:
                            luminance = luminance[..., :3].mean(axis=2)
                        frame_luminance_std.append(float(luminance.std()))

                    if recorder is not None:
                        recorder.submit(_encode_frame)
                    else:
                        _encode_frame()

                if step % 100 == 0:
                    print(json.dumps({
                        "sim_time_s": round(sim_time, 2),
                        "xyz": [round(float(v), 3) for v in position],
                        "command": [round(float(v), 4) for v in command],
                        "goal_error_xy_m": round(goal_error_xy, 3),
                        "scan_id": scan_index,
                    }), flush=True)

                if (args.contact_policy != "native_v12"
                        and robot.data.projected_gravity_b[0, 2].item() > -0.5):
                    status = "EXCESSIVE_TILT"
                    break
                if (
                    terminal_window_satisfied_s is not None
                    and sim_time - terminal_window_satisfied_s > 0.5
                ):
                    status = "GOAL_REACHED_AND_STOPPED"
                    break
    finally:
        # Stop live command and telemetry transport before slow teardown. The
        # priority sender is drained first so queued state and status frames
        # are not lost at shutdown.
        telemetry_server.drain(timeout_seconds=5.0)
        transport_metrics = telemetry_server.queue_metrics()
        command_server.stop()
        telemetry_server.stop()
        # Every queued encode and evidence write is completed before the video
        # file is closed. A writer failure raises here rather than silently
        # truncating the record.
        # Wall-clock spacing of the control loop itself. This is the quantity
        # the 0.25 s feedback deadline is actually measured against, so it is
        # reported with percentiles rather than as a mean.
        control_loop_timing = None
        if len(records) > 1:
            spacing = sorted(
                later["monotonic_s"] - earlier["monotonic_s"]
                for earlier, later in zip(records, records[1:])
            )

            def _quantile(fraction):
                index = min(len(spacing) - 1, int(len(spacing) * fraction))
                return spacing[index]

            control_loop_timing = {
                "samples": len(spacing),
                "p50_s": _quantile(0.50),
                "p95_s": _quantile(0.95),
                "p99_s": _quantile(0.99),
                "max_s": spacing[-1],
                "over_freshness_deadline_count": sum(1 for value in spacing if value > 0.25),
                "freshness_deadline_s": 0.25,
            }
        recorder_metrics = None
        if recorder is not None:
            recorder.close(timeout_seconds=300.0)
            recorder_metrics = recorder.metrics()
        writer.close()
        summary = {
            "status": status,
            "case": args.case,
            "record_count": len(records),
            "sim_seconds": float(env.sim.current_time) - initial_sim_time,
            "recorded_control_seconds": len(records) * float(env.step_dt),
            "wall_seconds": time.monotonic() - wall_start,
            "bridge_connected_wall_s": connected_wall_s,
            "scan_count": scan_index,
            "telemetry_frames": telemetry_sequence,
            "dropped_telemetry_frames": dropped_frames,
            "complete_body_state": {
                "enabled": bool(args.complete_body_state),
                "frames_published": complete_state_frames,
                "frames_dropped": complete_state_dropped,
                "run_epoch_ns": run_epoch_ns,
                "last_state_sequence": state_sequence,
                "period_s": float(env.step_dt),
                "message": "BODY_STATE_V2 id 8, !19dQQQ, 176 bytes, network byte order",
            },
            "telemetry_transport": transport_metrics,
            "feedback_dropout": dropout.record(),
            "recording_load": recorder_metrics,
            "control_loop_timing": control_loop_timing,
            "garbage_collection": {
                "freeze_requested": bool(args.freeze_gc),
                "frozen_objects": gc_frozen,
                "collections_before": [entry["collections"] for entry in gc_before],
                "collections_after": [entry["collections"] for entry in gc.get_stats()],
            },
            "first_nonzero_command_s": first_nonzero_command_s,
            "goal_reached_s": goal_reached_s,
            "terminal_window_satisfied_s": terminal_window_satisfied_s,
            "maximum_command_obs_error": max_command_obs_error,
            "nonfoot_contact_events_over_threshold": nonfoot_events,
            "contact_guard": contact_guard.as_record(),
            "case_failed": case_failure is not None,
            "contact_policy": args.contact_policy,
            "case_failure_reason": (
                "nonfoot_contact_above_threshold" if case_failure is not None else None
            ),
            "termination_code": (
                case_failure.termination_code if case_failure is not None else 0
            ),
            "command_watchdog_events": records[-1]["command_watchdog_events"] if records else None,
            "command_sequence_gaps": records[-1]["command_sequence_gaps"] if records else None,
            **events.as_record(),
            "claim": identity["claim"],
            "video_master": str(video_path),
            "camera": {
                "trail_m": args.camera_trail_m,
                "lateral_m": args.camera_lateral_m,
                "height_m": args.camera_height_m,
                "look_ahead_m": args.camera_look_ahead_m,
                "look_down_m": args.camera_look_down_m,
                "capture_stride_steps": capture_stride,
                "capture_fps": capture_fps,
                "pose_log": str(camera_frames_path),
                "pose_rows": camera_frame_index,
                "intrinsics": camera_intrinsics,
                "note": "world-side follow camera; observes only, changes no robot state",
            },
            "video_frame_contrast": {
                "frames": len(frame_luminance_std),
                "luminance_std_min": min(frame_luminance_std) if frame_luminance_std else None,
                "luminance_std_mean": (
                    sum(frame_luminance_std) / len(frame_luminance_std)
                    if frame_luminance_std
                    else None
                ),
                "featureless_frames_below_std_8": sum(
                    1 for value in frame_luminance_std if value < 8.0
                ),
            },
        }
        if records:
            positions = np.array([row["base_xyz"] for row in records])
            summary.update({
                "start_xyz": positions[0].tolist(),
                "end_xyz": positions[-1].tolist(),
                "travel_xy_m": float(
                    np.linalg.norm(np.diff(positions[:, :2], axis=0), axis=1).sum()
                ),
                "final_goal_error_xy_m": records[-1]["goal_error_xy_m"],
                "final_goal_layer_error_m": records[-1]["goal_layer_error_m"],
                "max_horizontal_speed_mps": max(r["horizontal_speed_mps"] for r in records),
                "max_abs_roll_deg": math.degrees(max(abs(r["base_rpy_rad"][0]) for r in records)),
                "max_abs_pitch_deg": math.degrees(max(abs(r["base_rpy_rad"][1]) for r in records)),
                # A fatal impact can occur before the enclosing control record
                # is completed. The substep guard includes that final impact.
                "max_nonfoot_force_n": contact_guard.as_record()["maximum_nonfoot_force_n"],
                "max_admitted_command_norm_mps": max(
                    r["command_horizontal_norm_mps"] for r in records
                ),
            })
        write_json(args.output / "summary.json", summary)
        print(json.dumps(summary, indent=2), flush=True)
        contact_guard.restore()
        events.restore()
        raw_env.close()
    # A latched physical failure is a failed trial, not a completed one.
    return trial_exit_code(status)


if __name__ == "__main__":
    raise SystemExit(main())

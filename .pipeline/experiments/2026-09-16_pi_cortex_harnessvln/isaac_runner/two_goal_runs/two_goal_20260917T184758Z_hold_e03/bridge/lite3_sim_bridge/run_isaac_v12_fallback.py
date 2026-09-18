"""Qualify the one allowed V12 model_149999 fallback in its pinned runtime."""

from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import random
import subprocess
import time
from typing import Mapping, Optional, Union
import xml.etree.ElementTree as ET

from .command_state import CommandLimits, LatestCommandState
from .isaac_adapter_core import (
    DEFAULT_QUALIFICATION_SCHEDULE,
    DynamicObstacleSpec,
    QualificationSegment,
    canonical_config_sha256,
    circle_surface_clearance_2d,
    dynamic_obstacle_state,
    expand_isaac_env_regex_ns,
    local_minimum_obstacle_hits,
    official_human_registered_state,
    point_to_segment_distance_2d,
    procedural_human_gait_angles,
    quaternion_wxyz_to_xyzw,
    schedule_duration,
    schedule_state,
    segment_to_aabb_clearance_2d,
    split_geometry_cloud_points,
    terrain_seating_for_mesh_support,
    world_hits_to_sensor_points,
)
from .mid360_pattern import (
    MID360_MAX_RANGE_M,
    MID360_MIN_RANGE_M,
    MID360_POINTS_PER_SCAN,
    MID360_SCAN_HZ,
    Mid360PatternError,
    load_mid360_pattern,
)
from .protocol import (
    DualCloudSensorFrameV1,
    JointStateV1,
    MessageType,
    SensorFrameV1,
    StatusFlag,
    StatusV1,
    encode_frame,
    encode_dual_cloud_sensor_payload,
    encode_joint_state_payload,
    encode_sensor_payload,
    encode_status_payload,
    pack_xyz_points,
)
from .official_human_contract import (
    BIPED_URL as OFFICIAL_HUMAN_BIPED_URL,
    CHARACTER_URL as OFFICIAL_HUMAN_CHARACTER_URL,
    cache_content_sha256 as official_human_cache_content_sha256,
)
from .office_crowd_contract import (
    office_pedestrian_state,
    pairwise_clearance_precheck,
    routes_from_preflight,
)
from .run_isaac_lite3 import (
    AdapterFailure,
    _QualificationSender,
    _TelemetrySink,
    _qualification_report,
    _sha256,
    _tensor_list,
    _write_json,
)
from .transport import CommandReceiverServer, TelemetryPublisherServer


PINNED_SOURCE_COMMIT = "8c3fdffa84b85be0704a10ea5b2533817d543822"
PINNED_CHECKPOINT_SHA256 = (
    "a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450"
)
PINNED_SENSOR_RIG_CANONICAL_SHA256 = (
    "d0a1be09f018c0ab31df26f69ad8e700bd88ec06ae5b0f4dfbcc4fddf21cec80"
)
PINNED_SENSOR_RIG_ISAAC_SHA256 = (
    "803d552703bcc4f72ce15f38b95bc3f62e3e4ada0b42bf3ecf71b32b6590bb9d"
)
PINNED_V12_ROBOT_ASSET_SHA256 = (
    "178428b97e7d0820e93c200b333f39f0b3b60a81f97d99cd06559d8957c58865"
)
PINNED_FOREST_GEN_COMMIT = "a75fb28c7b896e2a67e2d889b804732d33c56e0c"
PINNED_STRIPE_KIT_COMMIT = "ce97eed40d9fc4927c4856eda6a17204d01087db"
DEFAULT_TASK = "Wave-C-Stairs-V12-Lite3-v0"
POLICY_OBSERVATION_DIMENSION = 450
COMMAND_HISTORY_OFFSET = 60
COMMAND_HISTORY_LENGTH = 10
COURSE_OBSTACLE_CENTER = (2.0, 0.0, 0.4)
COURSE_OBSTACLE_SIZE = (0.6, 1.2, 0.8)
GROUND_MESH_PRIM = "/World/ground"
OBSTACLE_MESH_PRIM = "/World/ground/scan_obstacle"
VIDEO_CAMERA_EYE = (2.0, -5.5, 3.2)
VIDEO_CAMERA_LOOKAT = (2.0, 0.0, 0.25)
VIDEO_RESOLUTION = (1280, 720)
FOREST_SIZE_M = 32
FOREST_MARGIN_M = 10
FOREST_SEED = 14
FOREST_TREE_PROXY_RADIUS_M = 0.24
FOREST_TREE_PROXY_HEIGHT_M = 4.0
FOREST_ROCK_PROXY_SIZE_M = (0.72, 0.72, 0.46)
FOREST_ROCK_SEATING_CLEARANCE_M = 0.015
FOREST_ROCK_SUPPORT_BAND_M = 0.020
FOREST_NAVIGATION_GOAL_WORLD_M = (0.5, 3.0, 0.85)
FOREST_NAVIGATION_PLANNING_RADIUS_M = 0.40
OFFICE_STATIC_SCHEDULE = (
    QualificationSegment("office_settle_zero", 4.0, (0.0, 0.0, 0.0)),
)
DYNAMIC_OBSTACLE_PRIM_EXPR = "{ENV_REGEX_NS}/DynamicObstacle"
DYNAMIC_OBSTACLE_RUNTIME_PRIM = "/World/envs/env_0/DynamicObstacle"
DYNAMIC_HUMAN_VISUAL_RUNTIME_PRIM = "/World/DynamicHumanVisual"
OFFICE_PEDESTRIAN_PRIM_PREFIX = "OfficePedestrian"
OFFICE_HUMAN_VISUAL_PREFIX = "/World/OfficeHumanVisual"
DYNAMIC_OBSTACLE_DEFAULT_X_M = -3.0
DYNAMIC_OBSTACLE_DEFAULT_START_Y_M = 1.2
DYNAMIC_OBSTACLE_DEFAULT_END_Y_M = 4.8
DYNAMIC_OBSTACLE_DEFAULT_WAIT_SECONDS = 0.2
DYNAMIC_OBSTACLE_DEFAULT_SPEED_MPS = 0.8
DYNAMIC_OBSTACLE_DEFAULT_RADIUS_M = 0.30
DYNAMIC_OBSTACLE_DEFAULT_HEIGHT_M = 1.50
DYNAMIC_OBSTACLE_DEFAULT_TERRAIN_CLEARANCE_M = 0.02
DYNAMIC_OBSTACLE_DEFAULT_HOLD_FRACTION = 0.5
DYNAMIC_OBSTACLE_DEFAULT_HOLD_SECONDS = 0.0
DYNAMIC_ROUTE_MIN_STATIC_CLEARANCE_M = 0.15
DYNAMIC_HUMAN_PART_NAMES = (
    "Head",
    "Torso",
    "Pelvis",
    "LeftArm",
    "RightArm",
    "LeftLeg",
    "RightLeg",
)
DYNAMIC_HUMAN_GAIT_CADENCE_HZ = 1.6
DYNAMIC_HUMAN_GAIT_MAX_SWING_RADIANS = math.radians(25.0)
DYNAMIC_HUMAN_COLOR_RGB = (1.0, 0.82, 0.02)
OFFICIAL_HUMAN_SOURCE_FOOT_Z_M = -1.9355964298028994e-7
OFFICIAL_HUMAN_SOURCE_VISIBLE_TOP_Z_M = 1.7357525825500488
OFFICIAL_HUMAN_SOURCE_FORWARD_YAW_RADIANS = -math.pi / 2.0
OFFICIAL_HUMAN_CAPSULE_HEIGHT_M = 1.70
OFFICIAL_HUMAN_CAPSULE_RADIUS_M = 0.30
FOREST_PREVIEW_SCHEDULE = (
    QualificationSegment("settle_zero", 1.5, (0.0, 0.0, 0.0)),
    QualificationSegment("forward", 4.0, (0.25, 0.0, 0.0)),
    QualificationSegment("yaw", 3.0, (0.0, 0.0, 0.35)),
    QualificationSegment("stop_zero", 1.5, (0.0, 0.0, 0.0)),
)
MID360_FRAME = "mid360_scan_frame"
D435I_FRAME = "d435i_depth_optical_frame"
SENSOR_RIG_REQUIRED_LINKS = (
    "TORSO",
    "pro_interface_link",
    "sensor_carrier_link",
    "s410_guard_link",
    "mid360_body_link",
    MID360_FRAME,
    "d435i_body_link",
    D435I_FRAME,
)
# The sensor's own housing is deliberately omitted from its ray-cast targets:
# the optical origin is inside that geometry. These are the surrounding bodies
# that can physically occlude each sensor in the pinned assembly.
MID360_SELF_OCCLUSION_LINKS = (
    "TORSO",
    "pro_interface_link",
    "sensor_carrier_link",
    "s410_guard_link",
    "d435i_body_link",
)
D435I_SELF_OCCLUSION_LINKS = (
    "TORSO",
    "pro_interface_link",
    "sensor_carrier_link",
    "s410_guard_link",
    "mid360_body_link",
)


def _rgb_frame(frame):
    import numpy as np

    if frame is None:
        raise AdapterFailure("renderer returned no RGB frame")
    if frame.ndim != 3 or frame.shape[2] not in (3, 4):
        raise AdapterFailure(f"unexpected RGB frame shape: {frame.shape}")
    return np.asarray(frame[:, :, :3], dtype=np.uint8)


def _rgb_scene_content(frame, minimum_mean=25.0, minimum_std=12.0):
    """Detect a camera occlusion frame without changing simulation evidence."""
    import numpy as np

    rgb = _rgb_frame(frame).astype(np.float32)
    luma = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    mean = float(luma.mean())
    std = float(luma.std())
    return {
        "passed": mean >= minimum_mean and std >= minimum_std,
        "luma_mean": mean,
        "luma_std": std,
    }


def _write_depth_artifacts(output_dir, frame, metadata, maximum_range):
    import imageio.v2 as imageio
    import numpy as np

    depth_m = np.asarray(frame.numpy(), dtype=np.float32)
    npy_path = output_dir / "d435i_depth_frame_m.npy"
    millimetres_path = output_dir / "d435i_depth_frame_mm.png"
    preview_path = output_dir / "d435i_depth_preview.png"
    np.save(npy_path, depth_m, allow_pickle=False)
    depth_mm = np.rint(np.clip(depth_m, 0.0, maximum_range) * 1000.0).astype(
        np.uint16
    )
    imageio.imwrite(millimetres_path, depth_mm)
    valid = np.isfinite(depth_m) & (depth_m < maximum_range)
    preview = np.zeros(depth_m.shape, dtype=np.uint8)
    if np.any(valid):
        scaled = 1.0 - np.clip(depth_m[valid] / maximum_range, 0.0, 1.0)
        preview[valid] = np.rint(32.0 + 223.0 * scaled).astype(np.uint8)
    imageio.imwrite(preview_path, preview)
    artifact_metadata = dict(metadata)
    artifact_metadata["artifacts"] = {
        "depth_metres_npy": {
            "path": npy_path.name,
            "sha256": _sha256(npy_path),
            "bytes": npy_path.stat().st_size,
        },
        "depth_millimetres_png": {
            "path": millimetres_path.name,
            "sha256": _sha256(millimetres_path),
            "bytes": millimetres_path.stat().st_size,
            "invalid_or_clipped_value_mm": int(round(maximum_range * 1000.0)),
        },
        "human_preview_png": {
            "path": preview_path.name,
            "sha256": _sha256(preview_path),
            "bytes": preview_path.stat().st_size,
            "display_rule": "nearer valid depth is brighter; invalid is black",
        },
    }
    metadata_path = output_dir / "d435i_depth_frame_metadata.json"
    _write_json(metadata_path, artifact_metadata)
    return artifact_metadata


def _sensor_rig_enabled(args) -> bool:
    return args.robot_asset is not None


def _official_mid360_enabled(args) -> bool:
    return getattr(args, "lidar_pattern_mode", "uniform") == "livox_mid360"


def _dual_cloud_geometry_enabled(args) -> bool:
    return getattr(args, "cloud_profile", "legacy_planner_v1") == "upstream_go2_reference"


def _mid360_pattern_cfg(patterns, pattern_table):
    """Build an Isaac pattern config without importing Isaac in unit tests."""

    def initial_pattern(_cfg, device):
        import torch

        directions, _ = pattern_table.scan_window(0)
        ray_directions = torch.as_tensor(
            directions.copy(), dtype=torch.float32, device=device
        )
        return torch.zeros_like(ray_directions), ray_directions

    return patterns.PatternBaseCfg(func=initial_pattern)


def _set_mid360_scan_window(lidar, pattern_table, scan_index, torch):
    """Install one ordered slice and acquire it at the current Isaac pose.

    IsaacLab's public ``update(force_recompute=True)`` still requires the
    sensor's outdated bit. Its public reset operation marks that bit before the
    zero-dt update, making pose and rays come from the same physics step. This
    ray caster has zero configured drift, so reset does not perturb geometry.
    """

    directions, window = pattern_table.scan_window(scan_index)
    expected_shape = (1, pattern_table.points_per_scan, 3)
    if tuple(lidar.ray_directions.shape) != expected_shape:
        raise AdapterFailure(
            "MID-360 ray buffer shape mismatch: "
            f"expected {expected_shape}, got {tuple(lidar.ray_directions.shape)}"
        )
    lidar.ray_directions[0].copy_(
        torch.as_tensor(directions.copy(), dtype=torch.float32, device=lidar.device)
    )
    lidar.reset()
    lidar.update(dt=0.0, force_recompute=True)
    return window


def _forest_enabled(args) -> bool:
    return args.course in (
        "forest_gen",
        "forest_gen_nav",
        "forest_gen_nav_v6",
        "forest_gen_nav_v7_dynamic",
        "forest_gen_nav_v8_human",
        "forest_gen_nav_v8_official_human",
    )


def _forest_navigation_enabled(args) -> bool:
    return args.course in (
        "forest_gen_nav",
        "forest_gen_nav_v6",
        "forest_gen_nav_v7_dynamic",
        "forest_gen_nav_v8_human",
        "forest_gen_nav_v8_official_human",
    )


def _forest_v6_enabled(args) -> bool:
    return args.course == "forest_gen_nav_v6"


def _forest_v7_enabled(args) -> bool:
    return args.course == "forest_gen_nav_v7_dynamic"


def _forest_v8_enabled(args) -> bool:
    return args.course == "forest_gen_nav_v8_human"


def _forest_v8_official_enabled(args) -> bool:
    return args.course == "forest_gen_nav_v8_official_human"


def _office_enabled(args) -> bool:
    return args.course in ("office_l0_static", "office_l0_crowd")


def _office_crowd_enabled(args) -> bool:
    return args.course == "office_l0_crowd"


def _office_review_side_video_path(args) -> Optional[Path]:
    return getattr(args, "office_review_third_person_side_video_path", None) or getattr(args, "office_review_third_person_video_path", None)


def _office_review_overview_video_path(args) -> Optional[Path]:
    return getattr(args, "office_review_overview_video_path", None)


def _office_review_quality_profile():
    from .office_review_presentation import frozen_quality_profile

    return frozen_quality_profile()


def _office_review_presentation_enabled(args) -> bool:
    return bool(
        getattr(args, "office_review_presentation", False)
        or getattr(args, "office_review_material", False)
        or _office_review_side_video_path(args) is not None
        or _office_review_overview_video_path(args) is not None
        or getattr(args, "office_review_camera_trace_path", None) is not None
        or getattr(args, "office_review_material_audit_path", None) is not None
        or getattr(args, "office_review_dashboard_video_path", None) is not None
        or getattr(args, "office_review_dashboard_metadata_path", None) is not None
        or getattr(args, "office_review_validation_report_path", None) is not None
        or getattr(args, "office_review_effective_input_path", None) is not None
        or getattr(args, "office_review_launcher_path", None) is not None
    )


def _forest_v8_any_enabled(args) -> bool:
    return _forest_v8_enabled(args) or _forest_v8_official_enabled(args)


def _dynamic_obstacle_enabled(args) -> bool:
    return _forest_v7_enabled(args) or _forest_v8_any_enabled(args)


def _forest_review_geometry_enabled(args) -> bool:
    return _forest_v6_enabled(args) or _dynamic_obstacle_enabled(args)


def _dynamic_obstacle_spec(args) -> DynamicObstacleSpec:
    end_x = (
        args.dynamic_obstacle_x
        if args.dynamic_obstacle_end_x is None
        else args.dynamic_obstacle_end_x
    )
    return DynamicObstacleSpec(
        name=(
            "v8_official_human_crossing_actor"
            if _forest_v8_official_enabled(args)
            else "v8_human_crossing_actor"
            if _forest_v8_enabled(args)
            else "v7_crossing_actor"
        ),
        start_xy=(args.dynamic_obstacle_x, args.dynamic_obstacle_start_y),
        end_xy=(end_x, args.dynamic_obstacle_end_y),
        wait_seconds=args.dynamic_obstacle_wait_seconds,
        speed_mps=args.dynamic_obstacle_speed,
        radius_m=args.dynamic_obstacle_radius,
        height_m=args.dynamic_obstacle_height,
        terrain_clearance_m=args.dynamic_obstacle_terrain_clearance,
        hold_fraction=args.dynamic_obstacle_hold_fraction,
        hold_seconds=args.dynamic_obstacle_hold_seconds,
    )


def _dynamic_route_static_geometry_checks(
    forest_layout: Mapping[str, object], spec: DynamicObstacleSpec
) -> Mapping[str, object]:
    """Reject a scheduled actor route that sweeps through static forest proxies."""

    records = []
    for proxy in forest_layout.get("proxies", []):
        bounds_min = proxy.get("bounds_min_m", [])
        bounds_max = proxy.get("bounds_max_m", [])
        if len(bounds_min) < 2 or len(bounds_max) < 2:
            raise AdapterFailure("forest proxy lacks route-precheck XY bounds")
        clearance = segment_to_aabb_clearance_2d(
            spec.start_xy,
            spec.end_xy,
            bounds_min[:2],
            bounds_max[:2],
            swept_radius_m=spec.radius_m,
        )
        records.append(
            {
                "name": str(proxy.get("name")),
                "kind": str(proxy.get("kind")),
                "prim_path": str(proxy.get("prim_path")),
                "bounds_min_xy_m": [float(value) for value in bounds_min[:2]],
                "bounds_max_xy_m": [float(value) for value in bounds_max[:2]],
                "swept_capsule_clearance_m": clearance,
            }
        )
    if not records:
        raise AdapterFailure("dynamic route precheck has no static forest proxies")
    nearest = min(records, key=lambda row: row["swept_capsule_clearance_m"])
    minimum = float(nearest["swept_capsule_clearance_m"])
    return {
        "method": "exact centre-segment to static-proxy AABB distance minus actor radius",
        "route_start_xy_m": list(spec.start_xy),
        "route_end_xy_m": list(spec.end_xy),
        "swept_radius_m": spec.radius_m,
        "minimum_required_clearance_m": DYNAMIC_ROUTE_MIN_STATIC_CLEARANCE_M,
        "minimum_static_clearance_m": minimum,
        "nearest_static_object": nearest,
        "checked_static_object_count": len(records),
        "passed": minimum >= DYNAMIC_ROUTE_MIN_STATIC_CLEARANCE_M,
        "objects": records,
    }


def _dynamic_schedule_trigger_identity(trigger_mode: str) -> str:
    if trigger_mode == "first_nonzero_body_command":
        return "first nonzero accepted body command"
    if trigger_mode == "run_start":
        return "closed-loop run start"
    raise AdapterFailure(f"unsupported dynamic schedule trigger: {trigger_mode}")


def _dynamic_human_part_exprs() -> tuple[str, ...]:
    return tuple(
        f"{{ENV_REGEX_NS}}/DynamicObstacle/Visual/{name}"
        for name in DYNAMIC_HUMAN_PART_NAMES
    )


def _official_human_sensor_exprs() -> tuple[str, ...]:
    return (f"{DYNAMIC_OBSTACLE_PRIM_EXPR}/CollisionCapsule",)


def _write_procedural_human_usd(path: Path, spec: DynamicObstacleSpec) -> Mapping[str, object]:
    """Author the V8 human visual and hidden collision capsule as run evidence."""

    from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

    path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/Human")
    stage.SetDefaultPrim(root.GetPrim())
    rigid = UsdPhysics.RigidBodyAPI.Apply(root.GetPrim())
    rigid.CreateKinematicEnabledAttr(True)
    PhysxSchema.PhysxRigidBodyAPI.Apply(root.GetPrim()).CreateDisableGravityAttr(True)
    UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(20.0)

    material = UsdShade.Material.Define(stage, "/Human/Looks/YellowHuman")
    shader = UsdShade.Shader.Define(stage, "/Human/Looks/YellowHuman/PreviewSurface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*DYNAMIC_HUMAN_COLOR_RGB)
    )
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.62)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

    collision = UsdGeom.Capsule.Define(stage, "/Human/CollisionCapsule")
    collision.CreateAxisAttr(UsdGeom.Tokens.z)
    collision.CreateRadiusAttr(float(spec.radius_m))
    collision.CreateHeightAttr(float(spec.height_m - 2.0 * spec.radius_m))
    UsdPhysics.CollisionAPI.Apply(collision.GetPrim())
    collision.MakeInvisible()

    UsdGeom.Xform.Define(stage, "/Human/Visual")

    def part_xform(name, translation, rotate_x=False):
        part = UsdGeom.Xform.Define(stage, f"/Human/Visual/{name}")
        part.AddTranslateOp().Set(Gf.Vec3d(*translation))
        if rotate_x:
            part.AddRotateXOp().Set(0.0)
        return part

    def bind(geometry):
        UsdShade.MaterialBindingAPI(geometry.GetPrim()).Bind(material)

    head_part = part_xform("Head", (0.0, 0.0, 0.68))
    head = UsdGeom.Sphere.Define(stage, f"{head_part.GetPath()}/Shape")
    head.CreateRadiusAttr(0.16)
    bind(head)

    torso_part = part_xform("Torso", (0.0, 0.0, 0.30))
    torso = UsdGeom.Cube.Define(stage, f"{torso_part.GetPath()}/Shape")
    torso.CreateSizeAttr(1.0)
    # A high-visibility jacket-sized torso keeps the rendered human surface
    # commensurate with its conservative physical capsule.  A narrower first
    # draft produced only half the cylinder baseline's early lidar returns and
    # allowed the planner to react after the physical envelope was breached.
    torso.AddScaleOp().Set(Gf.Vec3f(0.52, 0.42, 0.58))
    bind(torso)

    pelvis_part = part_xform("Pelvis", (0.0, 0.0, 0.00))
    pelvis = UsdGeom.Cube.Define(stage, f"{pelvis_part.GetPath()}/Shape")
    pelvis.CreateSizeAttr(1.0)
    pelvis.AddScaleOp().Set(Gf.Vec3f(0.38, 0.32, 0.24))
    bind(pelvis)

    for name, x in (("LeftArm", 0.24), ("RightArm", -0.24)):
        part = part_xform(name, (x, 0.0, 0.48), rotate_x=True)
        arm = UsdGeom.Capsule.Define(stage, f"{part.GetPath()}/Shape")
        arm.CreateAxisAttr(UsdGeom.Tokens.z)
        arm.CreateRadiusAttr(0.075)
        arm.CreateHeightAttr(0.48)
        arm.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, -0.30))
        bind(arm)

    for name, x in (("LeftLeg", 0.105), ("RightLeg", -0.105)):
        part = part_xform(name, (x, 0.0, -0.08), rotate_x=True)
        leg = UsdGeom.Capsule.Define(stage, f"{part.GetPath()}/Shape")
        leg.CreateAxisAttr(UsdGeom.Tokens.z)
        leg.CreateRadiusAttr(0.095)
        leg.CreateHeightAttr(0.60)
        leg.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, -0.385))
        bind(leg)

    stage.GetRootLayer().Save()
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "source": "locally generated procedural USDA; no external character asset",
        "visible_part_names": list(DYNAMIC_HUMAN_PART_NAMES),
        "collision_prim_path": "/Human/CollisionCapsule",
        "collision_shape": "hidden capsule",
        "colour_rgb": list(DYNAMIC_HUMAN_COLOR_RGB),
        "gait_cadence_hz": DYNAMIC_HUMAN_GAIT_CADENCE_HZ,
        "gait_maximum_swing_radians": DYNAMIC_HUMAN_GAIT_MAX_SWING_RADIANS,
    }


def _write_official_human_wrapper_usd(
    path: Path, spec: DynamicObstacleSpec
) -> Mapping[str, object]:
    """Author the hidden physical/sensor proxy without the skinned visual."""

    from pxr import PhysxSchema, Usd, UsdGeom, UsdPhysics

    path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/Human")
    stage.SetDefaultPrim(root.GetPrim())
    UsdPhysics.RigidBodyAPI.Apply(root.GetPrim()).CreateKinematicEnabledAttr(True)
    PhysxSchema.PhysxRigidBodyAPI.Apply(root.GetPrim()).CreateDisableGravityAttr(True)
    UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(20.0)

    collision = UsdGeom.Capsule.Define(stage, "/Human/CollisionCapsule")
    collision.CreateAxisAttr(UsdGeom.Tokens.z)
    collision.CreateRadiusAttr(float(spec.radius_m))
    collision.CreateHeightAttr(float(spec.height_m - 2.0 * spec.radius_m))
    UsdPhysics.CollisionAPI.Apply(collision.GetPrim())
    collision.MakeInvisible()

    stage.GetRootLayer().Save()
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "source": "local hidden collision and sensor proxy; no visible character",
        "official_character_url": OFFICIAL_HUMAN_CHARACTER_URL,
        "official_biped_url": OFFICIAL_HUMAN_BIPED_URL,
        "collision_prim_path": "/Human/CollisionCapsule",
        "collision_shape": "hidden capsule",
        "total_envelope_height_m": float(spec.height_m),
        "radius_m": float(spec.radius_m),
        "redistribution": "official NVIDIA content is referenced, not vendored",
    }


def _load_official_human_animation_cache(path: Path) -> Mapping[str, object]:
    import numpy as np

    if path is None or not path.is_file():
        raise AdapterFailure(f"official Biped retarget cache is missing: {path}")
    required = {
        "schema_version",
        "fps",
        "joints",
        "character_url",
        "biped_url",
        "idle_translations",
        "idle_rotations_xyzw",
        "walk_translations",
        "walk_rotations_xyzw",
    }
    with np.load(path, allow_pickle=False) as archive:
        missing = sorted(required - set(archive.files))
        if missing:
            raise AdapterFailure(f"official Biped retarget cache fields missing: {missing}")
        arrays = {name: np.array(archive[name], copy=True) for name in required}
    schema_version = int(arrays["schema_version"][0])
    fps = int(arrays["fps"][0])
    joints = tuple(str(value) for value in arrays["joints"].tolist())
    if schema_version != 1 or fps <= 0 or len(joints) != 101:
        raise AdapterFailure(
            "official Biped retarget cache identity is invalid: "
            f"schema={schema_version} fps={fps} joints={len(joints)}"
        )
    if str(arrays["character_url"][0]) != OFFICIAL_HUMAN_CHARACTER_URL:
        raise AdapterFailure("official Biped retarget cache character URL changed")
    if str(arrays["biped_url"][0]) != OFFICIAL_HUMAN_BIPED_URL:
        raise AdapterFailure("official Biped retarget cache Biped URL changed")
    for clip in ("idle", "walk"):
        translations = arrays[f"{clip}_translations"]
        rotations = arrays[f"{clip}_rotations_xyzw"]
        if (
            translations.ndim != 3
            or translations.shape[0] <= 1
            or translations.shape[1:] != (len(joints), 3)
            or rotations.shape != (translations.shape[0], len(joints), 4)
        ):
            raise AdapterFailure(
                f"official {clip} Biped cache shapes are invalid: "
                f"translations={translations.shape} rotations={rotations.shape}"
            )
        if not np.isfinite(translations).all() or not np.isfinite(rotations).all():
            raise AdapterFailure(f"official {clip} Biped cache contains non-finite data")
        quaternion_norms = np.linalg.norm(rotations, axis=2)
        if np.max(np.abs(quaternion_norms - 1.0)) > 1.0e-4:
            raise AdapterFailure(f"official {clip} Biped cache quaternions are not unit")
        if (
            np.max(np.abs(translations - translations[0])) <= 1.0e-4
            and np.max(np.abs(rotations - rotations[0])) <= 1.0e-4
        ):
            raise AdapterFailure(f"official {clip} Biped cache is a static pose")
    return {
        "path": str(path.resolve()),
        "file_sha256": _sha256(path),
        "content_sha256": official_human_cache_content_sha256(arrays),
        "schema_version": schema_version,
        "fps": fps,
        "joints": joints,
        "idle_translations": arrays["idle_translations"],
        "idle_rotations_xyzw": arrays["idle_rotations_xyzw"],
        "walk_translations": arrays["walk_translations"],
        "walk_rotations_xyzw": arrays["walk_rotations_xyzw"],
    }


def _official_human_usd_components(translations, rotations_xyzw):
    from pxr import Gf

    usd_translations = [Gf.Vec3f(*[float(value) for value in row]) for row in translations]
    usd_rotations = [
        Gf.Quatf(
            float(row[3]),
            Gf.Vec3f(float(row[0]), float(row[1]), float(row[2])),
        )
        for row in rotations_xyzw
    ]
    return usd_translations, usd_rotations


def _write_official_human_visual_usd(
    path: Path,
    animation_cache_path: Path,
) -> Mapping[str, object]:
    """Author a visual-only official person with a Biped-retargeted replay slot."""

    from pxr import Sdf, Usd, UsdGeom, UsdSkel

    cache = _load_official_human_animation_cache(animation_cache_path)

    path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/HumanVisual")
    stage.SetDefaultPrim(root.GetPrim())
    character = UsdGeom.Xform.Define(stage, "/HumanVisual/OfficialCharacter")
    character.GetPrim().GetReferences().AddReference(OFFICIAL_HUMAN_CHARACTER_URL)

    skeleton_prims = [
        prim for prim in stage.Traverse() if prim.GetTypeName() == "Skeleton"
    ]
    if len(skeleton_prims) != 1:
        raise AdapterFailure(
            f"official character needs one skeleton, found {len(skeleton_prims)}"
        )
    skeleton_prim = skeleton_prims[0]
    skeleton = UsdSkel.Skeleton(skeleton_prim)
    skeleton_joints = tuple(str(value) for value in skeleton.GetJointsAttr().Get())
    rest_transforms = skeleton.GetRestTransformsAttr().Get()
    if len(skeleton_joints) != len(rest_transforms):
        raise AdapterFailure("official skeleton joint and rest-transform counts differ")
    if skeleton_joints != cache["joints"]:
        raise AdapterFailure("official runtime skeleton differs from the Biped cache")
    _, _, rest_scales = UsdSkel.DecomposeTransforms(rest_transforms)
    target_path = Sdf.Path("/HumanVisual/OfficialAnimations/Active")
    target = UsdSkel.Animation.Define(stage, target_path)
    target.CreateJointsAttr(list(skeleton_joints))
    initial_components = _official_human_usd_components(
        cache["idle_translations"][0],
        cache["idle_rotations_xyzw"][0],
    )
    target.CreateTranslationsAttr(initial_components[0])
    target.CreateRotationsAttr(initial_components[1])
    target.CreateScalesAttr(rest_scales)

    binding = UsdSkel.BindingAPI.Apply(skeleton_prim)
    binding.CreateAnimationSourceRel().SetTargets([target_path])
    stage.GetRootLayer().Save()
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "source": "visual-only wrapper referencing NVIDIA Isaac Sim 5.1 content",
        "official_character_url": OFFICIAL_HUMAN_CHARACTER_URL,
        "skeleton_path": str(skeleton_prim.GetPath()),
        "source_geometry": {
            "meters_per_unit": 1.0,
            "up_axis": "Z",
            "foot_z_m": OFFICIAL_HUMAN_SOURCE_FOOT_Z_M,
            "visible_top_z_m": OFFICIAL_HUMAN_SOURCE_VISIBLE_TOP_Z_M,
            "source_forward_yaw_radians": OFFICIAL_HUMAN_SOURCE_FORWARD_YAW_RADIANS,
        },
        "biped_retarget_cache": {
            "path": cache["path"],
            "file_sha256": cache["file_sha256"],
            "content_sha256": cache["content_sha256"],
            "schema_version": cache["schema_version"],
            "fps": cache["fps"],
            "joint_count": len(cache["joints"]),
            "idle_frame_count": int(cache["idle_translations"].shape[0]),
            "walk_frame_count": int(cache["walk_translations"].shape[0]),
            "source": "NVIDIA Biped AnimationGraph ControlRig retarget output",
            "target_path": str(target_path),
        },
        "redistribution": "official NVIDIA content is referenced, not vendored",
    }


def _official_human_clip_name(phase: str, animation_mode: str) -> str:
    """Select an official clip without changing the obstacle schedule."""

    if animation_mode == "continuous_walk":
        return "walk"
    if animation_mode == "phase_conditioned":
        return "walk" if phase == "crossing" else "idle"
    raise AdapterFailure(
        f"unsupported official human animation mode: {animation_mode}"
    )


class _OfficialHumanAnimationPlayer:
    """Replay official Biped-retargeted poses without an AnimationGraph."""

    def __init__(
        self,
        stage,
        animation_cache_path: Path,
        animation_mode: str = "phase_conditioned",
        visual_root_path: str = DYNAMIC_HUMAN_VISUAL_RUNTIME_PRIM,
    ):
        from pxr import Usd, UsdSkel

        self.stage = stage
        self.visual_root_path = visual_root_path
        self.cache = _load_official_human_animation_cache(animation_cache_path)
        visual_root = stage.GetPrimAtPath(visual_root_path)
        if not visual_root.IsValid():
            raise AdapterFailure("official human visual root is absent")
        skeleton_prims = [
            prim
            for prim in Usd.PrimRange(visual_root, Usd.TraverseInstanceProxies())
            if prim.GetTypeName() == "Skeleton"
        ]
        if len(skeleton_prims) != 1:
            raise AdapterFailure(
                f"runtime official human needs one skeleton, found {len(skeleton_prims)}"
            )
        self.skeleton_prim = skeleton_prims[0]
        skeleton = UsdSkel.Skeleton(self.skeleton_prim)
        self.skeleton_joints = tuple(
            str(value) for value in skeleton.GetJointsAttr().Get()
        )
        if self.skeleton_joints != self.cache["joints"]:
            raise AdapterFailure("runtime official skeleton differs from Biped cache")
        self.target = UsdSkel.Animation(
            stage.GetPrimAtPath(
                f"{visual_root_path}/OfficialAnimations/Active"
            )
        )
        if not self.target:
            raise AdapterFailure("runtime official animation replay slot is absent")
        self.active_name = None
        self.clip_origin_seconds = 0.0
        self.animation_mode = animation_mode
        _official_human_clip_name("waiting", animation_mode)

    def update(self, elapsed_seconds: float, phase: str) -> Mapping[str, object]:
        if not math.isfinite(elapsed_seconds) or elapsed_seconds < 0.0:
            raise AdapterFailure("official animation elapsed time is invalid")
        name = _official_human_clip_name(phase, self.animation_mode)
        if self.active_name != name:
            self.active_name = name
            self.clip_origin_seconds = elapsed_seconds
        translations = self.cache[f"{name}_translations"]
        rotations = self.cache[f"{name}_rotations_xyzw"]
        frame_index = int(
            max(0.0, elapsed_seconds - self.clip_origin_seconds) * self.cache["fps"]
        ) % int(translations.shape[0])
        components = _official_human_usd_components(
            translations[frame_index],
            rotations[frame_index],
        )
        self.target.GetTranslationsAttr().Set(components[0])
        self.target.GetRotationsAttr().Set(components[1])
        target_path = self.target.GetPrim().GetPath()
        return {
            "source": "NVIDIA Isaac Sim 5.1 Biped AnimationGraph retarget cache",
            "clip": name,
            "phase": phase,
            "animation_mode": self.animation_mode,
            "frame_index": frame_index,
            "frame_count": int(translations.shape[0]),
            "fps": self.cache["fps"],
            "target_joint_count": len(self.skeleton_joints),
            "target_animation_path": str(target_path),
            "cache_content_sha256": self.cache["content_sha256"],
            "local_procedural_gait": False,
            "direct_gpu_animation_graph_used": False,
        }


def _set_official_human_visual_pose(
    stage,
    registered_state,
    visual_root_path: str = DYNAMIC_HUMAN_VISUAL_RUNTIME_PRIM,
) -> Mapping[str, object]:
    from pxr import Gf, Usd, UsdGeom

    prim = stage.GetPrimAtPath(visual_root_path)
    if not prim.IsValid():
        raise AdapterFailure("official human visual root is absent during pose update")
    xformable = UsdGeom.Xformable(prim)
    translate_op = None
    orient_op = None
    for op in xformable.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            translate_op = op
        elif op.GetOpType() == UsdGeom.XformOp.TypeOrient:
            orient_op = op
    if translate_op is None:
        translate_op = xformable.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)
    if orient_op is None:
        orient_op = xformable.AddOrientOp(UsdGeom.XformOp.PrecisionDouble)
    xyz = registered_state["visual_root_xyz_m"]
    quat = registered_state["visual_quaternion_wxyz"]
    translate_op.Set(Gf.Vec3d(*xyz))
    orient_op.Set(Gf.Quatd(quat[0], Gf.Vec3d(quat[1], quat[2], quat[3])))
    world_translation = xformable.ComputeLocalToWorldTransform(
        Usd.TimeCode.Default()
    ).ExtractTranslation()
    return {
        "scheduled_root_xyz_m": list(xyz),
        "readback_root_xyz_m": [float(value) for value in world_translation],
        "root_pose_error_m": math.dist(xyz, world_translation),
        "visual_foot_world_z_m": registered_state["visual_foot_world_z_m"],
        "visual_top_world_z_m": registered_state["visual_top_world_z_m"],
        "capsule_bottom_world_z_m": registered_state[
            "capsule_bottom_world_z_m"
        ],
        "foot_to_capsule_bottom_error_m": registered_state[
            "foot_to_capsule_bottom_error_m"
        ],
        "visual_yaw_radians": registered_state["visual_yaw_radians"],
    }


def _apply_procedural_human_gait(stage, angles: Mapping[str, float]) -> None:
    """Write reviewed part-local rotations; the dynamic root remains PhysX-owned."""

    from pxr import UsdGeom

    angle_by_part = {
        "LeftArm": angles["left_arm_radians"],
        "RightArm": angles["right_arm_radians"],
        "LeftLeg": angles["left_leg_radians"],
        "RightLeg": angles["right_leg_radians"],
    }
    for name, radians in angle_by_part.items():
        prim = stage.GetPrimAtPath(
            f"{DYNAMIC_OBSTACLE_RUNTIME_PRIM}/Visual/{name}"
        )
        if not prim.IsValid():
            raise AdapterFailure(f"procedural human part is missing: {name}")
        rotate_ops = [
            op
            for op in UsdGeom.Xformable(prim).GetOrderedXformOps()
            if op.GetOpType() == UsdGeom.XformOp.TypeRotateX
        ]
        if len(rotate_ops) != 1:
            raise AdapterFailure(f"procedural human part has no unique rotateX op: {name}")
        rotate_ops[0].Set(math.degrees(float(radians)))


def _forest_preview_enabled(args) -> bool:
    return args.course == "forest_gen"


def _git_head(path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise AdapterFailure(f"cannot resolve pinned git commit for {path}") from error
    return result.stdout.strip()


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _forest_asset_source_path(asset) -> Path:
    converter = getattr(asset.mesh, "converter", None)
    converter_cfg = getattr(converter, "cfg", None)
    source_path = getattr(converter_cfg, "asset_path", None)
    if not source_path:
        raise AdapterFailure(
            f"forest visual {asset.name} has no traceable converter input"
        )
    path = Path(source_path).resolve()
    if not path.is_file():
        raise AdapterFailure(f"forest visual source asset is missing: {path}")
    return path


def _forest_runtime_asset_path(asset) -> Path:
    converter = getattr(asset.mesh, "converter", None)
    runtime_path = getattr(converter, "usd_path", None)
    if not runtime_path:
        raise AdapterFailure(
            f"forest visual {asset.name} has no converted runtime USD"
        )
    path = Path(runtime_path).resolve()
    if not path.is_file():
        raise AdapterFailure(f"forest visual runtime USD is missing: {path}")
    return path


def _usd_default_prim_bounds(path: Path):
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise AdapterFailure(f"cannot open forest runtime USD: {path}")
    root = stage.GetDefaultPrim()
    if not root.IsValid():
        raise AdapterFailure(f"forest runtime USD has no default prim: {path}")
    bbox = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
    ).ComputeWorldBound(root).ComputeAlignedRange()
    lower = tuple(float(value) for value in bbox.GetMin())
    upper = tuple(float(value) for value in bbox.GetMax())
    if (
        not all(math.isfinite(value) for value in lower + upper)
        or any(left >= right for left, right in zip(lower, upper))
    ):
        raise AdapterFailure(f"forest runtime USD has invalid bounds: {path}")
    return lower, upper


def _usd_default_prim_geometry(path: Path):
    """Return runtime bounds and real low-surface support vertices."""

    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(path), load=Usd.Stage.LoadAll)
    if stage is None:
        raise AdapterFailure(f"cannot open forest runtime USD: {path}")
    root = stage.GetDefaultPrim()
    if not root.IsValid():
        raise AdapterFailure(f"forest runtime USD has no default prim: {path}")
    lower, upper = _usd_default_prim_bounds(path)
    xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    points = []
    for prim in Usd.PrimRange(root, Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        transform = xform_cache.GetLocalToWorldTransform(prim)
        local_points = UsdGeom.Mesh(prim).GetPointsAttr().Get() or ()
        for point in local_points:
            transformed = transform.Transform(point)
            values = tuple(float(value) for value in transformed)
            if all(math.isfinite(value) for value in values):
                points.append(values)
    if not points:
        raise AdapterFailure(f"forest runtime USD has no finite mesh vertices: {path}")
    minimum_z = min(point[2] for point in points)
    support_points = tuple(
        point
        for point in points
        if point[2] <= minimum_z + FOREST_ROCK_SUPPORT_BAND_M
    )
    if not support_points:
        raise AdapterFailure(f"forest runtime USD has no low support vertices: {path}")
    return lower, upper, support_points, len(points)


def _forest_kind(asset) -> str:
    return asset.name.split("_", 1)[0]


def _build_forest_layout(args):
    """Generate one pinned forest terrain and a bounded visual/physics subset."""

    if not _forest_enabled(args):
        return None

    print("[forest-v4] layout_imports_start", flush=True)
    import numpy as np
    import forest_gen
    import stripe_kit
    from forest_gen.assets import PlantModelFactory
    from forest_gen.scene import HeightmapTerrain, classify_terrain
    from forest_gen_utils.terrain import TerrainConfig, TerrainGenerator
    from forest_gen_utils.terrain.microrelief import BasicMicrorelief
    from forest_gen_utils.terrain.moisture import DefaultMoistureModel
    from forest_gen_utils.terrain.noise import FractalNoise
    from stripe_kit import AssetInstance
    print("[forest-v4] layout_imports_ready", flush=True)

    forest_root = args.forest_gen_root.resolve()
    stripe_root = args.stripe_kit_root.resolve()
    if not _path_is_within(Path(forest_gen.__file__), forest_root):
        raise AdapterFailure("forest_gen imported outside the pinned source tree")
    if not _path_is_within(Path(stripe_kit.__file__), stripe_root):
        raise AdapterFailure("stripe_kit imported outside the pinned source tree")
    if _git_head(forest_root) != PINNED_FOREST_GEN_COMMIT:
        raise AdapterFailure("forest_gen source commit mismatch")
    if _git_head(stripe_root) != PINNED_STRIPE_KIT_COMMIT:
        raise AdapterFailure("STRIPE-kit source commit mismatch")

    origin_rng = random.Random(args.forest_seed)
    source_origin_xy = (
        float(origin_rng.randint(args.forest_margin, args.forest_size - args.forest_margin)),
        float(origin_rng.randint(args.forest_margin, args.forest_size - args.forest_margin)),
    )
    np.random.seed(args.forest_seed)
    print("[forest-v4] terrain_generation_start", flush=True)
    terrain_generator = TerrainGenerator(
        noise=FractalNoise(seed=args.forest_seed),
        micro=BasicMicrorelief(),
        moisture_model=DefaultMoistureModel(
            {"flow": 0.55, "slope": 0.30, "aspect": 0.15}
        ),
    )
    terrain_cfg = TerrainConfig(
        size=args.forest_size,
        resolution=0.25,
        scale=4.0,
        octaves=2,
        height_scale=2,
        apply_microrelief=True,
    )
    raw_terrain = terrain_generator.generate(terrain_cfg)
    source_origin_z = float(raw_terrain(*source_origin_xy))
    terrain = HeightmapTerrain(
        raw_terrain.to_meshes(classify_terrain),
        (*source_origin_xy, source_origin_z),
        (args.forest_size, args.forest_size),
        raw_terrain,
    )
    for mesh, _tags in terrain.mesh:
        if hasattr(mesh.visual, "to_color"):
            mesh.visual = mesh.visual.to_color()
    print("[forest-v4] terrain_generation_ready", flush=True)
    # TerrainImporter adds the V12 base z=0.35 to this origin. forest_gen's
    # upstream +1.0 offset is Spot-specific and is deliberately not reused.
    terrain.origin = (*source_origin_xy, source_origin_z)

    print("[forest-v4] bounded_visual_generation_start", flush=True)
    model_factory = PlantModelFactory(path=str(args.forest_asset_path.resolve()))
    generated_assets = []
    generated_counts = {}

    def make_asset(kind, variant, dx, dy, *, z_offset=0.0, scale_mult=1.0):
        source_x = source_origin_xy[0] + dx
        source_y = source_origin_xy[1] + dy
        position = (
            source_x,
            source_y,
            float(terrain.raw(source_x, source_y)) + z_offset,
        )
        index = generated_counts.get(kind, 0)
        generated_counts[kind] = index + 1
        generated_assets.append(
            AssetInstance(
                asset_class=None,
                mesh=model_factory.get_usdz_model_by_name(
                    kind, variant, scale_mult
                ),
                name=f"{kind}_{index}",
                position=position,
                rotation=(1.0, 0.0, 0.0, 0.0),
                additional_tags={
                    "species": kind,
                    "placement": (
                        "v5_navigation_blocker"
                        if _forest_navigation_enabled(args)
                        and kind == "Pine"
                        and index == 0
                        else "v4_deterministic_adapter"
                    ),
                },
                global_collisions=False,
            )
        )

    primary_tree_y = 0.0 if _forest_navigation_enabled(args) else 1.65
    tree_layout = (
        ("Pine", 1, 3.2, primary_tree_y),
        ("Birch", 1, 4.8, -2.20),
        ("Pine", 2, -3.0, -4.0),
        ("Birch", 2, -5.0, 2.5),
        ("Pine", 3, 7.0, 4.0),
        ("Birch", 3, 9.0, -4.0),
        ("Pine", 1, -7.0, -2.0),
        ("Birch", 1, 2.0, 7.0),
    )
    for kind, variant, dx, dy in tree_layout:
        make_asset(kind, variant, dx, dy)
    for variant, dx, dy in (
        (1, 2.7, -1.55),
        (2, -2.0, 2.0),
        (3, 6.0, 3.0),
    ):
        make_asset("Rock", variant, dx, dy, scale_mult=1.5)
    for dx, dy in (
        (1.8, 3.0),
        (-1.5, -2.8),
        (5.5, 2.4),
        (6.5, -3.0),
        (-4.0, 4.0),
        (0.0, 5.5),
    ):
        make_asset("Bush", 1, dx, dy)
    placement_rng = random.Random(args.forest_seed + 1000)
    for index in range(30):
        angle = 2.0 * math.pi * index / 30.0 + placement_rng.uniform(-0.08, 0.08)
        radius = placement_rng.uniform(1.2, 8.0)
        make_asset(
            "Grass",
            1,
            radius * math.cos(angle),
            radius * math.sin(angle),
            z_offset=-0.1,
        )
    print(
        "[forest-v4] bounded_visual_generation_ready "
        f"count={len(generated_assets)} counts={generated_counts}",
        flush=True,
    )

    visual_specs = []

    def add_visual(asset, source_position, placement):
        index = len(visual_specs)
        source_path = _forest_asset_source_path(asset)
        runtime_path = _forest_runtime_asset_path(asset)
        source_position = tuple(float(value) for value in source_position)
        unseated_source_position = source_position
        world_position = (
            source_position[0] - 0.5 * args.forest_size,
            source_position[1] - 0.5 * args.forest_size,
            source_position[2],
        )
        local_bounds = None
        mesh_support = None
        seating = None
        if _forest_kind(asset) == "Rock":
            if _forest_review_geometry_enabled(args):
                (
                    local_lower,
                    local_upper,
                    support_points,
                    mesh_vertex_count,
                ) = _usd_default_prim_geometry(runtime_path)
                mesh_support = {
                    "vertex_count": mesh_vertex_count,
                    "support_vertex_count": len(support_points),
                    "support_band_m": FOREST_ROCK_SUPPORT_BAND_M,
                    "support_points_local_xyz_m": support_points,
                }
            else:
                local_lower, local_upper = _usd_default_prim_bounds(runtime_path)
            local_bounds = {"min_m": local_lower, "max_m": local_upper}
            if _forest_review_geometry_enabled(args):
                seating = dict(
                    terrain_seating_for_mesh_support(
                        world_position[:2],
                        support_points,
                        lambda x, y: float(
                            terrain.raw(
                                x + 0.5 * args.forest_size,
                                y + 0.5 * args.forest_size,
                            )
                        ),
                        clearance_m=FOREST_ROCK_SEATING_CLEARANCE_M,
                    )
                )
                final_z = float(seating["required_origin_z_m"])
                seating["seated_bounds_min_z_m"] = final_z + local_lower[2]
                seating["unseated_origin_z_m"] = world_position[2]
                seating["vertical_correction_m"] = final_z - world_position[2]
                world_position = (world_position[0], world_position[1], final_z)
                source_position = (source_position[0], source_position[1], final_z)
        visual_specs.append(
            {
                "name": f"forest_visual_{index:03d}",
                "prim_path": f"/World/forest_visual/asset_{index:03d}",
                "kind": _forest_kind(asset),
                "source_asset_instance_name": asset.name,
                "source_asset_path": source_path,
                "source_asset_sha256": _sha256(source_path),
                "runtime_asset_path": runtime_path,
                "runtime_asset_sha256": _sha256(runtime_path),
                "runtime_local_bounds_m": local_bounds,
                "runtime_mesh_support": mesh_support,
                "terrain_seating": seating,
                "unseated_source_position_m": unseated_source_position,
                "source_position_m": source_position,
                "world_position_m": world_position,
                "placement": placement,
                "asset": asset,
            }
        )

    for asset in generated_assets:
        add_visual(
            asset,
            asset.position,
            (
                "v5_navigation_blocker_placement"
                if _forest_navigation_enabled(args) and asset.name == "Pine_0"
                else "v4_deterministic_adapter_placement"
            ),
        )
    print("[forest-v4] visual_records_ready", flush=True)

    proxies = []
    for visual in visual_specs:
        if visual["kind"] not in ("Pine", "Birch", "Rock"):
            continue
        x, y, ground_z = visual["world_position_m"]
        if visual["kind"] in ("Pine", "Birch"):
            size = (
                2.0 * FOREST_TREE_PROXY_RADIUS_M,
                2.0 * FOREST_TREE_PROXY_RADIUS_M,
                FOREST_TREE_PROXY_HEIGHT_M,
            )
            shape = "cylinder"
            center = (x, y, ground_z + 0.5 * size[2])
        elif _forest_review_geometry_enabled(args):
            local_bounds = visual["runtime_local_bounds_m"]
            local_lower = tuple(local_bounds["min_m"])
            local_upper = tuple(local_bounds["max_m"])
            size = tuple(
                local_upper[index] - local_lower[index] for index in range(3)
            )
            center = tuple(
                visual["world_position_m"][index]
                + 0.5 * (local_lower[index] + local_upper[index])
                for index in range(3)
            )
            shape = "cuboid"
        else:
            size = FOREST_ROCK_PROXY_SIZE_M
            shape = "cuboid"
            center = (x, y, ground_z + 0.5 * size[2])
        half = tuple(0.5 * value for value in size)
        index = len(proxies)
        proxies.append(
            {
                "name": f"forest_proxy_{index:03d}",
                "prim_path": f"/World/forest_collision/proxy_{index:03d}",
                "visual_name": visual["name"],
                "kind": visual["kind"],
                "shape": shape,
                "center_m": center,
                "size_m": size,
                "render_visible": not _forest_review_geometry_enabled(args),
                "bounds_min_m": tuple(center[i] - half[i] for i in range(3)),
                "bounds_max_m": tuple(center[i] + half[i] for i in range(3)),
            }
        )
    print(f"[forest-v4] proxy_records_ready count={len(proxies)}", flush=True)

    terrain_digest = hashlib.sha256()
    terrain_vertex_count = 0
    terrain_face_count = 0
    terrain_z_values = []
    for mesh, _tags in terrain.mesh:
        vertices = np.asarray(mesh.vertices, dtype=np.float64)
        faces = np.asarray(mesh.faces, dtype=np.int64)
        terrain_digest.update(vertices.tobytes(order="C"))
        terrain_digest.update(faces.tobytes(order="C"))
        terrain_vertex_count += int(vertices.shape[0])
        terrain_face_count += int(faces.shape[0])
        terrain_z_values.extend(vertices[:, 2].tolist())
    print("[forest-v4] terrain_identity_ready", flush=True)
    spawn_world = (
        source_origin_xy[0] - 0.5 * args.forest_size,
        source_origin_xy[1] - 0.5 * args.forest_size,
        source_origin_z,
    )
    navigation_identity = None
    if _forest_navigation_enabled(args):
        primary_proxy = next(
            proxy
            for proxy in proxies
            if proxy["visual_name"] == "forest_visual_000"
        )
        direct_path_distance = point_to_segment_distance_2d(
            primary_proxy["center_m"][:2],
            spawn_world[:2],
            FOREST_NAVIGATION_GOAL_WORLD_M[:2],
        )
        required_center_clearance = (
            FOREST_TREE_PROXY_RADIUS_M + FOREST_NAVIGATION_PLANNING_RADIUS_M
        )
        navigation_identity = {
            "start_world_m": spawn_world,
            "goal_world_m": FOREST_NAVIGATION_GOAL_WORLD_M,
            "primary_blocker": dict(primary_proxy),
            "planner_body_radius_m": FOREST_NAVIGATION_PLANNING_RADIUS_M,
            "required_center_clearance_m": required_center_clearance,
            "primary_center_to_direct_segment_m": direct_path_distance,
            "direct_path_intersects_inflated_blocker": (
                direct_path_distance < required_center_clearance
            ),
            "planner_input_boundary": (
                "rendered XYZ plus sensor pose only; proxy bounds and terrain "
                "height are retained for evaluation and never enter SCAN input"
            ),
        }
        if not navigation_identity["direct_path_intersects_inflated_blocker"]:
            raise AdapterFailure(
                "V5 primary tree does not block the direct start-to-goal segment"
            )
    identity_visuals = [
        {key: (str(value) if isinstance(value, Path) else value) for key, value in visual.items() if key != "asset"}
        for visual in visual_specs
    ]
    identity = {
        "forest_gen_commit": PINNED_FOREST_GEN_COMMIT,
        "stripe_kit_commit": PINNED_STRIPE_KIT_COMMIT,
        "forest_gen_root": str(forest_root),
        "stripe_kit_root": str(stripe_root),
        "asset_root": str(args.forest_asset_path.resolve()),
        "seed": args.forest_seed,
        "size_m": args.forest_size,
        "margin_m": args.forest_margin,
        "source_origin_xy_m": source_origin_xy,
        "spawn_world_xyz_m": spawn_world,
        "spot_specific_upstream_spawn_offset_removed_m": 1.0,
        "terrain": {
            "mesh_count": len(terrain.mesh),
            "vertex_count": terrain_vertex_count,
            "face_count": terrain_face_count,
            "z_min_m": min(terrain_z_values),
            "z_max_m": max(terrain_z_values),
            "geometry_sha256": terrain_digest.hexdigest(),
            "visual_normalization": (
                "TextureVisuals converted to ColorVisuals before TerrainImporter "
                "concatenation; vertices and faces are unchanged"
            ),
        },
        "source_asset_instantiated_counts": generated_counts,
        "navigation": navigation_identity,
        "bounded_adapter": {
            "visual_count": len(visual_specs),
            "physics_sensor_proxy_count": len(proxies),
            "proxy_render_mode": (
                "hidden_registered_collision_and_sensor_geometry"
                if _forest_review_geometry_enabled(args)
                else "visible_debug_geometry"
            ),
            "rock_seating": (
                "runtime_USD_lowest_20mm_mesh_vertex_band_terrain_support"
                if _forest_review_geometry_enabled(args)
                else "upstream_origin_at_centre_terrain_height"
            ),
            "full_grass_field_instantiated": False,
            "upstream_population_generator_used": False,
            "terrain_seed_injection": (
                "FractalNoise(seed=14) plus numpy seed 14 for BasicMicrorelief; "
                "forest_gen v0.3.8 otherwise constructs unseeded RandomState and "
                "random.Random(None) instances"
            ),
            "vegetation_placement": "task-owned deterministic bounded layout",
            "selection_reason": (
                "retain the upstream terrain algorithm and source visual assets "
                "without invoking its nondeterministic full population generator or "
                "instantiating thousands of independent grass prims"
            ),
            "placement_reason": (
                "place one registered tree across the fixed SCAN start-to-goal corridor"
                if _forest_navigation_enabled(args)
                else "guarantee visible and sensor-observable obstacles beside, not in, the short open-loop route"
            ),
            "v12_command_terrain_binding": {
                "terrain_name": "main",
                "maximum_range_source": "unchanged V12 flat-terrain range",
                "live_commands": (
                    "external Foxy SCAN closed-loop command stream"
                    if _forest_navigation_enabled(args)
                    else "overwritten by the recorded preview schedule"
                ),
            },
        },
        "visuals": identity_visuals,
        "proxies": proxies,
    }
    print(
        "[forest-v4] layout_ready "
        f"visuals={len(visual_specs)} proxies={len(proxies)}",
        flush=True,
    )
    return {
        "terrain": terrain,
        "visuals": visual_specs,
        "proxies": proxies,
        "spawn_world_xyz_m": spawn_world,
        "identity": identity,
    }


def _urdf_contract(path: Path):
    root = ET.parse(path).getroot()
    links = root.findall("link")
    joints = root.findall("joint")
    mass_by_link = {}
    inertia_by_link = {}
    collision_count_by_link = {}
    mesh_files = {}
    links_without_inertial = []
    for link in links:
        name = link.attrib["name"]
        inertial = link.find("inertial")
        if inertial is None or inertial.find("mass") is None:
            links_without_inertial.append(name)
        else:
            mass_by_link[name] = float(inertial.find("mass").attrib["value"])
            inertia = inertial.find("inertia")
            if inertia is not None:
                inertia_by_link[name] = {
                    key: float(inertia.attrib[key])
                    for key in ("ixx", "ixy", "ixz", "iyy", "iyz", "izz")
                }
        collision_count_by_link[name] = len(link.findall("collision"))
        for mesh in link.findall(".//mesh"):
            filename = mesh.attrib["filename"]
            mesh_path = (path.parent / filename).resolve()
            if not mesh_path.is_file():
                raise AdapterFailure(f"URDF mesh is missing: {mesh_path}")
            mesh_files[filename] = {
                "sha256": _sha256(mesh_path),
                "bytes": mesh_path.stat().st_size,
            }
    movable_joint_count = sum(
        joint.attrib.get("type") not in ("fixed", "floating") for joint in joints
    )
    return {
        "robot_name": root.attrib.get("name"),
        "link_count": len(links),
        "joint_count": len(joints),
        "movable_joint_count": movable_joint_count,
        "fixed_joint_count": sum(
            joint.attrib.get("type") == "fixed" for joint in joints
        ),
        "total_declared_mass_kg": sum(mass_by_link.values()),
        "mass_by_link_kg": mass_by_link,
        "inertia_by_link_kg_m2": inertia_by_link,
        "collision_count": sum(collision_count_by_link.values()),
        "collision_count_by_link": collision_count_by_link,
        "links_without_inertial": links_without_inertial,
        "referenced_meshes": mesh_files,
    }


def _candidate_name(args) -> str:
    if _office_crowd_enabled(args):
        return "V12 model_149999 on Lite3 Pro sensor rig SCAN Office L0 eight-person trial"
    if _office_enabled(args):
        return "V12 model_149999 on Lite3 Pro sensor rig Office L0 static support"
    if _forest_v8_enabled(args):
        return "V12 model_149999 on Lite3 Pro sensor rig v8 human SCAN forest navigation"
    if _forest_v7_enabled(args):
        return "V12 model_149999 on Lite3 Pro sensor rig v7 dynamic SCAN forest navigation"
    if _forest_v6_enabled(args):
        return "V12 model_149999 on Lite3 Pro sensor rig v6 1mps SCAN forest navigation"
    if _forest_navigation_enabled(args):
        return "V12 model_149999 on Lite3 Pro sensor rig v5 SCAN forest navigation"
    if _forest_preview_enabled(args):
        return "V12 model_149999 on Lite3 Pro sensor rig v4 forest preview"
    if _sensor_rig_enabled(args):
        return "V12 model_149999 on Lite3 Pro sensor rig v3"
    return "V12 model_149999 fallback"


def _asset_identity(args):
    if not _sensor_rig_enabled(args):
        return {
            "mode": "legacy_v12_task_asset",
            "asset_path": None,
            "asset_sha256": None,
            "canonical_asset_path": None,
            "canonical_asset_sha256": None,
        }
    canonical_contract = _urdf_contract(args.canonical_robot_asset.resolve())
    isaac_contract = _urdf_contract(args.robot_asset.resolve())
    expected_topology = (24, 23, 12)
    for label, contract in (
        ("canonical", canonical_contract),
        ("Isaac-safe", isaac_contract),
    ):
        observed_topology = (
            contract["link_count"],
            contract["joint_count"],
            contract["movable_joint_count"],
        )
        if observed_topology != expected_topology:
            raise AdapterFailure(
                f"{label} sensor-rig topology mismatch: {observed_topology}"
            )
        if contract["collision_count"] != 29:
            raise AdapterFailure(
                f"{label} sensor-rig collision count mismatch: "
                f"{contract['collision_count']}"
            )
    if isaac_contract["links_without_inertial"]:
        raise AdapterFailure("Isaac-safe sensor-rig still has inertial-less links")
    return {
        "mode": "v12_policy_on_pinned_sensor_rig",
        "asset_path": str(args.robot_asset.resolve()),
        "asset_sha256": _sha256(args.robot_asset),
        "canonical_asset_path": str(args.canonical_robot_asset.resolve()),
        "canonical_asset_sha256": _sha256(args.canonical_robot_asset),
        "merge_fixed_joints": False,
        "required_links": list(SENSOR_RIG_REQUIRED_LINKS),
        "canonical_urdf_contract": canonical_contract,
        "isaac_urdf_contract": isaac_contract,
        "composition_boundary": (
            "Only the V12 robot spawn asset and fixed-joint preservation are "
            "changed; checkpoint, policy loader, observations, actions, "
            "actuators, default pose, command schedule, and controller remain V12."
        ),
    }


def _depth_gate(depth_records):
    checks = {
        "frames_present": bool(depth_records),
        "timestamps_advance": len(depth_records) >= 2
        and all(
            right["sim_time_seconds"] > left["sim_time_seconds"]
            for left, right in zip(depth_records, depth_records[1:])
        ),
        "finite_depth": bool(depth_records)
        and all(row["nonfinite_depth_count"] == 0 for row in depth_records),
        "valid_depth_returns": bool(depth_records)
        and max(row["valid_depth_pixel_count"] for row in depth_records) > 0,
        "obstacle_returns": bool(depth_records)
        and max(row["obstacle_surface_pixel_count"] for row in depth_records) > 0,
        "intrinsics_present": bool(depth_records)
        and all(len(row["intrinsic_matrix"]) == 3 for row in depth_records),
    }
    pose_displacement = 0.0
    if len(depth_records) >= 2:
        pose_displacement = math.dist(
            depth_records[0]["sensor_position_w"],
            depth_records[-1]["sensor_position_w"],
        )
    checks["pose_displacement_m_value"] = pose_displacement
    checks["pose_dependent_frame"] = pose_displacement >= 0.10
    required = (
        "frames_present",
        "timestamps_advance",
        "finite_depth",
        "valid_depth_returns",
        "obstacle_returns",
        "intrinsics_present",
        "pose_dependent_frame",
    )
    return checks, all(bool(checks[name]) for name in required)


def _capture_v12_task_contract(env_cfg):
    """Fail closed unless the registry still resolves the pinned V12 controller."""

    robot_cfg = env_cfg.scene.robot
    original_asset = Path(robot_cfg.spawn.asset_path).resolve()
    if not original_asset.is_file():
        raise AdapterFailure(f"pinned V12 task asset is missing: {original_asset}")
    original_asset_sha256 = _sha256(original_asset)
    if original_asset_sha256 != PINNED_V12_ROBOT_ASSET_SHA256:
        raise AdapterFailure("pinned V12 task asset hash mismatch before composition")
    expected_joint_pos = {
        ".*HipX_joint": 0.0,
        ".*HipY_joint": -0.8,
        ".*Knee_joint": 1.6,
    }
    actual_joint_pos = dict(robot_cfg.init_state.joint_pos)
    if tuple(robot_cfg.init_state.pos) != (0.0, 0.0, 0.35):
        raise AdapterFailure("V12 default base pose changed before composition")
    if actual_joint_pos != expected_joint_pos:
        raise AdapterFailure("V12 default joint pose changed before composition")
    actuator_contract = {}
    for name, expected_effort, expected_velocity in (
        ("Hip", 24.0, 26.2),
        ("Knee", 36.0, 17.3),
    ):
        if name not in robot_cfg.actuators:
            raise AdapterFailure(f"V12 actuator group is missing: {name}")
        actuator = robot_cfg.actuators[name]
        observed = {
            "class": type(actuator).__name__,
            "effort_limit": float(actuator.effort_limit),
            "velocity_limit": float(actuator.velocity_limit),
            "stiffness": float(actuator.stiffness),
            "damping": float(actuator.damping),
            "min_delay": int(actuator.min_delay),
            "max_delay": int(actuator.max_delay),
        }
        if observed["class"] != "Lite3ActuatorCfg":
            raise AdapterFailure(f"V12 actuator class changed for {name}")
        if (
            observed["effort_limit"] != expected_effort
            or observed["velocity_limit"] != expected_velocity
            or observed["stiffness"] != 20.0
            or observed["damping"] != 0.5
            or observed["min_delay"] != 0
            or observed["max_delay"] != 4
        ):
            raise AdapterFailure(f"V12 actuator contract changed for {name}")
        actuator_contract[name] = observed
    return {
        "registry_task": DEFAULT_TASK,
        "original_robot_asset_path": str(original_asset),
        "original_robot_asset_sha256": original_asset_sha256,
        "default_base_position_m": [0.0, 0.0, 0.35],
        "default_joint_position_by_regex": expected_joint_pos,
        "actuators": actuator_contract,
        "policy_observation_dimension": POLICY_OBSERVATION_DIMENSION,
        "action_dimension": 12,
    }


def _activate_vendored_rsl_rl(vendored_root: Path) -> Path:
    """Require the complete RSL-RL package recovered from the pinned V12 run."""

    import rsl_rl

    package_dir = vendored_root.resolve() / "rsl_rl"
    package_source = Path(rsl_rl.__file__ or "").resolve()
    required_files = (
        package_dir / "env" / "vec_env.py",
        package_dir / "modules" / "actor_critic_moe_cts.py",
    )
    missing = [path for path in required_files if not path.is_file()]
    if missing:
        raise AdapterFailure(
            "pinned V12 RSL-RL runtime is incomplete: "
            + ", ".join(str(path) for path in missing)
        )
    try:
        package_source.relative_to(package_dir)
    except ValueError as error:
        raise AdapterFailure(
            f"RSL-RL resolved outside the pinned V12 runtime: {package_source}"
        ) from error
    return package_dir


def _load_inference_policy(wrapped_env, agent_cfg, checkpoint: Path, device: str):
    """Construct only the immutable V12 inference network, not its training split."""

    import torch
    from rsl_rl.modules import ActorCriticMoECTS
    from rsl_rl.utils import resolve_obs_groups

    train_cfg = agent_cfg.to_dict()
    observations = wrapped_env.get_observations()
    obs_groups = resolve_obs_groups(
        observations, train_cfg["obs_groups"], ["critic"]
    )
    policy_cfg = dict(train_cfg["policy"])
    class_name = policy_cfg.pop("class_name")
    if class_name != "ActorCriticMoECTS":
        raise AdapterFailure(f"unexpected V12 policy class: {class_name}")
    policy_module = ActorCriticMoECTS(
        observations, obs_groups, wrapped_env.num_actions, **policy_cfg
    ).to(device)
    checkpoint_payload = torch.load(
        checkpoint, weights_only=False, map_location=device
    )
    if "model_state_dict" not in checkpoint_payload:
        raise AdapterFailure("V12 checkpoint has no model_state_dict")
    policy_module.load_state_dict(checkpoint_payload["model_state_dict"], strict=True)
    policy_module.eval()
    source = Path(inspect.getsourcefile(ActorCriticMoECTS) or "").resolve()
    return policy_module.act_inference, policy_module, observations, source


def _configure_environment(env_cfg, args, forest_layout=None) -> None:
    env_cfg.scene.num_envs = 1
    env_cfg.seed = args.seed
    env_cfg.sim.device = args.device
    env_cfg.observations.policy.enable_corruption = False
    env_cfg.sim.enable_scene_query_support = True
    if _sensor_rig_enabled(args):
        # V3 is a cross-composition test, not a new policy bundle. Preserve the
        # complete V12 task configuration and replace only the physical URDF.
        env_cfg.scene.robot.spawn.asset_path = str(args.robot_asset.resolve())
        env_cfg.scene.robot.spawn.merge_fixed_joints = False
    if _office_enabled(args):
        start_x, start_y = args.office_start_xy
        original_z = float(env_cfg.scene.robot.init_state.pos[2])
        env_cfg.scene.robot.init_state.pos = (start_x, start_y, original_z)
    if args.video_path is not None and _office_enabled(args):
        start_x, start_y = args.office_start_xy
        start_yaw = float(getattr(args, "office_start_yaw", None) or -0.6435)
        env_cfg.viewer.origin_type = "world"
        env_cfg.viewer.eye = (
            start_x - 1.2 * math.cos(start_yaw),
            start_y - 1.2 * math.sin(start_yaw),
            1.4,
        )
        env_cfg.viewer.lookat = (
            start_x + 1.5 * math.cos(start_yaw),
            start_y + 1.5 * math.sin(start_yaw),
            0.35,
        )
        if _office_review_presentation_enabled(args):
            quality = _office_review_quality_profile()
            env_cfg.viewer.resolution = (
                int(quality["resolution_width"]),
                int(quality["resolution_height"]),
            )
        else:
            env_cfg.viewer.resolution = VIDEO_RESOLUTION
    elif args.video_path is not None and forest_layout is None:
        env_cfg.viewer.origin_type = "world"
        env_cfg.viewer.eye = VIDEO_CAMERA_EYE
        env_cfg.viewer.lookat = VIDEO_CAMERA_LOOKAT
        env_cfg.viewer.resolution = VIDEO_RESOLUTION
    elif args.video_path is not None and _forest_navigation_enabled(args):
        spawn_x, spawn_y, spawn_z = forest_layout["spawn_world_xyz_m"]
        env_cfg.viewer.origin_type = "world"
        env_cfg.viewer.eye = (spawn_x + 1.5, spawn_y - 7.5, spawn_z + 5.0)
        env_cfg.viewer.lookat = (spawn_x + 3.0, spawn_y, spawn_z + 0.45)
        env_cfg.viewer.resolution = VIDEO_RESOLUTION
    elif args.video_path is not None:
        spawn_x, spawn_y, spawn_z = forest_layout["spawn_world_xyz_m"]
        env_cfg.viewer.origin_type = "world"
        env_cfg.viewer.eye = (spawn_x - 6.0, spawn_y, spawn_z + 2.8)
        env_cfg.viewer.lookat = (spawn_x + 1.5, spawn_y, spawn_z + 0.5)
        env_cfg.viewer.resolution = VIDEO_RESOLUTION
    if args.mode == "external":
        env_cfg.episode_length_s = max(
            float(env_cfg.episode_length_s), args.duration_seconds + 5.0
        )

    events = getattr(env_cfg, "events", None)
    if events is not None:
        for name in (
            "randomize_rigid_body_mass_base",
            "randomize_rigid_body_mass_others",
            "randomize_com_positions",
            "randomize_actuator_gains",
            "randomize_motor_zero_offset",
            "randomize_push_robot",
            "randomize_apply_external_force_torque",
            "randomize_rigid_body_material",
        ):
            if hasattr(events, name):
                setattr(events, name, None)
        if getattr(events, "reset_robot_joints", None) is not None:
            events.reset_robot_joints.params["position_range"] = (1.0, 1.0)
            events.reset_robot_joints.params["velocity_range"] = (0.0, 0.0)
        if getattr(events, "reset_base", None) is not None:
            events.reset_base.params["pose_range"] = {
                "x": (0.0, 0.0),
                "y": (0.0, 0.0),
                "z": (0.0, 0.0),
                "yaw": (0.0, 0.0),
            }
            events.reset_base.params["velocity_range"] = {
                axis: (0.0, 0.0)
                for axis in ("x", "y", "z", "roll", "pitch", "yaw")
            }
    curriculum = getattr(env_cfg, "curriculum", None)
    if curriculum is not None:
        for name in (
            "terrain_levels",
            "command_levels_lin_vel",
            "command_levels_ang_vel",
            "base_linear_velocity",
            "base_height_l2",
        ):
            if hasattr(curriculum, name):
                setattr(curriculum, name, None)

    command_cfg = env_cfg.commands.base_velocity
    command_cfg.dynamic_resample_commands = False
    command_cfg.command_range_curriculum = []
    command_cfg.zero_command_curriculum = None
    command_cfg.limit_vel_prob = 0.0
    command_cfg.limit_ang_vel_at_zero_command_prob = 0.0
    command_cfg.resampling_time = 1000.0
    command_cfg.resampling_time_range = (1000.0, 1000.0)
    command_cfg.ranges.lin_vel_x = (0.0, 0.0)
    command_cfg.ranges.lin_vel_y = (0.0, 0.0)
    command_cfg.ranges.ang_vel_yaw = (0.0, 0.0)
    if forest_layout is not None:
        command_cfg.terrain_max_command_ranges["main"] = dict(
            command_cfg.terrain_max_command_ranges["flat"]
        )

    if _office_enabled(args):
        from isaaclab.terrains import TerrainImporterCfg

        command_contract_terrain = env_cfg.scene.terrain.terrain_generator
        if command_contract_terrain is None:
            raise AdapterFailure("pinned V12 task has no command-contract terrain generator")
        env_cfg.scene.terrain = TerrainImporterCfg(
            prim_path=GROUND_MESH_PRIM,
            terrain_type="usd",
            usd_path=str(args.office_usd_path.resolve()),
            env_spacing=1.0,
            use_terrain_origins=False,
            terrain_generator=command_contract_terrain,
            debug_vis=False,
        )
    elif forest_layout is None:
        terrain = env_cfg.scene.terrain.terrain_generator
        if terrain is None or "flat" not in terrain.sub_terrains:
            raise AdapterFailure("pinned V12 task has no flat terrain generator")
        terrain.num_rows = 1
        terrain.num_cols = 1
        terrain.curriculum = False
        terrain.difficulty_range = (0.0, 0.0)
        terrain.use_cache = False
        for name, sub_cfg in terrain.sub_terrains.items():
            sub_cfg.proportion = 1.0 if name == "flat" else 0.0
    else:
        import isaaclab.sim as sim_utils

        terrain = forest_layout["terrain"].to_cfg()
        terrain.num_rows = 1
        terrain.num_cols = 1
        terrain.curriculum = False
        terrain.difficulty_range = (0.0, 0.0)
        terrain.seed = args.forest_seed
        terrain.use_cache = False
        terrain.color_scheme = "none"
        env_cfg.scene.terrain.terrain_generator = terrain
        env_cfg.scene.terrain.visual_material = sim_utils.PreviewSurfaceCfg(
            diffuse_color=(0.16, 0.24, 0.08), roughness=0.92
        )
    env_cfg.scene.terrain.max_init_terrain_level = 0

    if args.course == "single_box":
        import isaaclab.sim as sim_utils
        from isaaclab.assets import AssetBaseCfg

        env_cfg.scene.scan_obstacle = AssetBaseCfg(
            prim_path="/World/ground/scan_obstacle",
            spawn=sim_utils.CuboidCfg(
                size=COURSE_OBSTACLE_SIZE,
                collision_props=sim_utils.CollisionPropertiesCfg(),
                visual_material=sim_utils.PreviewSurfaceCfg(
                    diffuse_color=(0.8, 0.1, 0.1)
                ),
            ),
            init_state=AssetBaseCfg.InitialStateCfg(pos=COURSE_OBSTACLE_CENTER),
        )

    if _office_enabled(args):
        import isaaclab.sim as sim_utils
        from isaaclab.assets import AssetBaseCfg

        review_lighting = _office_review_presentation_enabled(args) and args.office_review_lighting_profile == "high_contrast"
        env_cfg.scene.office_light = AssetBaseCfg(
            prim_path="/World/OfficeLight",
            spawn=sim_utils.DomeLightCfg(
                intensity=(args.office_review_dome_light_intensity if review_lighting else 900.0),
                color=((1.0, 0.96, 0.90) if review_lighting else (0.9, 0.9, 0.9)),
            ),
        )

    if _office_crowd_enabled(args):
        import isaaclab.sim as sim_utils
        from isaaclab.assets import AssetBaseCfg, RigidObjectCfg

        for index, route in enumerate(args.office_routes):
            proxy_name = f"office_pedestrian_{index}"
            visual_name = f"office_human_visual_{index}"
            proxy_spawn = sim_utils.CapsuleCfg(
                radius=route.radius_m,
                height=OFFICIAL_HUMAN_CAPSULE_HEIGHT_M,
                rigid_props=sim_utils.RigidBodyPropertiesCfg(
                    kinematic_enabled=True,
                    disable_gravity=True,
                ),
                mass_props=sim_utils.MassPropertiesCfg(mass=20.0),
                collision_props=sim_utils.CollisionPropertiesCfg(),
            )
            proxy_spawn.visible = False
            setattr(
                env_cfg.scene,
                proxy_name,
                RigidObjectCfg(
                    prim_path=(
                        f"{{ENV_REGEX_NS}}/{OFFICE_PEDESTRIAN_PRIM_PREFIX}_{index}"
                    ),
                    spawn=proxy_spawn,
                    init_state=RigidObjectCfg.InitialStateCfg(
                        pos=(*route.start_xy_m, 0.5 * OFFICIAL_HUMAN_CAPSULE_HEIGHT_M)
                    ),
                    collision_group=-1,
                ),
            )
            setattr(
                env_cfg.scene,
                visual_name,
                AssetBaseCfg(
                    prim_path=f"{OFFICE_HUMAN_VISUAL_PREFIX}_{index}",
                    spawn=sim_utils.UsdFileCfg(
                        usd_path=str(args.office_human_visual_usd_path),
                    ),
                    init_state=AssetBaseCfg.InitialStateCfg(
                        pos=(*route.start_xy_m, 0.0)
                    ),
                    collision_group=-1,
                ),
            )

    if forest_layout is not None:
        import isaaclab.sim as sim_utils
        from isaaclab.assets import AssetBaseCfg

        for visual in forest_layout["visuals"]:
            visual_cfg = copy.deepcopy(visual["asset"].to_cfg())
            visual_cfg.prim_path = visual["prim_path"]
            visual_cfg.init_state.pos = visual["world_position_m"]
            # forest_gen currently emits a zero quaternion. Normalize it at the
            # adapter boundary and record that decision in the run identity.
            visual_cfg.init_state.rot = (1.0, 0.0, 0.0, 0.0)
            visual_cfg.collision_group = -1
            setattr(env_cfg.scene, visual["name"], visual_cfg)
        for proxy in forest_layout["proxies"]:
            if proxy["shape"] == "cylinder":
                spawn_cfg = sim_utils.CylinderCfg(
                    radius=0.5 * proxy["size_m"][0],
                    height=proxy["size_m"][2],
                    collision_props=sim_utils.CollisionPropertiesCfg(),
                    visual_material=sim_utils.PreviewSurfaceCfg(
                        diffuse_color=(0.19, 0.09, 0.035), roughness=0.88
                    ),
                )
            else:
                spawn_cfg = sim_utils.CuboidCfg(
                    size=proxy["size_m"],
                    collision_props=sim_utils.CollisionPropertiesCfg(),
                    visual_material=sim_utils.PreviewSurfaceCfg(
                        diffuse_color=(0.24, 0.25, 0.22), roughness=0.95
                    ),
                )
            spawn_cfg.visible = bool(proxy["render_visible"])
            proxy_cfg = AssetBaseCfg(
                prim_path=proxy["prim_path"],
                spawn=spawn_cfg,
                init_state=AssetBaseCfg.InitialStateCfg(pos=proxy["center_m"]),
                collision_group=-1,
            )
            setattr(env_cfg.scene, proxy["name"], proxy_cfg)

        if _dynamic_obstacle_enabled(args):
            from isaaclab.assets import RigidObjectCfg

            spec = _dynamic_obstacle_spec(args)
            initial = dynamic_obstacle_state(
                0.0,
                spec,
                lambda x, y: _forest_height_world(forest_layout, x, y),
            )
            spawn = forest_layout["spawn_world_xyz_m"]
            centre = initial["center_xyz_m"]
            relative_centre = tuple(
                float(centre[index]) - float(spawn[index]) for index in range(3)
            )
            if _forest_v8_official_enabled(args):
                registered = official_human_registered_state(
                    initial,
                    spec,
                    source_foot_z_m=OFFICIAL_HUMAN_SOURCE_FOOT_Z_M,
                    source_visible_top_z_m=OFFICIAL_HUMAN_SOURCE_VISIBLE_TOP_Z_M,
                    source_forward_yaw_radians=(
                        OFFICIAL_HUMAN_SOURCE_FORWARD_YAW_RADIANS
                    ),
                )
                env_cfg.scene.dynamic_human_visual = AssetBaseCfg(
                    prim_path=DYNAMIC_HUMAN_VISUAL_RUNTIME_PRIM,
                    spawn=sim_utils.UsdFileCfg(
                        usd_path=str(args.dynamic_human_visual_usd_path),
                    ),
                    init_state=AssetBaseCfg.InitialStateCfg(
                        pos=registered["visual_root_xyz_m"],
                        rot=registered["visual_quaternion_wxyz"],
                    ),
                    collision_group=-1,
                )
            dynamic_spawn = (
                sim_utils.UsdFileCfg(
                    usd_path=str(args.dynamic_human_usd_path),
                    rigid_props=sim_utils.RigidBodyPropertiesCfg(
                        kinematic_enabled=True,
                        disable_gravity=True,
                    ),
                    mass_props=sim_utils.MassPropertiesCfg(mass=20.0),
                )
                if _forest_v8_any_enabled(args)
                else sim_utils.CylinderCfg(
                    radius=spec.radius_m,
                    height=spec.height_m,
                    rigid_props=sim_utils.RigidBodyPropertiesCfg(
                        kinematic_enabled=True,
                        disable_gravity=True,
                    ),
                    mass_props=sim_utils.MassPropertiesCfg(mass=20.0),
                    collision_props=sim_utils.CollisionPropertiesCfg(),
                    visual_material=sim_utils.PreviewSurfaceCfg(
                        diffuse_color=(1.0, 0.24, 0.02),
                        emissive_color=(0.12, 0.01, 0.0),
                        roughness=0.65,
                    ),
                )
            )
            env_cfg.scene.dynamic_obstacle = RigidObjectCfg(
                prim_path=DYNAMIC_OBSTACLE_PRIM_EXPR,
                spawn=dynamic_spawn,
                init_state=RigidObjectCfg.InitialStateCfg(pos=relative_centre),
                collision_group=-1,
            )

    from isaaclab.sensors import MultiMeshRayCasterCfg, patterns
    from isaaclab.sensors.ray_caster import MultiMeshRayCasterCameraCfg

    pitch_radians = math.radians(args.sensor_pitch_degrees)
    sensor_rotation_wxyz = (
        math.cos(pitch_radians / 2.0),
        0.0,
        math.sin(pitch_radians / 2.0),
        0.0,
    )
    sensor_rig = _sensor_rig_enabled(args)
    environment_targets = [GROUND_MESH_PRIM]
    if args.course == "single_box":
        environment_targets.append(OBSTACLE_MESH_PRIM)
    elif forest_layout is not None:
        environment_targets.extend(
            proxy["prim_path"] for proxy in forest_layout["proxies"]
        )
    lidar_targets = list(environment_targets)
    if _office_enabled(args):
        lidar_targets.append(
            MultiMeshRayCasterCfg.RaycastTargetCfg(
                prim_expr=f"{GROUND_MESH_PRIM}/terrain",
                merge_prim_meshes=True,
                track_mesh_transforms=False,
            )
        )
    if _office_crowd_enabled(args):
        lidar_targets.extend(
            MultiMeshRayCasterCfg.RaycastTargetCfg(
                prim_expr=(
                    f"{{ENV_REGEX_NS}}/{OFFICE_PEDESTRIAN_PRIM_PREFIX}_{index}"
                ),
                merge_prim_meshes=True,
                track_mesh_transforms=True,
            )
            for index in range(len(args.office_routes))
        )
    if _dynamic_obstacle_enabled(args):
        dynamic_targets = (
            _official_human_sensor_exprs()
            if _forest_v8_official_enabled(args)
            else
            _dynamic_human_part_exprs()
            if _forest_v8_enabled(args)
            else (DYNAMIC_OBSTACLE_PRIM_EXPR,)
        )
        lidar_targets.extend(
            MultiMeshRayCasterCfg.RaycastTargetCfg(
                prim_expr=prim_expr,
                merge_prim_meshes=True,
                track_mesh_transforms=True,
            )
            for prim_expr in dynamic_targets
        )
    if sensor_rig:
        lidar_targets.extend(
            MultiMeshRayCasterCfg.RaycastTargetCfg(
                prim_expr=f"{{ENV_REGEX_NS}}/Robot/{link}/visuals",
                merge_prim_meshes=True,
                track_mesh_transforms=True,
            )
            for link in MID360_SELF_OCCLUSION_LINKS
        )
    lidar_pattern_cfg = (
        _mid360_pattern_cfg(patterns, args.mid360_pattern_table)
        if _official_mid360_enabled(args)
        else patterns.LidarPatternCfg(
            channels=args.lidar_channels,
            vertical_fov_range=(args.lidar_vertical_min, args.lidar_vertical_max),
            horizontal_fov_range=(-180.0, 180.0),
            horizontal_res=args.lidar_horizontal_resolution,
        )
    )
    env_cfg.scene.navigation_lidar = MultiMeshRayCasterCfg(
        prim_path=(
            f"{{ENV_REGEX_NS}}/Robot/{MID360_FRAME}"
            if sensor_rig
            else "{ENV_REGEX_NS}/Robot/TORSO"
        ),
        update_period=args.sensor_period,
        offset=MultiMeshRayCasterCfg.OffsetCfg(
            pos=(0.0, 0.0, 0.0) if sensor_rig else tuple(args.sensor_translation),
            rot=(1.0, 0.0, 0.0, 0.0) if sensor_rig else sensor_rotation_wxyz,
        ),
        ray_alignment="base",
        pattern_cfg=lidar_pattern_cfg,
        max_distance=args.lidar_max_range,
        # Keep the obstacle as a distinct target. The terrain height scanner
        # already caches /World/ground before this sensor initializes, so using
        # the parent alone would silently reuse a terrain-only Warp mesh.
        mesh_prim_paths=lidar_targets,
        update_mesh_ids=False,
        debug_vis=False,
    )
    if sensor_rig:
        depth_targets = list(environment_targets)
        if _office_enabled(args):
            depth_targets.append(
                MultiMeshRayCasterCfg.RaycastTargetCfg(
                    prim_expr=f"{GROUND_MESH_PRIM}/terrain",
                    merge_prim_meshes=True,
                    track_mesh_transforms=False,
                )
            )
        if _office_crowd_enabled(args):
            depth_targets.extend(
                MultiMeshRayCasterCfg.RaycastTargetCfg(
                    prim_expr=(
                        f"{{ENV_REGEX_NS}}/{OFFICE_PEDESTRIAN_PRIM_PREFIX}_{index}"
                    ),
                    merge_prim_meshes=True,
                    track_mesh_transforms=True,
                )
                for index in range(len(args.office_routes))
            )
        if _dynamic_obstacle_enabled(args):
            dynamic_targets = (
                _official_human_sensor_exprs()
                if _forest_v8_official_enabled(args)
                else
                _dynamic_human_part_exprs()
                if _forest_v8_enabled(args)
                else (DYNAMIC_OBSTACLE_PRIM_EXPR,)
            )
            depth_targets.extend(
                MultiMeshRayCasterCfg.RaycastTargetCfg(
                    prim_expr=prim_expr,
                    merge_prim_meshes=True,
                    track_mesh_transforms=True,
                )
                for prim_expr in dynamic_targets
            )
        depth_targets.extend(
            MultiMeshRayCasterCfg.RaycastTargetCfg(
                prim_expr=f"{{ENV_REGEX_NS}}/Robot/{link}/visuals",
                merge_prim_meshes=True,
                track_mesh_transforms=True,
            )
            for link in D435I_SELF_OCCLUSION_LINKS
        )
        env_cfg.scene.navigation_depth_camera = MultiMeshRayCasterCameraCfg(
            prim_path=f"{{ENV_REGEX_NS}}/Robot/{D435I_FRAME}",
            update_period=args.depth_period,
            offset=MultiMeshRayCasterCameraCfg.OffsetCfg(
                pos=(0.0, 0.0, 0.0),
                rot=(1.0, 0.0, 0.0, 0.0),
                convention="ros",
            ),
            data_types=["distance_to_image_plane"],
            depth_clipping_behavior="max",
            pattern_cfg=patterns.PinholeCameraPatternCfg(
                focal_length=args.depth_focal_length,
                horizontal_aperture=args.depth_horizontal_aperture,
                width=args.depth_width,
                height=args.depth_height,
            ),
            mesh_prim_paths=depth_targets,
            update_mesh_ids=False,
            max_distance=args.depth_max_range,
            debug_vis=False,
        )


def _policy_command_evidence(observation, command):
    policy_observation = observation["policy"]
    if tuple(policy_observation.shape) != (1, POLICY_OBSERVATION_DIMENSION):
        raise AdapterFailure(
            f"V12 policy observation shape {tuple(policy_observation.shape)} != "
            f"(1, {POLICY_OBSERVATION_DIMENSION})"
        )
    history = policy_observation[
        0,
        COMMAND_HISTORY_OFFSET : COMMAND_HISTORY_OFFSET + COMMAND_HISTORY_LENGTH * 3,
    ].reshape(COMMAND_HISTORY_LENGTH, 3)
    expected = policy_observation.new_tensor(command)
    errors = (history - expected).abs().amax(dim=1)
    best_error, best_index = errors.min(dim=0)
    error = float(best_error.detach().cpu().item())
    if error > 1.0e-6:
        raise AdapterFailure(
            f"V12 command absent from policy observation history: error={error}"
        )
    selected = history[int(best_index.item())]
    return _tensor_list(selected), error, int(best_index.item())


def _sensor_gate(sensor_records):
    checks = {
        "frames_present": bool(sensor_records),
        "nonempty": bool(sensor_records)
        and all(row["point_count"] > 0 for row in sensor_records),
        "finite": bool(sensor_records)
        and all(row["finite_point_count"] == row["point_count"] for row in sensor_records),
        "timestamps_advance": len(sensor_records) >= 2
        and all(
            right["sim_time_seconds"] > left["sim_time_seconds"]
            for left, right in zip(sensor_records, sensor_records[1:])
        ),
        "ground_returns": bool(sensor_records)
        and max(row["ground_hit_count"] for row in sensor_records) > 0,
        "obstacle_returns": bool(sensor_records)
        and max(row["obstacle_surface_hit_count"] for row in sensor_records) > 0,
    }
    pose_displacement = 0.0
    centroid_displacement = 0.0
    if len(sensor_records) >= 2:
        first = sensor_records[0]
        last = sensor_records[-1]
        pose_displacement = math.dist(
            first["sensor_position_w"], last["sensor_position_w"]
        )
        centroid_displacement = math.dist(
            first["centroid_sensor"], last["centroid_sensor"]
        )
    checks["pose_displacement_m_value"] = pose_displacement
    checks["cloud_centroid_displacement_m_value"] = centroid_displacement
    checks["pose_dependent_geometry"] = (
        pose_displacement >= 0.10 and centroid_displacement >= 0.02
    )
    required = (
        "frames_present",
        "nonempty",
        "finite",
        "timestamps_advance",
        "ground_returns",
        "obstacle_returns",
        "pose_dependent_geometry",
    )
    return checks, all(bool(checks[name]) for name in required)


def _forest_obstacle_hit_mask(points_w, proxies, torch):
    mask = torch.zeros(points_w.shape[0], dtype=torch.bool, device=points_w.device)
    finite = torch.isfinite(points_w).all(dim=-1)
    for proxy in proxies:
        lower = points_w.new_tensor(proxy["bounds_min_m"]) - 0.015
        upper = points_w.new_tensor(proxy["bounds_max_m"]) + 0.015
        mask |= finite & ((points_w >= lower) & (points_w <= upper)).all(dim=-1)
    return mask


def _forest_proxy_hit_counts(points_w, proxies, torch):
    """Count evidence hits per declared proxy without changing planner points."""

    finite = torch.isfinite(points_w).all(dim=-1)
    counts = {}
    for proxy in proxies:
        lower = points_w.new_tensor(proxy["bounds_min_m"]) - 0.015
        upper = points_w.new_tensor(proxy["bounds_max_m"]) + 0.015
        mask = finite & ((points_w >= lower) & (points_w <= upper)).all(dim=-1)
        counts[proxy["name"]] = int(mask.sum().item())
    return counts


def _dynamic_obstacle_hit_mask(points_w, center_xyz, spec, torch):
    """Classify rendered hits for evidence without altering planner input."""

    finite = torch.isfinite(points_w).all(dim=-1)
    centre = points_w.new_tensor(center_xyz)
    radial_distance = torch.linalg.vector_norm(points_w[:, :2] - centre[:2], dim=-1)
    half_height = 0.5 * float(spec.height_m)
    return (
        finite
        & (radial_distance <= float(spec.radius_m) + 0.02)
        & (points_w[:, 2] >= centre[2] - half_height - 0.02)
        & (points_w[:, 2] <= centre[2] + half_height + 0.02)
    )


def _forest_height_world(forest_layout, x_world: float, y_world: float) -> float:
    terrain = forest_layout["terrain"]
    side = float(forest_layout["identity"]["size_m"])
    return float(terrain.raw(x_world + 0.5 * side, y_world + 0.5 * side))


def _inspect_forest_geometry(stage, forest_layout, lidar, depth_camera):
    from pxr import Usd, UsdGeom, UsdPhysics

    def direct_paths(sensor) -> set[str]:
        return {
            value
            for value in sensor.cfg.mesh_prim_paths
            if isinstance(value, str)
        }

    lidar_paths = direct_paths(lidar)
    depth_paths = direct_paths(depth_camera)
    bbox_cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
        True,
        True,
    )

    def world_bounds(prim):
        if not prim.IsValid():
            return None
        aligned = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
        lower = tuple(float(value) for value in aligned.GetMin())
        upper = tuple(float(value) for value in aligned.GetMax())
        if not all(math.isfinite(value) for value in lower + upper):
            return None
        return {"min_m": lower, "max_m": upper}

    def visible_geometry(prim):
        result = []
        if not prim.IsValid():
            return result
        for descendant in Usd.PrimRange(prim, Usd.TraverseInstanceProxies()):
            if descendant.GetTypeName() not in (
                "Capsule",
                "Cone",
                "Cube",
                "Cylinder",
                "Mesh",
                "Sphere",
            ):
                continue
            imageable = UsdGeom.Imageable(descendant)
            if imageable and str(imageable.ComputeVisibility()) != "invisible":
                result.append(str(descendant.GetPath()))
        return result

    records = []
    for proxy in forest_layout["proxies"]:
        root = stage.GetPrimAtPath(proxy["prim_path"])
        collision_paths = []
        if root.IsValid():
            for prim in Usd.PrimRange(root, Usd.TraverseInstanceProxies()):
                if prim.HasAPI(UsdPhysics.CollisionAPI):
                    collision_paths.append(str(prim.GetPath()))
        visible_geometry_paths = visible_geometry(root)
        visual = next(
            item
            for item in forest_layout["visuals"]
            if item["name"] == proxy["visual_name"]
        )
        visual_prim = stage.GetPrimAtPath(visual["prim_path"])
        proxy_world_bounds = world_bounds(root)
        source_visual_world_bounds = world_bounds(visual_prim)
        declared_values = tuple(proxy["bounds_min_m"]) + tuple(
            proxy["bounds_max_m"]
        )
        actual_values = (
            ()
            if proxy_world_bounds is None
            else tuple(proxy_world_bounds["min_m"])
            + tuple(proxy_world_bounds["max_m"])
        )
        proxy_bounds_error = (
            math.inf
            if len(actual_values) != len(declared_values)
            else max(
                abs(float(actual) - float(declared))
                for actual, declared in zip(actual_values, declared_values)
            )
        )
        seating = visual.get("terrain_seating")
        source_visual_clearance = None
        source_visual_seated = True
        if visual["kind"] == "Rock" and seating is not None:
            source_visual_clearance = float(
                seating["minimum_support_clearance_m"]
            )
            source_visual_seated = (
                source_visual_world_bounds is not None
                and seating.get("method") == "lowest_mesh_vertex_band"
                and int(seating.get("sample_count", 0)) > 0
                and source_visual_clearance
                >= FOREST_ROCK_SEATING_CLEARANCE_M - 0.005
            )
        records.append(
            {
                "name": proxy["name"],
                "kind": proxy["kind"],
                "prim_path": proxy["prim_path"],
                "root_prim_valid": root.IsValid(),
                "collision_prim_paths": collision_paths,
                "expected_render_visible": bool(proxy["render_visible"]),
                "visible_geometry_prim_paths": visible_geometry_paths,
                "render_visibility_matches": bool(visible_geometry_paths)
                == bool(proxy["render_visible"]),
                "lidar_targeted": proxy["prim_path"] in lidar_paths,
                "depth_targeted": proxy["prim_path"] in depth_paths,
                "source_visual_prim_path": visual["prim_path"],
                "source_visual_prim_valid": visual_prim.IsValid(),
                "source_visual_visible_geometry_prim_paths": visible_geometry(
                    visual_prim
                ),
                "source_visual_world_bounds_m": source_visual_world_bounds,
                "source_visual_terrain_clearance_m": source_visual_clearance,
                "source_visual_support_method": (
                    None if seating is None else seating.get("method")
                ),
                "source_visual_seated": source_visual_seated,
                "terrain_seating": seating,
                "declared_bounds_min_m": proxy["bounds_min_m"],
                "declared_bounds_max_m": proxy["bounds_max_m"],
                "runtime_proxy_bounds_m": proxy_world_bounds,
                "proxy_bounds_max_error_m": proxy_bounds_error,
            }
        )
    checks = {
        "terrain_targeted_by_lidar": GROUND_MESH_PRIM in lidar_paths,
        "terrain_targeted_by_depth": GROUND_MESH_PRIM in depth_paths,
        "all_proxy_roots_exist": bool(records)
        and all(row["root_prim_valid"] for row in records),
        "all_proxies_have_collision": bool(records)
        and all(bool(row["collision_prim_paths"]) for row in records),
        "all_proxy_render_modes_match": bool(records)
        and all(row["render_visibility_matches"] for row in records),
        "all_proxy_bounds_match": bool(records)
        and all(row["proxy_bounds_max_error_m"] <= 0.005 for row in records),
        "all_proxies_targeted_by_lidar": bool(records)
        and all(row["lidar_targeted"] for row in records),
        "all_proxies_targeted_by_depth": bool(records)
        and all(row["depth_targeted"] for row in records),
        "all_source_visuals_exist": bool(records)
        and all(row["source_visual_prim_valid"] for row in records),
        "all_source_visuals_visible": bool(records)
        and all(
            bool(row["source_visual_visible_geometry_prim_paths"])
            for row in records
        ),
        "all_review_rocks_seated": bool(records)
        and all(row["source_visual_seated"] for row in records),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "proxy_records": records,
        "agreement_definition": (
            "each source visual is runtime-bounded and registered to one declared "
            "proxy root; the proxy has collision, matches its declared bounds and "
            "render mode, and is targeted by both ray sensors; each V6 rock is "
            "seated from real low-surface mesh vertices rather than an empty AABB corner"
        ),
    }


def _inspect_dynamic_obstacle(
    stage,
    dynamic_obstacle,
    lidar,
    depth_camera,
    expected_target_exprs=(DYNAMIC_OBSTACLE_PRIM_EXPR,),
    require_separate_official_visual=False,
):
    from pxr import Usd, UsdGeom, UsdPhysics

    def target_records(sensor):
        records = []
        for target in sensor.cfg.mesh_prim_paths:
            if isinstance(target, str):
                records.append(
                    {
                        "prim_expr": target,
                        "track_mesh_transforms": False,
                    }
                )
            else:
                records.append(
                    {
                        "prim_expr": str(target.prim_expr),
                        "track_mesh_transforms": bool(
                            target.track_mesh_transforms
                        ),
                    }
                )
        return records

    root = stage.GetPrimAtPath(DYNAMIC_OBSTACLE_RUNTIME_PRIM)
    collision_paths = []
    visible_collision_paths = []
    visible_geometry_paths = []
    visible_part_names = set()
    if root.IsValid():
        for prim in Usd.PrimRange(root, Usd.TraverseInstanceProxies()):
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                collision_paths.append(str(prim.GetPath()))
            if prim.GetTypeName() in (
                "Capsule",
                "Cone",
                "Cube",
                "Cylinder",
                "Mesh",
                "Sphere",
            ):
                imageable = UsdGeom.Imageable(prim)
                if imageable and str(imageable.ComputeVisibility()) != "invisible":
                    geometry_path = str(prim.GetPath())
                    visible_geometry_paths.append(geometry_path)
                    if prim.HasAPI(UsdPhysics.CollisionAPI):
                        visible_collision_paths.append(geometry_path)
                    visual_prefix = f"{DYNAMIC_OBSTACLE_RUNTIME_PRIM}/Visual/"
                    if geometry_path.startswith(visual_prefix):
                        visible_part_names.add(
                            geometry_path[len(visual_prefix):].split("/", 1)[0]
                        )
    rigid_api = UsdPhysics.RigidBodyAPI(root) if root.IsValid() else None
    kinematic_enabled = (
        bool(rigid_api.GetKinematicEnabledAttr().Get())
        if rigid_api is not None and rigid_api.GetKinematicEnabledAttr().IsValid()
        else False
    )
    lidar_targets = target_records(lidar)
    depth_targets = target_records(depth_camera)
    configured_dynamic_expr = str(dynamic_obstacle.cfg.prim_path)
    official_visual_root = stage.GetPrimAtPath(DYNAMIC_HUMAN_VISUAL_RUNTIME_PRIM)
    official_visual_geometry_paths = []
    official_visual_collision_paths = []
    if official_visual_root.IsValid():
        for prim in Usd.PrimRange(
            official_visual_root, Usd.TraverseInstanceProxies()
        ):
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                official_visual_collision_paths.append(str(prim.GetPath()))
            if prim.GetTypeName() == "Mesh":
                imageable = UsdGeom.Imageable(prim)
                if imageable and str(imageable.ComputeVisibility()) != "invisible":
                    official_visual_geometry_paths.append(str(prim.GetPath()))
    official_visual_rigid = (
        official_visual_root.IsValid()
        and official_visual_root.HasAPI(UsdPhysics.RigidBodyAPI)
    )

    def tracked_targets(records):
        return {
            row["prim_expr"]
            for row in records
            if row["track_mesh_transforms"]
        }

    expected_targets = {
        expand_isaac_env_regex_ns(expr) for expr in expected_target_exprs
    }
    if expected_targets == {
        expand_isaac_env_regex_ns(DYNAMIC_OBSTACLE_PRIM_EXPR)
    }:
        expected_targets.add(configured_dynamic_expr)
        lidar_tracking = bool(expected_targets & tracked_targets(lidar_targets))
        depth_tracking = bool(expected_targets & tracked_targets(depth_targets))
    else:
        lidar_tracking = expected_targets.issubset(tracked_targets(lidar_targets))
        depth_tracking = expected_targets.issubset(tracked_targets(depth_targets))
    human_expected = expected_targets == {
        expand_isaac_env_regex_ns(expr) for expr in _dynamic_human_part_exprs()
    }
    official_human_expected = expected_targets == {
        expand_isaac_env_regex_ns(expr)
        for expr in _official_human_sensor_exprs()
    }
    human_parts_complete = (
        set(DYNAMIC_HUMAN_PART_NAMES) == visible_part_names
        if human_expected
        else True
    )

    checks = {
        "runtime_root_exists": root.IsValid(),
        "rigid_object_initialized": bool(dynamic_obstacle.is_initialized),
        "kinematic_enabled": kinematic_enabled,
        "collision_enabled": bool(collision_paths),
        "physical_geometry_visibility": (
            not visible_geometry_paths
            if require_separate_official_visual
            else bool(visible_geometry_paths)
        ),
        "lidar_transform_tracking": lidar_tracking,
        "depth_transform_tracking": depth_tracking,
        "human_parts_complete": human_parts_complete,
        "human_collision_hidden": (
            not visible_collision_paths if human_expected else True
        ),
        "official_visual_root_exists": (
            official_visual_root.IsValid()
            if require_separate_official_visual
            else True
        ),
        "official_visual_geometry_visible": (
            bool(official_visual_geometry_paths)
            if require_separate_official_visual
            else True
        ),
        "official_visual_has_no_collision": (
            not official_visual_collision_paths
            if require_separate_official_visual
            else True
        ),
        "official_visual_has_no_rigid_body": (
            not official_visual_rigid
            if require_separate_official_visual
            else True
        ),
        "official_sensor_proxy_is_capsule": (
            official_human_expected
            if require_separate_official_visual
            else True
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "runtime_prim_path": DYNAMIC_OBSTACLE_RUNTIME_PRIM,
        "configured_prim_expr": configured_dynamic_expr,
        "collision_prim_paths": collision_paths,
        "visible_geometry_prim_paths": visible_geometry_paths,
        "visible_collision_prim_paths": visible_collision_paths,
        "visible_human_part_names": sorted(visible_part_names),
        "official_visual_runtime_prim": DYNAMIC_HUMAN_VISUAL_RUNTIME_PRIM,
        "official_visual_geometry_prim_paths": official_visual_geometry_paths,
        "official_visual_collision_prim_paths": official_visual_collision_paths,
        "expected_sensor_target_exprs": sorted(expected_target_exprs),
        "lidar_targets": lidar_targets,
        "depth_targets": depth_targets,
        "ground_truth_use": "evidence only; never planner input or robot steering",
    }


def _forest_preview_report(
    records,
    sink,
    command_stats,
    telemetry_stats,
    static_geometry_checks,
):
    checks = {
        "records_present": bool(records),
        "no_termination": bool(records) and not any(row["done"] for row in records),
        "finite_policy": bool(records) and all(row["finite"] for row in records),
        "command_visible": bool(records)
        and max(row["command_observation_max_error"] for row in records) <= 1.0e-5,
        "static_geometry_agreement": bool(static_geometry_checks)
        and bool(static_geometry_checks.get("passed")),
    }
    supported_fraction = (
        sum(row["contact_count"] >= 2 for row in records) / len(records)
        if records
        else 0.0
    )
    minimum_clearance = (
        min(row["base_clearance_m"] for row in records) if records else None
    )
    checks["supported_sample_fraction_value"] = supported_fraction
    checks["minimum_base_clearance_m_value"] = minimum_clearance
    checks["support"] = (
        bool(records)
        and supported_fraction >= 0.85
        and minimum_clearance is not None
        and minimum_clearance >= 0.15
    )
    for name, field, index in (
        ("forward", "root_lin_vel_b", 0),
        ("yaw", "root_ang_vel_b", 2),
    ):
        samples = [
            row[field][index]
            for row in records
            if row["schedule_segment"] == name
            and row["schedule_segment_elapsed_seconds"] >= 0.75
        ]
        mean = sum(samples) / len(samples) if samples else None
        checks[f"{name}_mean"] = mean
        checks[f"{name}_response"] = bool(samples) and mean > 0.03
    stop_samples = [
        row
        for row in records
        if row["schedule_segment"] == "stop_zero"
        and row["schedule_segment_elapsed_seconds"] >= 0.5
    ]
    checks["final_zero"] = bool(stop_samples) and all(
        row["applied_command"] == [0.0, 0.0, 0.0] for row in stop_samples
    )
    displacement = (
        math.dist(records[0]["root_pos_w"][:2], records[-1]["root_pos_w"][:2])
        if len(records) >= 2
        else 0.0
    )
    terrain_heights = [row["terrain_height_under_root_m"] for row in records]
    checks["root_xy_displacement_m_value"] = displacement
    checks["terrain_height_range_m_value"] = (
        max(terrain_heights) - min(terrain_heights) if terrain_heights else 0.0
    )
    checks["locomotion_displacement"] = displacement >= 0.25
    checks["telemetry_nonempty"] = (
        sink.get("sensor_frames", 0) > 0
        and sink.get("nonempty_sensor_frames", 0) == sink.get("sensor_frames", 0)
        and sink.get("status_frames", 0) > 0
    )
    required = (
        "records_present",
        "no_termination",
        "finite_policy",
        "command_visible",
        "static_geometry_agreement",
        "support",
        "forward_response",
        "yaw_response",
        "final_zero",
        "locomotion_displacement",
        "telemetry_nonempty",
    )
    return {
        "schema_version": 1,
        "status": "PASS" if all(bool(checks[name]) for name in required) else "FAIL",
        "claim": (
            "pinned V12 policy short locomotion preview on a native forest_gen "
            "terrain; not training, navigation, obstacle avoidance, or real-robot validation"
        ),
        "checks": checks,
        "static_geometry_checks": static_geometry_checks,
        "telemetry_sink": sink,
        "command_transport": command_stats.__dict__,
        "telemetry_transport": telemetry_stats.__dict__,
        "record_count": len(records),
    }


def _run(args) -> int:
    import gymnasium as gym
    import torch
    from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry

    vendored_package_dir = _activate_vendored_rsl_rl(args.vendored_rsl_rl)
    expected_policy_source = vendored_package_dir / "modules" / "actor_critic_moe_cts.py"
    from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper

    if args.source_commit != PINNED_SOURCE_COMMIT:
        raise AdapterFailure("source commit is not the pinned V12 fallback")
    checkpoint_sha256 = _sha256(args.checkpoint)
    if checkpoint_sha256 != PINNED_CHECKPOINT_SHA256:
        raise AdapterFailure("V12 fallback checkpoint hash mismatch")
    asset_identity = _asset_identity(args)
    if _sensor_rig_enabled(args):
        if asset_identity["asset_sha256"] != PINNED_SENSOR_RIG_ISAAC_SHA256:
            raise AdapterFailure("Isaac-safe Lite3 sensor-rig URDF hash mismatch")
        if (
            asset_identity["canonical_asset_sha256"]
            != PINNED_SENSOR_RIG_CANONICAL_SHA256
        ):
            raise AdapterFailure("canonical Lite3 sensor-rig URDF hash mismatch")
    if args.command_host != "127.0.0.1" or args.telemetry_host != "127.0.0.1":
        raise AdapterFailure("v1 endpoints must bind to 127.0.0.1")
    if (
        not math.isfinite(args.planner_floor_filter_max_z)
        or args.planner_floor_filter_max_z < 0.0
        or args.planner_floor_filter_max_z > 0.10
    ):
        raise AdapterFailure("planner floor filter must be within [0.0, 0.10] m")
    if args.video_path is not None and (
        args.video_fps <= 0 or args.video_frame_stride <= 0
    ):
        raise AdapterFailure("video fps and frame stride must be positive")
    if (
        not math.isfinite(args.connection_ready_timeout_seconds)
        or args.connection_ready_timeout_seconds <= 0.0
    ):
        raise AdapterFailure("connection ready timeout must be positive and finite")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if _forest_enabled(args):
        print("[forest-v4] run_enter", flush=True)
    try:
        forest_layout = _build_forest_layout(args)
    except BaseException as error:
        print(
            "[forest-v4] layout_exception "
            f"type={type(error).__name__} value={error!r}",
            flush=True,
        )
        raise
    if forest_layout is not None:
        print("[forest-v4] run_identity_start", flush=True)
    dynamic_spec = (
        _dynamic_obstacle_spec(args) if _dynamic_obstacle_enabled(args) else None
    )
    dynamic_route_static_checks = None
    if dynamic_spec is not None and forest_layout is not None:
        dynamic_route_static_checks = _dynamic_route_static_geometry_checks(
            forest_layout, dynamic_spec
        )
        _write_json(
            output_dir / "dynamic_route_static_precheck.json",
            dynamic_route_static_checks,
        )
        if not dynamic_route_static_checks["passed"]:
            nearest = dynamic_route_static_checks["nearest_static_object"]
            raise AdapterFailure(
                "dynamic route intersects or approaches static forest geometry: "
                f"{nearest['name']} clearance="
                f"{nearest['swept_capsule_clearance_m']:.3f} m"
            )
    dynamic_human_asset = None
    args.dynamic_human_usd_path = None
    args.dynamic_human_visual_usd_path = None
    office_routes = ()
    office_crowd_precheck = None
    office_human_visual_asset = None
    args.office_human_visual_usd_path = None
    if _office_crowd_enabled(args):
        route_payload = json.loads(args.office_route_path.read_text(encoding="utf-8"))
        office_routes = routes_from_preflight(
            route_payload,
            motion_mode=args.office_pedestrian_motion_mode,
            turnaround_hold_s=args.office_pedestrian_turnaround_hold_seconds,
        )
        office_crowd_precheck = pairwise_clearance_precheck(
            office_routes, args.duration_seconds
        )
        _write_json(output_dir / "office_crowd_pairwise_precheck.json", office_crowd_precheck)
        if not office_crowd_precheck["passed"]:
            raise AdapterFailure(
                "Office pedestrian routes fail pairwise clearance precheck: "
                f"{office_crowd_precheck}"
            )
        args.office_routes = office_routes
        args.office_human_visual_usd_path = output_dir / "office_human_visual.usda"
        office_human_visual_asset = _write_official_human_visual_usd(
            args.office_human_visual_usd_path,
            args.official_human_animation_cache,
        )
    if _forest_v8_official_enabled(args):
        args.dynamic_human_usd_path = output_dir / "official_human_proxy.usda"
        args.dynamic_human_visual_usd_path = (
            output_dir / "official_human_visual.usda"
        )
        physical_proxy = _write_official_human_wrapper_usd(
            args.dynamic_human_usd_path,
            dynamic_spec,
        )
        official_visual = _write_official_human_visual_usd(
            args.dynamic_human_visual_usd_path,
            args.official_human_animation_cache,
        )
        dynamic_human_asset = {
            "physical_and_sensor_proxy": physical_proxy,
            "official_visual": official_visual,
            "registration": {
                "time_xy_heading_owner": "dynamic obstacle schedule",
                "visual_vertical_datum": "official shoe sole",
                "physical_vertical_datum": "capsule centre",
                "visual_runtime_prim": DYNAMIC_HUMAN_VISUAL_RUNTIME_PRIM,
                "physical_runtime_prim": DYNAMIC_OBSTACLE_RUNTIME_PRIM,
            },
        }
    elif _forest_v8_enabled(args):
        args.dynamic_human_usd_path = output_dir / "procedural_human.usda"
        dynamic_human_asset = _write_procedural_human_usd(
            args.dynamic_human_usd_path,
            dynamic_spec,
        )
    qualification_schedule = (
        OFFICE_STATIC_SCHEDULE
        if _office_enabled(args)
        else FOREST_PREVIEW_SCHEDULE
        if _forest_preview_enabled(args)
        else None
    )
    sensor_rotation_wxyz = (
        math.cos(math.radians(args.sensor_pitch_degrees) / 2.0),
        0.0,
        math.sin(math.radians(args.sensor_pitch_degrees) / 2.0),
        0.0,
    )
    sensor_rig = _sensor_rig_enabled(args)
    lidar_translation = (0.0, 0.0, 0.0) if sensor_rig else args.sensor_translation
    lidar_rotation = (1.0, 0.0, 0.0, 0.0) if sensor_rig else sensor_rotation_wxyz
    raycast_targets = [GROUND_MESH_PRIM]
    if args.course == "single_box":
        raycast_targets.append(OBSTACLE_MESH_PRIM)
    elif forest_layout is not None:
        raycast_targets.extend(
            proxy["prim_path"] for proxy in forest_layout["proxies"]
        )
    if dynamic_spec is not None:
        raycast_targets.extend(
            _official_human_sensor_exprs()
            if _forest_v8_official_enabled(args)
            else _dynamic_human_part_exprs()
            if _forest_v8_enabled(args)
            else (DYNAMIC_OBSTACLE_PRIM_EXPR,)
        )
    if _office_enabled(args):
        start_x, start_y = args.office_start_xy
        camera_eye = (start_x + 5.5, start_y - 5.5, 4.5)
        camera_lookat = (start_x, start_y + 2.0, 0.45)
    elif forest_layout is None:
        camera_eye = VIDEO_CAMERA_EYE
        camera_lookat = VIDEO_CAMERA_LOOKAT
    elif _forest_navigation_enabled(args):
        spawn_x, spawn_y, spawn_z = forest_layout["spawn_world_xyz_m"]
        camera_eye = (spawn_x + 1.5, spawn_y - 7.5, spawn_z + 5.0)
        camera_lookat = (spawn_x + 3.0, spawn_y, spawn_z + 0.45)
    else:
        spawn_x, spawn_y, spawn_z = forest_layout["spawn_world_xyz_m"]
        camera_eye = (spawn_x - 6.0, spawn_y, spawn_z + 2.8)
        camera_lookat = (spawn_x + 1.5, spawn_y, spawn_z + 0.5)
    identity = {
        "schema_version": (
            7
            if _forest_v8_official_enabled(args)
            else 6
            if _forest_v8_enabled(args)
            else 5
            if _forest_v7_enabled(args)
            else 4
            if _forest_v6_enabled(args)
            else 3
            if forest_layout is not None
            else 2
            if sensor_rig
            else 1
        ),
        "candidate": _candidate_name(args),
        "source_commit": args.source_commit,
        "checkpoint_sha256": checkpoint_sha256,
        "robot_asset": asset_identity,
        "task": args.task,
        "mode": args.mode,
        "seed": args.seed,
        "device": args.device,
        "terrain": (
            "pinned forest_gen native heightmap"
            if forest_layout is not None
            else "official Isaac Sim 5.1 Office L0 physics wrapper"
            if _office_enabled(args)
            else "flat at difficulty 0.0"
        ),
        "course": {
            "name": args.course,
            "office_usd_path": (
                str(args.office_usd_path.resolve()) if _office_enabled(args) else None
            ),
            "office_usd_sha256": (
                args.office_usd_sha256 if _office_enabled(args) else None
            ),
            "office_route_path": (
                str(args.office_route_path.resolve()) if _office_enabled(args) else None
            ),
            "office_route_sha256": (
                args.office_route_sha256 if _office_enabled(args) else None
            ),
            "office_start_xy_m": (
                list(args.office_start_xy) if _office_enabled(args) else None
            ),
            "office_goal_xy_m": (
                list(args.office_goal_xy) if _office_enabled(args) else None
            ),
            "obstacle_center_m": (
                COURSE_OBSTACLE_CENTER if args.course == "single_box" else None
            ),
            "obstacle_size_m": (
                COURSE_OBSTACLE_SIZE if args.course == "single_box" else None
            ),
        },
        "command_limits": [args.max_vx, args.max_vy, args.max_wz],
        "cloud_profile": args.cloud_profile,
        "command_schedule": [
            {
                "name": segment.name,
                "duration_seconds": segment.duration_seconds,
                "command": segment.command,
                "connected": segment.connected,
            }
            for segment in (
                OFFICE_STATIC_SCHEDULE
                if _office_enabled(args)
                else FOREST_PREVIEW_SCHEDULE
                if _forest_preview_enabled(args)
                else ()
            )
        ],
        "watchdog_seconds": args.watchdog_seconds,
        "acceptance_config_sha256": (
            None if args.acceptance_config is None else _sha256(args.acceptance_config)
        ),
        "video": {
            "enabled": args.video_path is not None,
            "filename": None if args.video_path is None else args.video_path.name,
            "fps": args.video_fps,
            "frame_stride": args.video_frame_stride,
            "camera_eye_world": camera_eye,
            "camera_lookat_world": camera_lookat,
            "resolution": VIDEO_RESOLUTION,
        },
        "policy_observation_contract": {
            "dimension": POLICY_OBSERVATION_DIMENSION,
            "command_history_offset": COMMAND_HISTORY_OFFSET,
            "command_history_length": COMMAND_HISTORY_LENGTH,
        },
        "inference_policy": {
            "class": "ActorCriticMoECTS",
            "loader": "direct policy-only strict state_dict load",
            "vendored_package": "source/rsl_rl/rsl_rl",
            "source": "modules/actor_critic_moe_cts.py",
            "source_sha256": _sha256(expected_policy_source),
        },
        "sensor": {
            "backend": (
                "IsaacLab MultiMeshRayCaster with ordered Livox MID-360 pattern"
                if _official_mid360_enabled(args)
                else "IsaacLab MultiMeshRayCaster LidarPatternCfg"
            ),
            "truth_pose": True,
            "declared_device": (
                "Livox MID-360 source-backed geometric snapshot"
                if _official_mid360_enabled(args)
                else "MID-360-like uniform geometric ray model"
                if sensor_rig
                else None
            ),
            "parent_frame": MID360_FRAME if sensor_rig else "TORSO",
            "translation_m": lidar_translation,
            "rotation_wxyz": lidar_rotation,
            "pattern_mode": args.lidar_pattern_mode,
            "pattern": (
                args.mid360_pattern_table.identity()
                if _official_mid360_enabled(args)
                else None
            ),
            "channels": None if _official_mid360_enabled(args) else args.lidar_channels,
            "vertical_fov_degrees": (
                None
                if _official_mid360_enabled(args)
                else [args.lidar_vertical_min, args.lidar_vertical_max]
            ),
            "horizontal_resolution_degrees": (
                None
                if _official_mid360_enabled(args)
                else args.lidar_horizontal_resolution
            ),
            "rays_per_scan": (
                args.mid360_pattern_table.points_per_scan
                if _official_mid360_enabled(args)
                else args.lidar_channels
                * int(round(360.0 / args.lidar_horizontal_resolution))
            ),
            "minimum_range_m": args.lidar_min_range,
            "maximum_range_m": args.lidar_max_range,
            "period_seconds": args.sensor_period,
            "pose_and_frame_stamp_alignment": (
                "public RayCaster reset plus same-step zero-dt update before publish"
                if _official_mid360_enabled(args)
                else "legacy sensor-period scheduling"
            ),
            "planner_floor_filter": {
                "frame": "world",
                "enabled": forest_layout is None and not _dual_cloud_geometry_enabled(args),
                "remove_hits_at_or_below_z_m": (
                    None
                    if forest_layout is not None or _dual_cloud_geometry_enabled(args)
                    else args.planner_floor_filter_max_z
                ),
                "reason": (
                    "replaced by the geometry-only local terrain filter for dual-cloud telemetry"
                    if _dual_cloud_geometry_enabled(args)
                    else "replaced by the geometry-only local terrain filter in V5"
                    if _forest_navigation_enabled(args)
                    else "disabled for the terrain-only V4 preview; SCAN is not connected"
                    if forest_layout is not None
                    else "SCAN occupancy input excludes the traversable flat floor"
                ),
            },
            "forest_geometry_filter": {
                "enabled": _forest_navigation_enabled(args) or _dual_cloud_geometry_enabled(args),
                "inputs": ["rendered_hit_xyz_world", "sensor_position_world"],
                "forbidden_inputs": [
                    "terrain_height_function",
                    "scene_prim_id",
                    "proxy_bounds",
                    "obstacle_label",
                ],
                "cell_size_m": (
                    args.terrain_filter_cell_size
                    if _forest_navigation_enabled(args) or _dual_cloud_geometry_enabled(args)
                    else None
                ),
                "height_threshold_m": (
                    args.terrain_filter_height_threshold
                    if _forest_navigation_enabled(args) or _dual_cloud_geometry_enabled(args)
                    else None
                ),
                "neighbor_cells": (
                    args.terrain_filter_neighbor_cells
                    if _forest_navigation_enabled(args) or _dual_cloud_geometry_enabled(args)
                    else None
                ),
                "minimum_neighbor_cells": (
                    args.terrain_filter_minimum_neighbor_cells
                    if _forest_navigation_enabled(args) or _dual_cloud_geometry_enabled(args)
                    else None
                ),
            },
            "raycast_targets": raycast_targets,
            "self_occlusion_links": (
                list(MID360_SELF_OCCLUSION_LINKS) if sensor_rig else []
            ),
            "self_occlusion_treatment": (
                "Ray-cast against moving rig geometry; discard a blocking self hit "
                "inside the declared minimum range without allowing the ray to pass "
                "through to environment geometry."
                if sensor_rig
                else "not modelled by the legacy V12 sensor"
            ),
            "obstacle_return_classification": (
                "finite hit inside a declared visible physics-and-sensor proxy bound"
                if forest_layout is not None
                else "finite hit above floor filter inside the only non-ground mesh bounds"
            ),
        },
    }
    if dynamic_spec is not None:
        identity["dynamic_obstacle"] = {
            "name": dynamic_spec.name,
            "prim_expr": DYNAMIC_OBSTACLE_PRIM_EXPR,
            "runtime_prim_path": DYNAMIC_OBSTACLE_RUNTIME_PRIM,
            "shape": (
                "procedural_humanoid"
                if _forest_v8_enabled(args)
                else "official_skinned_human_plus_capsule"
                if _forest_v8_official_enabled(args)
                else "cylinder"
            ),
            "collision_shape": (
                "hidden_capsule"
                if _forest_v8_any_enabled(args)
                else "visible_cylinder"
            ),
            "start_xy_m": dynamic_spec.start_xy,
            "end_xy_m": dynamic_spec.end_xy,
            "wait_seconds": dynamic_spec.wait_seconds,
            "speed_mps": dynamic_spec.speed_mps,
            "crossing_duration_seconds": dynamic_spec.crossing_duration_seconds,
            "hold_fraction": dynamic_spec.hold_fraction,
            "hold_seconds": dynamic_spec.hold_seconds,
            "schedule_trigger": _dynamic_schedule_trigger_identity(
                args.dynamic_obstacle_schedule_trigger
            ),
            "schedule_trigger_mode": args.dynamic_obstacle_schedule_trigger,
            "radius_m": dynamic_spec.radius_m,
            "height_m": dynamic_spec.height_m,
            "terrain_clearance_m": dynamic_spec.terrain_clearance_m,
            "static_route_precheck": dynamic_route_static_checks,
            "rigid_body_mode": "kinematic obstacle with scheduled pose writes",
            "collision_enabled": True,
            "lidar_transform_tracking": True,
            "depth_transform_tracking": True,
            "colour_rgb": (
                list(DYNAMIC_HUMAN_COLOR_RGB)
                if _forest_v8_enabled(args)
                else None
                if _forest_v8_official_enabled(args)
                else [1.0, 0.24, 0.02]
            ),
            "human_asset": dynamic_human_asset,
            "visible_part_names": (
                list(DYNAMIC_HUMAN_PART_NAMES)
                if _forest_v8_enabled(args)
                else [DYNAMIC_HUMAN_VISUAL_RUNTIME_PRIM]
                if _forest_v8_official_enabled(args)
                else []
            ),
            "sensor_target_exprs": (
                list(_dynamic_human_part_exprs())
                if _forest_v8_enabled(args)
                else list(_official_human_sensor_exprs())
                if _forest_v8_official_enabled(args)
                else [DYNAMIC_OBSTACLE_PRIM_EXPR]
            ),
            "gait": (
                {
                    "enabled_phase": "crossing",
                    "neutral_phases": ["waiting", "holding", "parked"],
                    "cadence_hz": DYNAMIC_HUMAN_GAIT_CADENCE_HZ,
                    "maximum_swing_radians": DYNAMIC_HUMAN_GAIT_MAX_SWING_RADIANS,
                    "part_local_visual_transforms_only": True,
                }
                if _forest_v8_enabled(args)
                else {
                    "status": "official_biped_retarget_cache_replay",
                    "source": (
                        "NVIDIA Isaac Sim 5.1 Biped AnimationGraph output after "
                        "ControlRig retargeting to male_adult_police_04"
                    ),
                    "biped_url": OFFICIAL_HUMAN_BIPED_URL,
                    "retarget_cache": dynamic_human_asset["official_visual"][
                        "biped_retarget_cache"
                    ],
                    "animation_mode": args.official_human_animation_mode,
                    "phase_to_clip": (
                        "all phases -> walk"
                        if args.official_human_animation_mode == "continuous_walk"
                        else "crossing -> walk; waiting/holding/parked -> idle"
                    ),
                    "local_procedural_gait": False,
                    "direct_gpu_animation_graph_used": False,
                    "claim": (
                        "official Biped graph output replayed on the exact 101-joint "
                        "official character; runtime gait still requires rendered "
                        "visual verification"
                    ),
                }
                if _forest_v8_official_enabled(args)
                else None
            ),
            "planner_input": "rendered sensor hits only",
            "ground_truth_use": (
                "evidence classification and synchronized clearance only; forbidden "
                "from point injection, filtering, command generation, and robot steering"
            ),
            "claim_boundary": (
                "official Isaac character, Biped-retarget cache replay, and co-moving "
                "physical/sensor proxy integrated for qualification; human appearance and full "
                "closed-loop avoidance remain unvalidated until runtime and human review"
                if _forest_v8_official_enabled(args)
                else "single deterministic person-shaped crossing with reactive "
                "occupancy replanning; no semantic person detection, social navigation, "
                "obstacle-velocity prediction, or intention model"
                if _forest_v8_enabled(args)
                else "single deterministic crossing with reactive occupancy replanning; "
                "no obstacle-velocity prediction or intention model"
            ),
        }
    if forest_layout is not None:
        identity["forest_scene"] = forest_layout["identity"]
    if _office_crowd_enabled(args):
        identity["office_crowd"] = {
            "pedestrian_count": len(office_routes),
            "pedestrian_motion_mode": args.office_pedestrian_motion_mode,
            "pedestrian_turnaround_hold_s": (
                args.office_pedestrian_turnaround_hold_seconds
            ),
            "official_human_animation_mode": args.official_human_animation_mode,
            "routes": [
                {
                    "name": route.name,
                    "start_xy_m": list(route.start_xy_m),
                    "end_xy_m": list(route.end_xy_m),
                    "speed_mps": route.speed_mps,
                    "start_delay_s": route.start_delay_s,
                    "radius_m": route.radius_m,
                    "motion_mode": route.motion_mode,
                    "turnaround_hold_s": route.turnaround_hold_s,
                }
                for route in office_routes
            ],
            "pairwise_precheck": office_crowd_precheck,
            "official_visual_asset": office_human_visual_asset,
            "physical_proxy": {
                "shape": "capsule",
                "radius_m": OFFICIAL_HUMAN_CAPSULE_RADIUS_M,
                "height_m": OFFICIAL_HUMAN_CAPSULE_HEIGHT_M,
                "kinematic": True,
                "render_visible": False,
            },
            "planner_input": "rendered simulated sensor hits only",
            "truth_use": "evaluation and synchronized clearance only",
        }
    if sensor_rig:
        identity["depth_camera"] = {
            "backend": "IsaacLab MultiMeshRayCasterCameraCfg",
            "declared_device": "D435i-like provisional ray-cast depth",
            "parent_frame": D435I_FRAME,
            "translation_m": [0.0, 0.0, 0.0],
            "rotation_wxyz": [1.0, 0.0, 0.0, 0.0],
            "orientation_convention": "ros optical frame",
            "width": args.depth_width,
            "height": args.depth_height,
            "focal_length": args.depth_focal_length,
            "horizontal_aperture": args.depth_horizontal_aperture,
            "minimum_range_m": args.depth_min_range,
            "maximum_range_m": args.depth_max_range,
            "period_seconds": args.depth_period,
            "raycast_targets": raycast_targets,
            "self_occlusion_links": list(D435I_SELF_OCCLUSION_LINKS),
            "self_occlusion_treatment": (
                "Ray-cast against moving rig geometry; replace blocking near-self "
                "pixels with the maximum-depth invalid sentinel."
            ),
            "intrinsics_status": (
                "provisional; no live D435i depth CameraInfo is available. The "
                "recorded color CameraInfo is intentionally not reused."
            ),
            "navigation_use": (
                "generated and logged concurrently; not fused into SCAN in this preview"
            ),
        }
    if _office_review_presentation_enabled(args):
        from .office_review_presentation import (
            PRESERVED_FIRST_VIEW_CAMERA_MODEL,
            REVIEW_MATERIAL_LIMB_RGB,
            REVIEW_MATERIAL_TORSO_RGB,
            SIDE_VIEW_CAMERA_MODEL,
            frozen_quality_profile,
            review_film_iso,
            validate_overview_camera_config,
            validate_side_camera_config,
        )
        validated_cam = validate_side_camera_config({
            "side": args.office_review_camera_side,
            "lateral_distance_m": args.office_review_camera_lateral_distance,
            "trailing_bias_m": args.office_review_camera_trailing_bias,
            "height_m": args.office_review_camera_height,
            "focal_length_mm": args.office_review_camera_focal_length_mm,
            "look_ahead_m": args.office_review_camera_look_ahead,
            "look_height_offset_m": args.office_review_camera_look_height_offset,
            "smoothing_rate": args.office_review_camera_smoothing_rate,
            "max_eye_speed_mps": args.office_review_camera_max_eye_speed,
            "max_target_speed_mps": args.office_review_camera_max_target_speed,
        })
        validated_overview = validate_overview_camera_config({
            "distance_m": args.office_review_overview_distance,
            "azimuth_offset_deg": args.office_review_overview_azimuth_offset_deg,
            "height_m": args.office_review_overview_height,
            "look_ahead_m": args.office_review_overview_look_ahead,
            "look_height_offset_m": args.office_review_overview_look_height_offset,
            "smoothing_rate": args.office_review_overview_smoothing_rate,
            "max_eye_speed_mps": args.office_review_overview_max_eye_speed,
            "max_target_speed_mps": args.office_review_overview_max_target_speed,
        })
        quality_profile = frozen_quality_profile()
        quality_profile["fps"] = float(args.video_fps)
        quality_profile["exposure"] = float(args.office_review_exposure)
        quality_profile["renderer_film_iso"] = review_film_iso(
            args.office_review_exposure,
            quality_profile["renderer_base_film_iso"],
        )
        pres_module_path = Path(__file__).parent / "office_review_presentation.py"
        identity["office_review_presentation"] = {
            "enabled": True,
            "first_view_model": PRESERVED_FIRST_VIEW_CAMERA_MODEL,
            "first_view": {
                "camera_model": PRESERVED_FIRST_VIEW_CAMERA_MODEL,
                "frame": "world_root_relative_chase",
                "render_modality": "simulated_rgb_from_preserved_chase_pose",
                "eye_equation": ["rx-2.2*cos(yaw)", "ry-2.2*sin(yaw)", "clamp(rz+1.8,1.8,2.4)"],
                "target_equation": ["rx+0.6*cos(yaw)", "ry+0.6*sin(yaw)", "rz+0.16"],
                "claim_boundary": (
                    "Exact preserved Office chase-camera geometry called first view "
                    "by Dr Sun; not a D435i or robot-mounted optical view"
                ),
            },
            "side_view_model": SIDE_VIEW_CAMERA_MODEL,
            "camera_render_cutaway": {
                "scope": "all_review_camera_views_render_only",
                "selection_rule": (
                    "L0 per-floor view: hide ceiling/light actors, non-L0 floor "
                    "actors, and actor roots wholly above z=2.85 m"
                ),
                "restore_before_next_view_and_physics_step": True,
                "navigation_sensor_and_planner_inputs_unchanged": True,
            },
            "side_camera_config": validated_cam,
            "overview_camera_config": validated_overview,
            "quality_profile": quality_profile,
            "lighting": {
                "profile": args.office_review_lighting_profile,
                "dome_light_intensity": args.office_review_dome_light_intensity,
                "dome_light_color_rgb": [1.0, 0.96, 0.90],
                "exposure": args.office_review_exposure,
                "tone_mapping": quality_profile["tone_mapping"],
                "motion_blur": quality_profile["motion_blur"],
            },
            "output_paths": {
                "first_video": str(args.video_path),
                "side_video": str(_office_review_side_video_path(args)),
                "overview_video": str(_office_review_overview_video_path(args)),
                "camera_trace": str(args.office_review_camera_trace_path),
                "material_audit": str(args.office_review_material_audit_path),
                "dashboard_video": str(args.office_review_dashboard_video_path),
                "dashboard_metadata": str(args.office_review_dashboard_metadata_path),
                "validation_report": str(args.office_review_validation_report_path),
            },
            "material_override": {
                "applied": True,
                "torso_linear_rgb": list(REVIEW_MATERIAL_TORSO_RGB),
                "limb_linear_rgb": list(REVIEW_MATERIAL_LIMB_RGB),
                "opacity": 1.0,
                "emission": 0.0,
            },
            "source_hashes": {
                "runner": _sha256(Path(__file__)),
                "presentation_module": _sha256(pres_module_path) if pres_module_path.is_file() else None,
                "launcher": _sha256(args.office_review_launcher_path),
                "effective_input": _sha256(args.office_review_effective_input_path),
                "acceptance_config": _sha256(args.acceptance_config),
            },
        }
    config_sha256 = canonical_config_sha256(identity)
    identity["config_sha256"] = config_sha256.hex()
    _write_json(output_dir / "run_identity.json", identity)

    limits = CommandLimits(args.max_vx, args.max_vy, args.max_wz)
    state = LatestCommandState(
        limits,
        timeout_ns=int(args.watchdog_seconds * 1.0e9),
        max_source_age_ns=int(args.watchdog_seconds * 1.0e9),
        max_future_skew_ns=25_000_000,
    )
    command_server = CommandReceiverServer(state, args.command_host, args.command_port)
    telemetry_server = TelemetryPublisherServer(args.telemetry_host, args.telemetry_port)
    sender = None
    sink = None
    if args.mode in ("qualification", "sensor_qualification"):
        sender = _QualificationSender(
            args.command_port,
            50.0,
            limits,
            schedule=(
                qualification_schedule
                if qualification_schedule is not None
                else DEFAULT_QUALIFICATION_SCHEDULE
            ),
        )
        sink = _TelemetrySink(args.telemetry_port, config_sha256)

    raw_env = None
    wrapped_env = None
    runtime_error = None
    records = []
    sensor_records = []
    mid360_scan_index = 0
    depth_records = []
    best_depth_frame = None
    best_depth_metadata = None
    telemetry_sequence = 0
    dropped_frames = 0
    video_writer = None
    video_frame_count = 0
    video_camera_fallback_sim_times = []
    third_person_video_writer = None
    overview_video_writer = None
    review_viewport_camera = None
    review_default_focal_length_mm = None
    review_default_horizontal_aperture_mm = None
    camera_trace_handle = None
    camera_trace_rows = []
    third_person_eye = None
    third_person_target = None
    overview_eye = None
    overview_target = None
    runtime_rates = {}
    static_forest_geometry_checks = None
    dynamic_obstacle_geometry_checks = None
    official_animation_player = None
    official_visual_pose_evidence = None
    office_pedestrians = []
    office_animation_players = []
    office_visual_pose_evidence = []
    review_capture_profile = None
    review_side_camera_cfg = None
    review_overview_camera_cfg = None
    review_side_desired_pose = None
    review_overview_desired_pose = None
    review_smooth_pose_bounded = None
    review_first_view_pose = None
    review_camera_trace_row = None
    review_state_snapshot_identity = None
    review_writer_type = None
    review_actor_root_paths = None
    review_floor_root_paths = None
    review_cutaway_root_paths = None
    review_cutaway_imageables = []
    review_cutaway_audit = None
    review_renderer_runtime_settings = None
    review_render_frame = None
    if _office_review_presentation_enabled(args):
        from .office_review_presentation import (
            DirectH264Writer,
            camera_trace_row,
            frozen_quality_profile,
            office_actor_root_paths,
            office_floor_root_paths,
            office_l0_cutaway_root_paths,
            overview_desired_pose,
            preserved_first_view_pose,
            render_temporally_settled_frame,
            review_film_iso,
            side_follow_desired_pose,
            smooth_pose_bounded,
            state_snapshot_identity,
            validate_overview_camera_config,
            validate_side_camera_config,
        )
        review_capture_profile = frozen_quality_profile()
        review_capture_profile["fps"] = float(args.video_fps)
        review_capture_profile["exposure"] = float(args.office_review_exposure)
        review_capture_profile["renderer_film_iso"] = review_film_iso(
            args.office_review_exposure,
            review_capture_profile["renderer_base_film_iso"],
        )
        review_side_camera_cfg = validate_side_camera_config({
            "side": args.office_review_camera_side,
            "lateral_distance_m": args.office_review_camera_lateral_distance,
            "trailing_bias_m": args.office_review_camera_trailing_bias,
            "height_m": args.office_review_camera_height,
            "focal_length_mm": args.office_review_camera_focal_length_mm,
            "look_ahead_m": args.office_review_camera_look_ahead,
            "look_height_offset_m": args.office_review_camera_look_height_offset,
            "smoothing_rate": args.office_review_camera_smoothing_rate,
            "max_eye_speed_mps": args.office_review_camera_max_eye_speed,
            "max_target_speed_mps": args.office_review_camera_max_target_speed,
        })
        review_overview_camera_cfg = validate_overview_camera_config({
            "distance_m": args.office_review_overview_distance,
            "azimuth_offset_deg": args.office_review_overview_azimuth_offset_deg,
            "height_m": args.office_review_overview_height,
            "look_ahead_m": args.office_review_overview_look_ahead,
            "look_height_offset_m": args.office_review_overview_look_height_offset,
            "smoothing_rate": args.office_review_overview_smoothing_rate,
            "max_eye_speed_mps": args.office_review_overview_max_eye_speed,
            "max_target_speed_mps": args.office_review_overview_max_target_speed,
        })
        review_writer_type = DirectH264Writer
        review_actor_root_paths = office_actor_root_paths
        review_floor_root_paths = office_floor_root_paths
        review_cutaway_root_paths = office_l0_cutaway_root_paths
        review_camera_trace_row = camera_trace_row
        review_side_desired_pose = side_follow_desired_pose
        review_overview_desired_pose = overview_desired_pose
        review_smooth_pose_bounded = smooth_pose_bounded
        review_first_view_pose = preserved_first_view_pose
        review_state_snapshot_identity = state_snapshot_identity
    try:
        __import__("robot_lab.tasks")
        env_cfg = load_cfg_from_registry(args.task, "env_cfg_entry_point")
        agent_cfg = load_cfg_from_registry(args.task, "rsl_rl_cfg_entry_point")
        v12_task_contract = _capture_v12_task_contract(env_cfg)
        _configure_environment(env_cfg, args, forest_layout)
        agent_cfg.seed = args.seed
        agent_cfg.device = args.device
        raw_env = gym.make(
            args.task,
            cfg=env_cfg,
            render_mode="rgb_array" if args.video_path is not None else None,
        )
        base_env = raw_env.unwrapped
        if _office_review_presentation_enabled(args):
            import carb

            renderer_settings = carb.settings.get_settings()
            renderer_settings.set(
                "/rtx/post/aa/op",
                int(review_capture_profile["renderer_anti_aliasing_mode"]),
            )
            renderer_settings.set(
                "/rtx-transient/dlssg/enabled",
                bool(review_capture_profile["renderer_dlss_frame_generation"]),
            )
            renderer_settings.set(
                "/rtx/post/histogram/enabled",
                bool(review_capture_profile["renderer_auto_exposure"]),
            )
            renderer_settings.set(
                "/rtx/post/tonemap/filmIso",
                float(review_capture_profile["renderer_film_iso"]),
            )
            review_renderer_runtime_settings = {
                "anti_aliasing_path": "/rtx/post/aa/op",
                "anti_aliasing_mode": int(
                    renderer_settings.get("/rtx/post/aa/op")
                ),
                "dlss_frame_generation_path": "/rtx-transient/dlssg/enabled",
                "dlss_frame_generation": bool(
                    renderer_settings.get("/rtx-transient/dlssg/enabled")
                ),
                "auto_exposure_path": "/rtx/post/histogram/enabled",
                "auto_exposure": bool(
                    renderer_settings.get("/rtx/post/histogram/enabled")
                ),
                "film_iso_path": "/rtx/post/tonemap/filmIso",
                "film_iso": float(
                    renderer_settings.get("/rtx/post/tonemap/filmIso")
                ),
                "settle_render_count": int(
                    review_capture_profile["renderer_settle_render_count"]
                ),
            }
            if (
                review_renderer_runtime_settings["anti_aliasing_mode"]
                != int(review_capture_profile["renderer_anti_aliasing_mode"])
                or review_renderer_runtime_settings["dlss_frame_generation"]
                is not bool(
                    review_capture_profile["renderer_dlss_frame_generation"]
                )
                or review_renderer_runtime_settings["auto_exposure"]
                is not bool(review_capture_profile["renderer_auto_exposure"])
                or abs(
                    review_renderer_runtime_settings["film_iso"]
                    - float(review_capture_profile["renderer_film_iso"])
                )
                > 1.0e-4
            ):
                raise AdapterFailure(
                    "Office review renderer quality settings did not apply"
                )
        runtime_rates = {
            "physics_hz": 1.0 / float(base_env.physics_dt),
            "policy_hz": 1.0 / float(base_env.step_dt),
            "sensor_hz": 1.0 / args.sensor_period,
        }
        wrapped_env = RslRlVecEnvWrapper(raw_env, clip_actions=agent_cfg.clip_actions)
        policy, policy_state, observation, policy_source = _load_inference_policy(
            wrapped_env, agent_cfg, args.checkpoint, agent_cfg.device
        )
        if policy_source != expected_policy_source:
            raise AdapterFailure(
                f"ActorCriticMoECTS resolved outside the pinned source: {policy_source}"
            )
        robot = base_env.scene["robot"]
        dynamic_obstacle = (
            base_env.scene["dynamic_obstacle"]
            if dynamic_spec is not None
            else None
        )
        if _office_crowd_enabled(args):
            office_pedestrians = [
                base_env.scene[f"office_pedestrian_{index}"]
                for index in range(len(office_routes))
            ]
        lidar = base_env.scene.sensors["navigation_lidar"]
        depth_camera = (
            base_env.scene.sensors["navigation_depth_camera"]
            if sensor_rig
            else None
        )
        contact = base_env.scene.sensors["contact_forces"]
        contact_foot_ids, contact_names = contact.find_bodies(
            ["FL_FOOT", "FR_FOOT", "HL_FOOT", "HR_FOOT"], preserve_order=True
        )
        if len(contact_foot_ids) != 4:
            raise AdapterFailure(f"V12 contact foot binding mismatch: {contact_names}")
        missing_rig_links = []
        if sensor_rig:
            missing_rig_links = [
                name for name in SENSOR_RIG_REQUIRED_LINKS if name not in robot.body_names
            ]
            if missing_rig_links:
                raise AdapterFailure(
                    f"sensor-rig links absent after Isaac import: {missing_rig_links}"
                )
        default_joint_position = {
            name: float(robot.data.default_joint_pos[0, index].item())
            for index, name in enumerate(robot.joint_names)
        }
        for name, position in default_joint_position.items():
            expected = 0.0 if "HipX" in name else (-0.8 if "HipY" in name else 1.6)
            if abs(position - expected) > 1.0e-6:
                raise AdapterFailure(
                    f"V12 runtime default joint pose changed for {name}: {position}"
                )
        runtime_mass_by_link = {
            name: float(robot.data.default_mass[0, index].item())
            for index, name in enumerate(robot.body_names)
        }
        runtime_inertia_by_link = {
            name: _tensor_list(robot.data.default_inertia[0, index])
            for index, name in enumerate(robot.body_names)
        }
        imported_prim_paths = []
        imported_collision_prim_paths = []
        imported_joint_prim_paths = []
        imported_fixed_joint_prim_paths = []
        imported_movable_joint_prim_paths = []
        imported_geometry_prim_records = []
        if sensor_rig:
            import omni.usd
            from pxr import Usd, UsdGeom, UsdPhysics

            stage = omni.usd.get_context().get_stage()
            robot_prim_prefix = "/World/envs/env_0/Robot"
            robot_prim = stage.GetPrimAtPath(robot_prim_prefix)
            if not robot_prim.IsValid():
                raise AdapterFailure("imported sensor-rig robot prim is missing")
            for prim in Usd.PrimRange(robot_prim, Usd.TraverseInstanceProxies()):
                prim_path = str(prim.GetPath())
                imported_prim_paths.append(prim_path)
                if prim.HasAPI(UsdPhysics.CollisionAPI):
                    imported_collision_prim_paths.append(prim_path)
                if prim.GetTypeName() in (
                    "Capsule",
                    "Cone",
                    "Cube",
                    "Cylinder",
                    "Mesh",
                    "Sphere",
                ):
                    imported_geometry_prim_records.append(
                        {
                            "path": prim_path,
                            "type": prim.GetTypeName(),
                            "applied_schemas": list(prim.GetAppliedSchemas()),
                        }
                    )
                if prim.IsA(UsdPhysics.Joint):
                    imported_joint_prim_paths.append(prim_path)
                    if prim.IsA(UsdPhysics.FixedJoint):
                        imported_fixed_joint_prim_paths.append(prim_path)
                    else:
                        imported_movable_joint_prim_paths.append(prim_path)
            expected_runtime_mass = asset_identity["isaac_urdf_contract"][
                "total_declared_mass_kg"
            ]
            observed_runtime_mass = sum(runtime_mass_by_link.values())
            if len(robot.body_names) != 24:
                raise AdapterFailure(
                    f"sensor-rig runtime body count is {len(robot.body_names)}, not 24"
                )
            if len(imported_joint_prim_paths) != 23:
                raise AdapterFailure(
                    "sensor-rig runtime USD joint count is "
                    f"{len(imported_joint_prim_paths)}, not 23"
                )
            if len(imported_fixed_joint_prim_paths) != 11:
                raise AdapterFailure(
                    "sensor-rig runtime USD fixed-joint count is "
                    f"{len(imported_fixed_joint_prim_paths)}, not 11"
                )
            if len(imported_movable_joint_prim_paths) != 12:
                raise AdapterFailure(
                    "sensor-rig runtime USD movable-joint count is "
                    f"{len(imported_movable_joint_prim_paths)}, not 12"
                )
            if len(imported_collision_prim_paths) != 29:
                raise AdapterFailure(
                    "sensor-rig runtime collision-prim count is "
                    f"{len(imported_collision_prim_paths)}, not 29"
                )
            if abs(observed_runtime_mass - expected_runtime_mass) > 1.0e-5:
                raise AdapterFailure(
                    "sensor-rig runtime mass differs from the Isaac URDF: "
                    f"{observed_runtime_mass} != {expected_runtime_mass}"
                )
            for frame_name in (MID360_FRAME, D435I_FRAME):
                if abs(runtime_mass_by_link[frame_name] - 1.0e-6) > 1.0e-8:
                    raise AdapterFailure(
                        f"{frame_name} received an unexpected runtime mass: "
                        f"{runtime_mass_by_link[frame_name]}"
                    )
            if _office_review_presentation_enabled(args) or args.office_review_material:
                from .office_review_presentation import apply_office_review_material_usd
                referenced_mesh_hashes = {
                    name: record["sha256"]
                    for name, record in asset_identity["isaac_urdf_contract"]["referenced_meshes"].items()
                }
                apply_office_review_material_usd(
                    stage=stage,
                    robot_prim_path=robot_prim_prefix,
                    audit_output_path=args.office_review_material_audit_path,
                    robot_asset_sha256=_sha256(args.robot_asset) if args.robot_asset else "",
                    referenced_mesh_sha256=referenced_mesh_hashes,
                )
            if _office_review_presentation_enabled(args):
                stage_paths = [str(prim.GetPath()) for prim in stage.Traverse()]
                ceiling_cutaway_paths = review_cutaway_root_paths(stage_paths)
                floor_paths = review_floor_root_paths(stage_paths)
                known_actor_roots = sorted(
                    set(ceiling_cutaway_paths) | set(floor_paths)
                )
                actor_paths = review_actor_root_paths(stage_paths, known_actor_roots)
                if not ceiling_cutaway_paths or not floor_paths or not actor_paths:
                    raise AdapterFailure(
                        "Office L0 high-oblique review could not inventory floor actors"
                    )
                bbox_cache = UsdGeom.BBoxCache(
                    Usd.TimeCode.Default(),
                    [
                        UsdGeom.Tokens.default_,
                        UsdGeom.Tokens.render,
                        UsdGeom.Tokens.proxy,
                    ],
                    useExtentsHint=True,
                )
                upper_actor_paths = []
                non_l0_floor_paths = []
                for actor_path in actor_paths:
                    actor_prim = stage.GetPrimAtPath(actor_path)
                    if not actor_prim.IsValid():
                        continue
                    aligned = bbox_cache.ComputeWorldBound(
                        actor_prim
                    ).ComputeAlignedRange()
                    minimum = aligned.GetMin()
                    maximum = aligned.GetMax()
                    bounds = [float(value) for value in (*minimum, *maximum)]
                    if not all(math.isfinite(value) for value in bounds):
                        continue
                    z_min = bounds[2]
                    z_max = bounds[5]
                    actor_name = actor_path.rsplit("/", 1)[-1]
                    if actor_name.startswith(("SM_Floor_", "SM_Floor")):
                        floor_center_z = 0.5 * (z_min + z_max)
                        if abs(floor_center_z) > 0.20:
                            non_l0_floor_paths.append(actor_path)
                    elif z_min > 2.85:
                        upper_actor_paths.append(actor_path)
                cutaway_paths = sorted(
                    set(ceiling_cutaway_paths)
                    | set(non_l0_floor_paths)
                    | set(upper_actor_paths)
                )
                for cutaway_path in cutaway_paths:
                    cutaway_prim = stage.GetPrimAtPath(cutaway_path)
                    if not cutaway_prim.IsValid() or not cutaway_prim.IsA(
                        UsdGeom.Imageable
                    ):
                        raise AdapterFailure(
                            f"Office cutaway root is not imageable: {cutaway_path}"
                        )
                    imageable = UsdGeom.Imageable(cutaway_prim)
                    review_cutaway_imageables.append(
                        (cutaway_path, imageable, imageable.GetVisibilityAttr().Get())
                    )
                cutaway_paths_sha256 = hashlib.sha256(
                    json.dumps(
                        cutaway_paths, sort_keys=True, separators=(",", ":")
                    ).encode("utf-8")
                ).hexdigest()
                review_cutaway_audit = {
                    "mode": "office_l0_per_floor_global_cutaway_v2",
                    "scope": "all_review_camera_views_render_only",
                    "prim_count": len(cutaway_paths),
                    "ceiling_and_light_prim_count": len(ceiling_cutaway_paths),
                    "non_l0_floor_prim_count": len(non_l0_floor_paths),
                    "upper_actor_prim_count": len(upper_actor_paths),
                    "upper_actor_min_z_threshold_m": 2.85,
                    "prim_paths_sha256": cutaway_paths_sha256,
                    "selection_rule": (
                        "L0 per-floor view: hide ceiling/light actors, non-L0 floor "
                        "actors, and actor roots wholly above z=2.85 m"
                    ),
                    "restore_before_next_view_and_physics_step": True,
                    "navigation_sensor_and_planner_inputs_unchanged": True,
                }
        if _forest_v8_official_enabled(args):
            official_animation_player = _OfficialHumanAnimationPlayer(
                stage,
                args.official_human_animation_cache,
                args.official_human_animation_mode,
            )
        if _office_crowd_enabled(args):
            office_animation_players = [
                _OfficialHumanAnimationPlayer(
                    stage,
                    args.official_human_animation_cache,
                    args.official_human_animation_mode,
                    visual_root_path=f"{OFFICE_HUMAN_VISUAL_PREFIX}_{index}",
                )
                for index in range(len(office_routes))
            ]
        if forest_layout is not None:
            static_forest_geometry_checks = _inspect_forest_geometry(
                stage,
                forest_layout,
                lidar,
                depth_camera,
            )
        if dynamic_obstacle is not None:
            initial_dynamic_state = dynamic_obstacle_state(
                0.0,
                dynamic_spec,
                lambda x, y: _forest_height_world(forest_layout, x, y),
            )
            initial_dynamic_pose = torch.tensor(
                [[*initial_dynamic_state["center_xyz_m"], 1.0, 0.0, 0.0, 0.0]],
                dtype=torch.float32,
                device=base_env.device,
            )
            dynamic_obstacle.write_root_pose_to_sim(initial_dynamic_pose)
            dynamic_obstacle.write_root_velocity_to_sim(
                torch.zeros((1, 6), dtype=torch.float32, device=base_env.device)
            )
            if _forest_v8_enabled(args):
                _apply_procedural_human_gait(
                    stage,
                    procedural_human_gait_angles(0.0, "waiting"),
                )
            elif _forest_v8_official_enabled(args):
                initial_registered_state = official_human_registered_state(
                    initial_dynamic_state,
                    dynamic_spec,
                    source_foot_z_m=OFFICIAL_HUMAN_SOURCE_FOOT_Z_M,
                    source_visible_top_z_m=OFFICIAL_HUMAN_SOURCE_VISIBLE_TOP_Z_M,
                    source_forward_yaw_radians=(
                        OFFICIAL_HUMAN_SOURCE_FORWARD_YAW_RADIANS
                    ),
                )
                official_visual_pose_evidence = _set_official_human_visual_pose(
                    stage, initial_registered_state
                )
                official_animation_player.update(0.0, "waiting")
            base_env.sim.forward()
            dynamic_obstacle_geometry_checks = _inspect_dynamic_obstacle(
                stage,
                dynamic_obstacle,
                lidar,
                depth_camera,
                (
                    _official_human_sensor_exprs()
                    if _forest_v8_official_enabled(args)
                    else _dynamic_human_part_exprs()
                    if _forest_v8_enabled(args)
                    else (DYNAMIC_OBSTACLE_PRIM_EXPR,)
                ),
                require_separate_official_visual=_forest_v8_official_enabled(args),
            )
        runtime_composition = {
            "schema_version": 1,
            "candidate": _candidate_name(args),
            "v12_task_contract": v12_task_contract,
            "configured_robot_asset": asset_identity,
            "runtime_body_names": list(robot.body_names),
            "runtime_joint_names": list(robot.joint_names),
            "runtime_default_joint_position": default_joint_position,
            "runtime_mass_by_link_kg": runtime_mass_by_link,
            "runtime_total_mass_kg": sum(runtime_mass_by_link.values()),
            "runtime_inertia_by_link_kg_m2_row_major": runtime_inertia_by_link,
            "missing_required_sensor_rig_links": missing_rig_links,
            "imported_prim_paths": imported_prim_paths,
            "imported_collision_prim_paths": imported_collision_prim_paths,
            "imported_joint_prim_paths": imported_joint_prim_paths,
            "imported_fixed_joint_prim_paths": imported_fixed_joint_prim_paths,
            "imported_movable_joint_prim_paths": imported_movable_joint_prim_paths,
            "imported_geometry_prim_records": imported_geometry_prim_records,
            "silent_default_mass_check": {
                "mid360_scan_frame_mass_kg": runtime_mass_by_link.get(MID360_FRAME),
                "d435i_depth_optical_frame_mass_kg": runtime_mass_by_link.get(
                    D435I_FRAME
                ),
                "expected_frame_mass_kg": 1.0e-6,
                "status": "pass" if sensor_rig else "not_applicable",
            },
            "navigation_lidar_prim_path": lidar.cfg.prim_path,
            "navigation_depth_camera_prim_path": (
                None if depth_camera is None else depth_camera.cfg.prim_path
            ),
            "forest_scene": (
                None
                if forest_layout is None
                else {
                    "identity": forest_layout["identity"],
                    "static_geometry_checks": static_forest_geometry_checks,
                }
            ),
            "dynamic_obstacle": (
                None
                if dynamic_obstacle is None
                else {
                    "identity": identity["dynamic_obstacle"],
                    "geometry_checks": dynamic_obstacle_geometry_checks,
                    "official_visual_initial_pose": (
                        official_visual_pose_evidence
                        if _forest_v8_official_enabled(args)
                        else None
                    ),
                    "official_animation_player_initialized": (
                        official_animation_player is not None
                        if _forest_v8_official_enabled(args)
                        else None
                    ),
                }
            ),
            "office_review_presentation": (
                {
                    **identity.get("office_review_presentation", {}),
                    "camera_render_cutaway_runtime": review_cutaway_audit,
                    "renderer_runtime_settings": review_renderer_runtime_settings,
                }
                if _office_review_presentation_enabled(args)
                else None
            ),
        }
        _write_json(output_dir / "runtime_composition.json", runtime_composition)
        if (
            static_forest_geometry_checks is not None
            and not static_forest_geometry_checks["passed"]
        ):
            raise AdapterFailure("forest visible/physics/sensor static gate failed")
        if (
            dynamic_obstacle_geometry_checks is not None
            and not dynamic_obstacle_geometry_checks["passed"]
        ):
            raise AdapterFailure("dynamic obstacle physics/sensor gate failed")
        previous_actions = torch.zeros((1, 12), device=base_env.device)
        sensor_stride = max(1, int(round(args.sensor_period / float(base_env.step_dt))))
        if args.video_path is not None:
            args.video_path.parent.mkdir(parents=True, exist_ok=True)
            for _ in range(8):
                _rgb_frame(raw_env.render())
            side_v_path = _office_review_side_video_path(args)
            over_v_path = _office_review_overview_video_path(args)
            if _office_review_presentation_enabled(args):
                import omni.usd
                from pxr import Usd, UsdGeom

                viewport_stage = omni.usd.get_context().get_stage()
                viewport_camera_prim = viewport_stage.GetPrimAtPath(
                    "/OmniverseKit_Persp"
                )
                if not viewport_camera_prim.IsValid() or not viewport_camera_prim.IsA(
                    UsdGeom.Camera
                ):
                    raise AdapterFailure(
                        "Office review viewport camera /OmniverseKit_Persp is missing"
                    )
                review_viewport_camera = UsdGeom.Camera(viewport_camera_prim)
                review_default_focal_length_mm = float(
                    review_viewport_camera.GetFocalLengthAttr().Get()
                )
                review_default_horizontal_aperture_mm = float(
                    review_viewport_camera.GetHorizontalApertureAttr().Get()
                )
                if (
                    not math.isfinite(review_default_focal_length_mm)
                    or review_default_focal_length_mm <= 0.0
                ):
                    raise AdapterFailure(
                        "Office review viewport camera has invalid focal length"
                    )
                if (
                    not math.isfinite(review_default_horizontal_aperture_mm)
                    or review_default_horizontal_aperture_mm <= 0.0
                ):
                    raise AdapterFailure(
                        "Office review viewport camera has invalid horizontal aperture"
                    )

                def _render_camera_with_shared_cutaway():
                    if not review_cutaway_imageables or review_cutaway_audit is None:
                        raise AdapterFailure(
                            "Office shared review-camera cutaway was not initialized"
                        )
                    try:
                        with Usd.EditContext(
                            viewport_stage, viewport_stage.GetSessionLayer()
                        ):
                            for _, imageable, _ in review_cutaway_imageables:
                                if not imageable.GetVisibilityAttr().Set(
                                    UsdGeom.Tokens.invisible
                                ):
                                    raise AdapterFailure(
                                        "Office shared cutaway visibility could not be authored"
                                    )
                        return _rgb_frame(
                            render_temporally_settled_frame(
                                raw_env.render,
                                int(
                                    review_capture_profile[
                                        "renderer_settle_render_count"
                                    ]
                                ),
                            )
                        )
                    finally:
                        with Usd.EditContext(
                            viewport_stage, viewport_stage.GetSessionLayer()
                        ):
                            for (
                                _,
                                imageable,
                                original_visibility,
                            ) in review_cutaway_imageables:
                                restore_token = (
                                    original_visibility
                                    if original_visibility is not None
                                    else UsdGeom.Tokens.inherited
                                )
                                if not imageable.GetVisibilityAttr().Set(restore_token):
                                    raise AdapterFailure(
                                        "Office shared cutaway visibility could not be restored"
                                    )

                review_render_frame = _render_camera_with_shared_cutaway
                exact_capture_fps = 1.0 / (float(base_env.step_dt) * args.video_frame_stride)
                if abs(exact_capture_fps - float(args.video_fps)) > 1e-9:
                    raise AdapterFailure(
                        f"review capture cadence is {exact_capture_fps} fps, not declared {args.video_fps} fps"
                    )
                video_writer = review_writer_type(args.video_path, args.video_fps, review_capture_profile)
                third_person_video_writer = review_writer_type(side_v_path, args.video_fps, review_capture_profile)
                overview_video_writer = review_writer_type(over_v_path, args.video_fps, review_capture_profile)
            else:
                import imageio
                video_writer = imageio.get_writer(
                    str(args.video_path), fps=args.video_fps, codec="libx264",
                    quality=8, macro_block_size=16,
                )
            if (
                _office_enabled(args)
                and args.office_review_camera_trace_path is not None
            ):
                args.office_review_camera_trace_path.parent.mkdir(
                    parents=True, exist_ok=True
                )
                camera_trace_handle = args.office_review_camera_trace_path.open(
                    "x", encoding="utf-8"
                )
        # Expose the TCP endpoints only after the scene, policy, sensor, and
        # optional renderer are ready. Otherwise a Foxy client can accumulate
        # commands that become stale during simulator initialization.
        command_server.start()
        telemetry_server.start()
        if sink is not None:
            sink.start()
        if sender is not None:
            sender.start()
        connection_deadline = time.monotonic() + args.connection_ready_timeout_seconds
        while time.monotonic() < connection_deadline:
            if sender is not None and sender.error is not None:
                raise AdapterFailure(f"fallback command sender failed: {sender.error}")
            if (
                command_server.stats().accepted_connections > 0
                and telemetry_server.stats().accepted_connections > 0
            ):
                break
            time.sleep(0.01)
        else:
            raise AdapterFailure(
                "command and telemetry clients did not connect before the ready timeout"
            )
        started = time.monotonic()
        next_tick = started
        active_schedule = (
            qualification_schedule
            if qualification_schedule is not None
            else DEFAULT_QUALIFICATION_SCHEDULE
        )
        run_seconds = (
            schedule_duration(active_schedule) + 0.25
            if args.mode in ("qualification", "sensor_qualification")
            else args.duration_seconds
        )
        dynamic_schedule_start_sim_time = (
            float(base_env.sim.current_time)
            if dynamic_obstacle is not None
            and args.dynamic_obstacle_schedule_trigger == "run_start"
            else None
        )
        initial_sim_time = float(base_env.sim.current_time)
        max_wall_seconds = run_seconds * 6.0 + 60.0
        max_step_wall_seconds = float(args.max_step_wall_seconds)
        if _office_review_presentation_enabled(args):
            # The presentation capture renders three 2K observer views and
            # deliberately settles temporal lighting history before encoding
            # each frame.  The legacy 6x wall-clock allowance can therefore
            # truncate a nominal 10 s simulator run even though it exits
            # cleanly.  Budget from the declared view/settle workload, with a
            # conservative per-render allowance for RTX shader/cache variance.
            review_view_count = 3
            settle_render_count = int(
                review_capture_profile["renderer_settle_render_count"]
            )
            review_wall_seconds = (
                run_seconds
                * review_view_count
                * settle_render_count
                * 4.0
                + 120.0
            )
            max_wall_seconds = max(max_wall_seconds, review_wall_seconds)
            max_step_wall_seconds = max(
                max_step_wall_seconds,
                review_view_count * settle_render_count * 2.0 + 5.0,
            )
        metrics_path = output_dir / "metrics.jsonl"
        sensor_metrics_path = output_dir / "sensor_metrics.jsonl"
        depth_metrics_path = output_dir / "depth_metrics.jsonl"
        with metrics_path.open("w", encoding="utf-8") as metrics_file, \
                sensor_metrics_path.open("w", encoding="utf-8") as sensor_metrics_file, \
                depth_metrics_path.open("w", encoding="utf-8") as depth_metrics_file:
            step = 0
            while (float(base_env.sim.current_time) - initial_sim_time < run_seconds) and (time.monotonic() - started < max_wall_seconds):
                tick_started = time.monotonic()
                if sender is not None and sender.error is not None:
                    raise AdapterFailure(f"fallback command sender failed: {sender.error}")
                snapshot = command_server.snapshot(time.monotonic_ns())
                command = (snapshot.command.vx, snapshot.command.vy, snapshot.command.wz)
                if (
                    dynamic_obstacle is not None
                    and dynamic_schedule_start_sim_time is None
                    and args.dynamic_obstacle_schedule_trigger
                    == "first_nonzero_body_command"
                    and max(abs(float(value)) for value in command) > 0.05
                ):
                    dynamic_schedule_start_sim_time = float(base_env.sim.current_time)
                scheduled_dynamic_state = None
                dynamic_human_gait = None
                office_pedestrian_states = []
                if office_pedestrians:
                    office_visual_pose_evidence = []
                    for index, (pedestrian, route, player) in enumerate(
                        zip(
                            office_pedestrians,
                            office_routes,
                            office_animation_players,
                            strict=True,
                        )
                    ):
                        pedestrian_state = office_pedestrian_state(
                            float(base_env.sim.current_time), route
                        )
                        x, y = pedestrian_state["xy_m"]
                        yaw = pedestrian_state["yaw_rad"]
                        half_yaw = 0.5 * yaw
                        center_z = 0.5 * OFFICIAL_HUMAN_CAPSULE_HEIGHT_M + 0.02
                        pose = torch.tensor(
                            [[x, y, center_z, math.cos(half_yaw), 0.0, 0.0, math.sin(half_yaw)]],
                            dtype=torch.float32,
                            device=base_env.device,
                        )
                        velocity_xy = pedestrian_state["velocity_xy_mps"]
                        velocity = torch.tensor(
                            [[*velocity_xy, 0.0, 0.0, 0.0, 0.0]],
                            dtype=torch.float32,
                            device=base_env.device,
                        )
                        pedestrian.write_root_pose_to_sim(pose)
                        pedestrian.write_root_velocity_to_sim(velocity)
                        visual_yaw = yaw - OFFICIAL_HUMAN_SOURCE_FORWARD_YAW_RADIANS
                        visual_half_yaw = 0.5 * visual_yaw
                        registered = {
                            "visual_root_xyz_m": (x, y, 0.02 - OFFICIAL_HUMAN_SOURCE_FOOT_Z_M),
                            "visual_quaternion_wxyz": (
                                math.cos(visual_half_yaw),
                                0.0,
                                0.0,
                                math.sin(visual_half_yaw),
                            ),
                            "visual_yaw_radians": visual_yaw,
                            "visual_foot_world_z_m": 0.02,
                            "visual_top_world_z_m": (
                                0.02
                                - OFFICIAL_HUMAN_SOURCE_FOOT_Z_M
                                + OFFICIAL_HUMAN_SOURCE_VISIBLE_TOP_Z_M
                            ),
                            "capsule_bottom_world_z_m": 0.02,
                            "foot_to_capsule_bottom_error_m": 0.0,
                        }
                        visual_evidence = _set_official_human_visual_pose(
                            stage,
                            registered,
                            visual_root_path=f"{OFFICE_HUMAN_VISUAL_PREFIX}_{index}",
                        )
                        animation_evidence = player.update(
                            float(base_env.sim.current_time),
                            "crossing"
                            if pedestrian_state["phase"] == "walking"
                            else "waiting",
                        )
                        office_visual_pose_evidence.append(visual_evidence)
                        office_pedestrian_states.append(
                            {
                                "name": route.name,
                                **pedestrian_state,
                                "center_xyz_m": [x, y, center_z],
                                "velocity_xy_mps": list(velocity_xy),
                                "animation": animation_evidence,
                            }
                        )
                if dynamic_obstacle is not None:
                    scheduled_dynamic_state = dynamic_obstacle_state(
                        0.0
                        if dynamic_schedule_start_sim_time is None
                        else max(
                            0.0,
                            float(base_env.sim.current_time)
                            - dynamic_schedule_start_sim_time,
                        ),
                        dynamic_spec,
                        lambda x, y: _forest_height_world(forest_layout, x, y),
                    )
                    dynamic_pose = torch.tensor(
                        [[*scheduled_dynamic_state["center_xyz_m"], 1.0, 0.0, 0.0, 0.0]],
                        dtype=torch.float32,
                        device=base_env.device,
                    )
                    dynamic_velocity_xy = scheduled_dynamic_state[
                        "velocity_xy_mps"
                    ]
                    dynamic_velocity = torch.tensor(
                        [[*dynamic_velocity_xy, 0.0, 0.0, 0.0, 0.0]],
                        dtype=torch.float32,
                        device=base_env.device,
                    )
                    dynamic_obstacle.write_root_pose_to_sim(dynamic_pose)
                    dynamic_obstacle.write_root_velocity_to_sim(dynamic_velocity)
                    if _forest_v8_enabled(args):
                        dynamic_human_gait = procedural_human_gait_angles(
                            scheduled_dynamic_state["elapsed_seconds"],
                            scheduled_dynamic_state["phase"],
                            DYNAMIC_HUMAN_GAIT_CADENCE_HZ,
                            DYNAMIC_HUMAN_GAIT_MAX_SWING_RADIANS,
                        )
                        _apply_procedural_human_gait(stage, dynamic_human_gait)
                    elif _forest_v8_official_enabled(args):
                        registered_state = official_human_registered_state(
                            scheduled_dynamic_state,
                            dynamic_spec,
                            source_foot_z_m=OFFICIAL_HUMAN_SOURCE_FOOT_Z_M,
                            source_visible_top_z_m=(
                                OFFICIAL_HUMAN_SOURCE_VISIBLE_TOP_Z_M
                            ),
                            source_forward_yaw_radians=(
                                OFFICIAL_HUMAN_SOURCE_FORWARD_YAW_RADIANS
                            ),
                        )
                        official_visual_pose_evidence = (
                            _set_official_human_visual_pose(stage, registered_state)
                        )
                        dynamic_human_gait = official_animation_player.update(
                            scheduled_dynamic_state["elapsed_seconds"],
                            scheduled_dynamic_state["phase"],
                        )
                command_term = base_env.command_manager.get_term("base_velocity")
                command_term.commands[:, 0] = command[0]
                command_term.commands[:, 1] = command[1]
                command_term.commands[:, 2] = command[2]
                observation, _, dones, _ = wrapped_env.step(previous_actions)
                policy_state.reset(dones)
                actual_command = base_env.command_manager.get_command("base_velocity")
                expected_command = actual_command.new_tensor([command])
                if not torch.allclose(actual_command, expected_command, atol=1.0e-6, rtol=0.0):
                    raise AdapterFailure(
                        "V12 live command drifted after the physics step: "
                        f"actual={actual_command.detach().cpu().tolist()} "
                        f"expected={expected_command.detach().cpu().tolist()} "
                        f"dones={dones.detach().cpu().tolist()}"
                    )
                observed_command, command_error, command_history_index = _policy_command_evidence(
                    observation, command
                )
                with torch.inference_mode():
                    actions = policy(observation)
                if tuple(actions.shape) != (1, 12):
                    raise AdapterFailure(f"V12 action shape {tuple(actions.shape)} != (1, 12)")
                previous_actions = actions

                force_norm = torch.linalg.vector_norm(contact.data.net_forces_w[0], dim=-1)
                contact_count = int(
                    (force_norm[contact_foot_ids] >= args.contact_force_threshold).sum().item()
                )
                nonfoot_ids = [
                    index for index in range(force_norm.shape[0]) if index not in contact_foot_ids
                ]
                nonfoot_max = float(force_norm[nonfoot_ids].max().item()) if nonfoot_ids else 0.0
                done = bool(dones.any().item())
                finite = bool(
                    all(torch.isfinite(value).all().item() for value in observation.values())
                    and torch.isfinite(actions).all().item()
                    and torch.isfinite(robot.data.root_state_w).all().item()
                )
                now = time.monotonic()
                command_age_ms = (
                    0.0
                    if snapshot.received_monotonic_ns is None
                    else max(
                        0.0,
                        (time.monotonic_ns() - snapshot.received_monotonic_ns) / 1.0e6,
                    )
                )
                schedule_elapsed = 0.0
                if sender is not None and sender.started_monotonic is not None:
                    schedule_elapsed = max(0.0, now - sender.started_monotonic)
                segment, segment_elapsed = schedule_state(
                    schedule_elapsed, active_schedule
                )
                root_position = _tensor_list(robot.data.root_pos_w[0])
                terrain_height_under_root = (
                    _forest_height_world(
                        forest_layout,
                        root_position[0],
                        root_position[1],
                    )
                    if forest_layout is not None
                    else 0.0
                )
                dynamic_metrics = {}
                if dynamic_obstacle is not None:
                    dynamic_actual_position = _tensor_list(
                        dynamic_obstacle.data.root_pos_w[0]
                    )
                    dynamic_actual_velocity = _tensor_list(
                        dynamic_obstacle.data.root_lin_vel_w[0]
                    )
                    dynamic_ground_z = _forest_height_world(
                        forest_layout,
                        dynamic_actual_position[0],
                        dynamic_actual_position[1],
                    )
                    dynamic_center_distance = math.dist(
                        root_position[:2], dynamic_actual_position[:2]
                    )
                    dynamic_metrics = {
                        "dynamic_obstacle_phase": scheduled_dynamic_state["phase"],
                        "dynamic_obstacle_elapsed_seconds": scheduled_dynamic_state[
                            "elapsed_seconds"
                        ],
                        "dynamic_obstacle_schedule_triggered": (
                            dynamic_schedule_start_sim_time is not None
                        ),
                        "dynamic_obstacle_schedule_trigger_mode": (
                            args.dynamic_obstacle_schedule_trigger
                        ),
                        "dynamic_obstacle_trigger_sim_time_seconds": (
                            dynamic_schedule_start_sim_time
                        ),
                        "dynamic_obstacle_crossing_fraction": scheduled_dynamic_state[
                            "crossing_fraction"
                        ],
                        "dynamic_obstacle_scheduled_pos_w": list(
                            scheduled_dynamic_state["center_xyz_m"]
                        ),
                        "dynamic_obstacle_actual_pos_w": dynamic_actual_position,
                        "dynamic_obstacle_scheduled_lin_vel_w": [
                            *scheduled_dynamic_state["velocity_xy_mps"],
                            0.0,
                        ],
                        "dynamic_obstacle_actual_lin_vel_w": dynamic_actual_velocity,
                        "dynamic_obstacle_pose_error_m": math.dist(
                            scheduled_dynamic_state["center_xyz_m"],
                            dynamic_actual_position,
                        ),
                        "dynamic_obstacle_terrain_height_m": dynamic_ground_z,
                        "dynamic_obstacle_bottom_clearance_m": (
                            dynamic_actual_position[2]
                            - 0.5 * dynamic_spec.height_m
                            - dynamic_ground_z
                        ),
                        "root_to_dynamic_center_xy_m": dynamic_center_distance,
                        "root_to_dynamic_surface_clearance_m": (
                            circle_surface_clearance_2d(
                                root_position[:2],
                                dynamic_actual_position[:2],
                                FOREST_NAVIGATION_PLANNING_RADIUS_M,
                                dynamic_spec.radius_m,
                            )
                        ),
                        "dynamic_human_gait_angles": dynamic_human_gait,
                        "official_human_visual_pose": (
                            official_visual_pose_evidence
                            if _forest_v8_official_enabled(args)
                            else None
                        ),
                    }
                row = {
                    "step": step,
                    "wall_elapsed_seconds": now - started,
                    "sim_time_seconds": float(base_env.sim.current_time),
                    "schedule_segment": (
                        segment.name if sender is not None else "external"
                    ),
                    "schedule_segment_elapsed_seconds": segment_elapsed,
                    "applied_command": list(command),
                    "command_sequence": snapshot.sequence,
                    "command_reason": snapshot.reason,
                    "command_stale": snapshot.stale,
                    "command_observation": observed_command,
                    "command_observation_history_index": command_history_index,
                    "command_observation_max_error": command_error,
                    "root_pos_w": root_position,
                    "terrain_height_under_root_m": terrain_height_under_root,
                    "base_clearance_m": root_position[2] - terrain_height_under_root,
                    "root_quat_wxyz": _tensor_list(robot.data.root_quat_w[0]),
                    "root_lin_vel_w": _tensor_list(robot.data.root_lin_vel_w[0]),
                    "root_ang_vel_w": _tensor_list(robot.data.root_ang_vel_w[0]),
                    "root_lin_vel_b": _tensor_list(robot.data.root_lin_vel_b[0]),
                    "root_ang_vel_b": _tensor_list(robot.data.root_ang_vel_b[0]),
                    "actions": _tensor_list(actions[0]),
                    "joint_position": _tensor_list(robot.data.joint_pos[0]),
                    "joint_velocity": _tensor_list(robot.data.joint_vel[0]),
                    "applied_torque": _tensor_list(robot.data.applied_torque[0]),
                    "contact_count": contact_count,
                    "nonfoot_contact_max_n": nonfoot_max,
                    "done": done,
                    "finite": finite,
                    "watchdog_events": snapshot.watchdog_events,
                    "sequence_gaps": snapshot.sequence_gaps,
                    "command_age_ms": command_age_ms,
                    "office_pedestrians": office_pedestrian_states,
                    "office_human_visual_poses": office_visual_pose_evidence,
                    **dynamic_metrics,
                }
                records.append(row)
                metrics_file.write(json.dumps(row, sort_keys=True) + "\n")
                metrics_file.flush()

                if step % sensor_stride == 0:
                    mid360_window = None
                    if _official_mid360_enabled(args):
                        mid360_window = _set_mid360_scan_window(
                            lidar,
                            args.mid360_pattern_table,
                            mid360_scan_index,
                            torch,
                        )
                    else:
                        lidar.update(dt=0.0, force_recompute=True)
                    hits_w = lidar.data.ray_hits_w[0]
                    sensor_position = lidar.data.pos_w[0]
                    sensor_quaternion_wxyz_tensor = lidar.data.quat_w[0]
                    sensor_timestamp_ns = int(
                        float(base_env.sim.current_time) * 1.0e9
                    )
                    body_position_values = _tensor_list(robot.data.root_pos_w[0])
                    body_quaternion_wxyz_values = _tensor_list(
                        robot.data.root_quat_w[0]
                    )
                    sensor_position_values = _tensor_list(sensor_position)
                    sensor_quaternion_values = _tensor_list(
                        sensor_quaternion_wxyz_tensor
                    )
                    world_hit_values = hits_w.detach().cpu().tolist()
                    geometry_filter_stats = None
                    planner_world_hits = world_hit_values
                    raw_points = None
                    if _dual_cloud_geometry_enabled(args):
                        raw_points, points, geometry_filter_stats = split_geometry_cloud_points(
                            world_hit_values,
                            sensor_position_values,
                            sensor_quaternion_values,
                            args.lidar_min_range,
                            args.lidar_max_range,
                            args.terrain_filter_cell_size,
                            args.terrain_filter_height_threshold,
                            args.terrain_filter_neighbor_cells,
                            args.terrain_filter_minimum_neighbor_cells,
                        )
                    elif _forest_navigation_enabled(args):
                        planner_world_hits, geometry_filter_stats = (
                            local_minimum_obstacle_hits(
                                world_hit_values,
                                sensor_position_values,
                                args.lidar_min_range,
                                args.lidar_max_range,
                                args.terrain_filter_cell_size,
                                args.terrain_filter_height_threshold,
                                args.terrain_filter_neighbor_cells,
                                args.terrain_filter_minimum_neighbor_cells,
                            )
                        )
                    else:
                        points = world_hits_to_sensor_points(
                            planner_world_hits,
                            sensor_position_values,
                            sensor_quaternion_values,
                            args.lidar_min_range,
                            args.lidar_max_range,
                            minimum_world_z=(
                                None
                                if forest_layout is not None
                                else args.planner_floor_filter_max_z
                            ),
                        )
                    if _forest_navigation_enabled(args) and not _dual_cloud_geometry_enabled(args):
                        points = world_hits_to_sensor_points(
                            planner_world_hits,
                            sensor_position_values,
                            sensor_quaternion_values,
                            args.lidar_min_range,
                            args.lidar_max_range,
                            minimum_world_z=None,
                        )
                    point_count, point_bytes = pack_xyz_points(points)
                    raw_point_count = None
                    raw_point_bytes = None
                    if _dual_cloud_geometry_enabled(args):
                        assert raw_points is not None
                        raw_point_count, raw_point_bytes = pack_xyz_points(raw_points)
                        if geometry_filter_stats is None:
                            raise AdapterFailure("dual-cloud geometry filter stats are missing")
                    finite_hits = torch.isfinite(hits_w).all(dim=-1)
                    hit_ranges = torch.linalg.vector_norm(
                        hits_w - sensor_position.unsqueeze(0), dim=-1
                    )
                    self_occluded_hits = finite_hits & (
                        hit_ranges < args.lidar_min_range
                    )
                    environment_hit_ranges = hit_ranges[
                        finite_hits & ~self_occluded_hits
                    ]
                    raw_environment_hit_range_min_m = (
                        None
                        if environment_hit_ranges.numel() == 0
                        else float(environment_hit_ranges.min().item())
                    )
                    raw_environment_hit_range_max_m = (
                        None
                        if environment_hit_ranges.numel() == 0
                        else float(environment_hit_ranges.max().item())
                    )
                    planner_point_ranges = [
                        math.sqrt(sum(coordinate * coordinate for coordinate in point))
                        for point in points
                    ]
                    floor_filtered_hits = (
                        torch.zeros_like(finite_hits)
                        if forest_layout is not None
                        else finite_hits
                        & (hits_w[:, 2] <= args.planner_floor_filter_max_z)
                    )
                    obstacle_hits = torch.zeros_like(finite_hits)
                    office_pedestrian_hits = torch.zeros_like(finite_hits)
                    office_pedestrian_hit_counts = {}
                    if args.course == "single_box":
                        center = hits_w.new_tensor(COURSE_OBSTACLE_CENTER)
                        half_size = 0.5 * hits_w.new_tensor(COURSE_OBSTACLE_SIZE)
                        obstacle_hits = (
                            finite_hits
                            & ~self_occluded_hits
                            & (hits_w[:, 2] > args.planner_floor_filter_max_z)
                            & (
                                (hits_w >= center - half_size - 0.01)
                                & (hits_w <= center + half_size + 0.01)
                            ).all(dim=-1)
                        )
                    elif forest_layout is not None:
                        obstacle_hits = _forest_obstacle_hit_mask(
                            hits_w,
                            forest_layout["proxies"],
                            torch,
                        ) & ~self_occluded_hits
                    elif office_pedestrian_states:
                        for pedestrian_state, route in zip(
                            office_pedestrian_states, office_routes, strict=True
                        ):
                            center = hits_w.new_tensor(
                                pedestrian_state["center_xyz_m"]
                            )
                            radial = torch.linalg.vector_norm(
                                hits_w[:, :2] - center[:2], dim=-1
                            )
                            pedestrian_hits = (
                                finite_hits
                                & ~self_occluded_hits
                                & (radial <= route.radius_m + 0.02)
                                & (hits_w[:, 2] >= 0.01)
                                & (
                                    hits_w[:, 2]
                                    <= OFFICIAL_HUMAN_CAPSULE_HEIGHT_M + 0.03
                                )
                            )
                            office_pedestrian_hits |= pedestrian_hits
                            office_pedestrian_hit_counts[route.name] = int(
                                pedestrian_hits.sum().item()
                            )
                    if _office_enabled(args):
                        obstacle_hits |= (
                            finite_hits
                            & ~self_occluded_hits
                            & (hits_w[:, 2] > args.planner_floor_filter_max_z)
                        )
                        obstacle_hits |= office_pedestrian_hits
                    raw_proxy_hit_counts = {}
                    planner_proxy_hit_counts = {}
                    if forest_layout is not None:
                        raw_proxy_hit_counts = _forest_proxy_hit_counts(
                            hits_w,
                            forest_layout["proxies"],
                            torch,
                        )
                        if planner_world_hits:
                            planner_proxy_hit_counts = _forest_proxy_hit_counts(
                                hits_w.new_tensor(planner_world_hits),
                                forest_layout["proxies"],
                                torch,
                            )
                    dynamic_obstacle_hits = torch.zeros_like(finite_hits)
                    if dynamic_obstacle is not None:
                        dynamic_obstacle_hits = _dynamic_obstacle_hit_mask(
                            hits_w,
                            dynamic_actual_position,
                            dynamic_spec,
                            torch,
                        ) & ~self_occluded_hits
                    ground_hits = (
                        finite_hits
                        & ~self_occluded_hits
                        & ~obstacle_hits
                        & ~dynamic_obstacle_hits
                        if forest_layout is not None
                        else finite_hits
                        & ~self_occluded_hits
                        & torch.isclose(
                            hits_w[:, 2],
                            hits_w.new_tensor(0.0),
                            atol=0.03,
                            rtol=0.0,
                        )
                    )
                    centroid = [0.0, 0.0, 0.0]
                    if points:
                        centroid = [
                            sum(point[axis] for point in points) / len(points)
                            for axis in range(3)
                        ]
                    sensor_row = {
                        "step": step,
                        "sim_time_seconds": float(base_env.sim.current_time),
                        "scan_reference_timestamp_ns": sensor_timestamp_ns,
                        "body_position_w": body_position_values,
                        "body_quaternion_wxyz": body_quaternion_wxyz_values,
                        "sensor_position_w": sensor_position_values,
                        "sensor_quaternion_wxyz": sensor_quaternion_values,
                        "lidar_pattern_mode": args.lidar_pattern_mode,
                        "pattern_window": (
                            None
                            if mid360_window is None
                            else mid360_window.as_dict()
                        ),
                        "intra_scan_motion_distortion": (
                            "not_modeled_simultaneous_same_step_snapshot"
                            if mid360_window is not None
                            else "legacy_uniform_snapshot"
                        ),
                        "raw_ray_count": int(hits_w.shape[0]),
                        "scan_id": (
                            mid360_scan_index + 1
                            if _dual_cloud_geometry_enabled(args)
                            else None
                        ),
                        "raw_cloud_point_count": raw_point_count,
                        "planning_cloud_point_count": point_count,
                        "filtered_ground_point_count": (
                            None
                            if geometry_filter_stats is None
                            else geometry_filter_stats["filtered_ground_hit_count"]
                        ),
                        "conservative_retained_point_count": (
                            None
                            if geometry_filter_stats is None
                            else geometry_filter_stats["sparse_retained_hit_count"]
                        ),
                        "point_count": point_count,
                        "finite_point_count": point_count,
                        "raw_finite_hit_count": int(finite_hits.sum().item()),
                        "raw_environment_hit_range_min_m": (
                            raw_environment_hit_range_min_m
                        ),
                        "raw_environment_hit_range_max_m": (
                            raw_environment_hit_range_max_m
                        ),
                        "planner_point_range_min_m": (
                            None
                            if not planner_point_ranges
                            else min(planner_point_ranges)
                        ),
                        "planner_point_range_max_m": (
                            None
                            if not planner_point_ranges
                            else max(planner_point_ranges)
                        ),
                        "self_occluded_hit_count": int(
                            self_occluded_hits.sum().item()
                        ),
                        "planner_floor_filtered_hit_count": int(
                            floor_filtered_hits.sum().item()
                        ),
                        "planner_geometry_filter_enabled": (
                            geometry_filter_stats is not None
                        ),
                        "planner_geometry_filter_input_hit_count": (
                            0
                            if geometry_filter_stats is None
                            else geometry_filter_stats["input_hit_count"]
                        ),
                        "planner_geometry_filter_finite_in_range_hit_count": (
                            0
                            if geometry_filter_stats is None
                            else geometry_filter_stats[
                                "finite_in_range_hit_count"
                            ]
                        ),
                        "planner_geometry_filter_cell_count": (
                            0
                            if geometry_filter_stats is None
                            else geometry_filter_stats["cell_count"]
                        ),
                        "planner_geometry_filter_ground_hit_count": (
                            0
                            if geometry_filter_stats is None
                            else geometry_filter_stats["filtered_ground_hit_count"]
                        ),
                        "planner_geometry_filter_obstacle_hit_count": (
                            0
                            if geometry_filter_stats is None
                            else geometry_filter_stats["obstacle_hit_count"]
                        ),
                        "planner_geometry_filter_sparse_retained_hit_count": (
                            0
                            if geometry_filter_stats is None
                            else geometry_filter_stats["sparse_retained_hit_count"]
                        ),
                        "ground_hit_count": int(ground_hits.sum().item()),
                        "terrain_surface_hit_count": int(
                            ground_hits.sum().item()
                            if forest_layout is not None
                            else 0
                        ),
                        "obstacle_surface_hit_count": int(obstacle_hits.sum().item()),
                        "office_pedestrian_surface_hit_count": int(
                            office_pedestrian_hits.sum().item()
                        ),
                        "office_pedestrian_surface_hit_counts": (
                            office_pedestrian_hit_counts
                        ),
                        "forest_raw_proxy_hit_counts": raw_proxy_hit_counts,
                        "forest_planner_proxy_hit_counts": planner_proxy_hit_counts,
                        "dynamic_obstacle_surface_hit_count": int(
                            dynamic_obstacle_hits.sum().item()
                        ),
                        "dynamic_obstacle_actual_pos_w": (
                            None
                            if dynamic_obstacle is None
                            else dynamic_actual_position
                        ),
                        "dynamic_human_gait_angles": dynamic_human_gait,
                        "official_human_visual_pose": (
                            official_visual_pose_evidence
                            if _forest_v8_official_enabled(args)
                            else None
                        ),
                        "unexpected_above_floor_hit_count": int(
                            0
                            if forest_layout is not None
                            else (
                                finite_hits
                                & ~self_occluded_hits
                                & (hits_w[:, 2] > args.planner_floor_filter_max_z)
                                & ~obstacle_hits
                            ).sum().item()
                        ),
                        "centroid_sensor": centroid,
                    }
                    sensor_records.append(sensor_row)
                    sensor_metrics_file.write(json.dumps(sensor_row, sort_keys=True) + "\n")
                    sensor_metrics_file.flush()
                    if depth_camera is not None:
                        depth_camera.update(dt=0.0, force_recompute=True)
                        depth_data = depth_camera.data
                        raw_depth = depth_data.output["distance_to_image_plane"][
                            0, ..., 0
                        ].clone()
                        camera_hits_w = depth_camera.ray_hits_w[0].reshape(-1, 3)
                        camera_position = depth_data.pos_w[0]
                        camera_ranges = torch.linalg.vector_norm(
                            camera_hits_w - camera_position.unsqueeze(0), dim=-1
                        )
                        finite_camera_hits = torch.isfinite(camera_hits_w).all(dim=-1)
                        self_occluded_pixels = finite_camera_hits & (
                            camera_ranges < args.depth_min_range
                        )
                        depth_flat = raw_depth.reshape(-1)
                        depth_flat[self_occluded_pixels] = args.depth_max_range
                        finite_depth = torch.isfinite(depth_flat)
                        valid_depth = (
                            finite_depth
                            & (depth_flat >= args.depth_min_range)
                            & (depth_flat < args.depth_max_range)
                        )
                        obstacle_pixels = torch.zeros_like(finite_camera_hits)
                        office_pedestrian_pixels = torch.zeros_like(
                            finite_camera_hits
                        )
                        office_pedestrian_pixel_counts = {}
                        if args.course == "single_box":
                            center = camera_hits_w.new_tensor(COURSE_OBSTACLE_CENTER)
                            half_size = 0.5 * camera_hits_w.new_tensor(
                                COURSE_OBSTACLE_SIZE
                            )
                            obstacle_pixels = (
                                finite_camera_hits
                                & ~self_occluded_pixels
                                & (
                                    (camera_hits_w >= center - half_size - 0.01)
                                    & (camera_hits_w <= center + half_size + 0.01)
                                ).all(dim=-1)
                            )
                        elif forest_layout is not None:
                            obstacle_pixels = _forest_obstacle_hit_mask(
                                camera_hits_w,
                                forest_layout["proxies"],
                                torch,
                            ) & ~self_occluded_pixels
                        elif office_pedestrian_states:
                            for pedestrian_state, route in zip(
                                office_pedestrian_states, office_routes, strict=True
                            ):
                                center = camera_hits_w.new_tensor(
                                    pedestrian_state["center_xyz_m"]
                                )
                                radial = torch.linalg.vector_norm(
                                    camera_hits_w[:, :2] - center[:2], dim=-1
                                )
                                pedestrian_pixels = (
                                    finite_camera_hits
                                    & ~self_occluded_pixels
                                    & (radial <= route.radius_m + 0.02)
                                    & (camera_hits_w[:, 2] >= 0.01)
                                    & (
                                        camera_hits_w[:, 2]
                                        <= OFFICIAL_HUMAN_CAPSULE_HEIGHT_M + 0.03
                                    )
                                )
                                office_pedestrian_pixels |= pedestrian_pixels
                                office_pedestrian_pixel_counts[route.name] = int(
                                    pedestrian_pixels.sum().item()
                                )
                        if _office_enabled(args):
                            obstacle_pixels |= (
                                finite_camera_hits
                                & ~self_occluded_pixels
                                & (
                                    camera_hits_w[:, 2]
                                    > args.planner_floor_filter_max_z
                                )
                            )
                            obstacle_pixels |= office_pedestrian_pixels
                        dynamic_obstacle_pixels = torch.zeros_like(
                            finite_camera_hits
                        )
                        if dynamic_obstacle is not None:
                            dynamic_obstacle_pixels = _dynamic_obstacle_hit_mask(
                                camera_hits_w,
                                dynamic_actual_position,
                                dynamic_spec,
                                torch,
                            ) & ~self_occluded_pixels
                        valid_values = depth_flat[valid_depth]
                        depth_row = {
                            "step": step,
                            "sim_time_seconds": float(base_env.sim.current_time),
                            "sensor_position_w": _tensor_list(camera_position),
                            "sensor_quaternion_wxyz_ros": _tensor_list(
                                depth_data.quat_w_ros[0]
                            ),
                            "width": args.depth_width,
                            "height": args.depth_height,
                            "intrinsic_matrix": depth_data.intrinsic_matrices[0]
                            .detach()
                            .cpu()
                            .tolist(),
                            "pixel_count": int(depth_flat.numel()),
                            "nonfinite_depth_count": int(
                                (~finite_depth).sum().item()
                            ),
                            "valid_depth_pixel_count": int(valid_depth.sum().item()),
                            "self_occluded_pixel_count": int(
                                self_occluded_pixels.sum().item()
                            ),
                            "obstacle_surface_pixel_count": int(
                                obstacle_pixels.sum().item()
                            ),
                            "office_pedestrian_surface_pixel_count": int(
                                office_pedestrian_pixels.sum().item()
                            ),
                            "office_pedestrian_surface_pixel_counts": (
                                office_pedestrian_pixel_counts
                            ),
                            "dynamic_obstacle_surface_pixel_count": int(
                                dynamic_obstacle_pixels.sum().item()
                            ),
                            "dynamic_obstacle_actual_pos_w": (
                                None
                                if dynamic_obstacle is None
                                else dynamic_actual_position
                            ),
                            "dynamic_human_gait_angles": dynamic_human_gait,
                            "official_human_visual_pose": (
                                official_visual_pose_evidence
                                if _forest_v8_official_enabled(args)
                                else None
                            ),
                            "minimum_valid_depth_m": (
                                None
                                if valid_values.numel() == 0
                                else float(valid_values.min().item())
                            ),
                            "maximum_valid_depth_m": (
                                None
                                if valid_values.numel() == 0
                                else float(valid_values.max().item())
                            ),
                            "mean_valid_depth_m": (
                                None
                                if valid_values.numel() == 0
                                else float(valid_values.mean().item())
                            ),
                        }
                        depth_records.append(depth_row)
                        depth_metrics_file.write(
                            json.dumps(depth_row, sort_keys=True) + "\n"
                        )
                        depth_metrics_file.flush()
                        best_obstacle_count = (
                            -1
                            if best_depth_metadata is None
                            else best_depth_metadata["obstacle_surface_pixel_count"]
                            + best_depth_metadata.get(
                                "dynamic_obstacle_surface_pixel_count", 0
                            )
                        )
                        if (
                            depth_row["obstacle_surface_pixel_count"]
                            + depth_row["dynamic_obstacle_surface_pixel_count"]
                            > best_obstacle_count
                        ):
                            best_depth_frame = raw_depth.detach().cpu().clone()
                            best_depth_metadata = dict(depth_row)
                    if _dual_cloud_geometry_enabled(args):
                        assert raw_point_count is not None
                        assert raw_point_bytes is not None
                        assert geometry_filter_stats is not None
                        sensor_payload = encode_dual_cloud_sensor_payload(
                            DualCloudSensorFrameV1(
                                body_position=tuple(body_position_values),
                                body_quaternion_xyzw=quaternion_wxyz_to_xyzw(
                                    body_quaternion_wxyz_values
                                ),
                                sensor_position=tuple(sensor_position_values),
                                sensor_quaternion_xyzw=quaternion_wxyz_to_xyzw(
                                    sensor_quaternion_values
                                ),
                                config_sha256=config_sha256,
                                scan_id=mid360_scan_index + 1,
                                raw_point_count=raw_point_count,
                                raw_points_xyz_f32_be=raw_point_bytes,
                                planner_point_count=point_count,
                                planner_points_xyz_f32_be=point_bytes,
                                filtered_ground_point_count=geometry_filter_stats[
                                    "filtered_ground_hit_count"
                                ],
                                conservative_retained_point_count=geometry_filter_stats[
                                    "sparse_retained_hit_count"
                                ],
                            )
                        )
                        sensor_message_type = MessageType.SENSOR_FRAME_DUAL_CLOUD_V1
                    else:
                        sensor_payload = encode_sensor_payload(SensorFrameV1(
                            body_position=tuple(body_position_values),
                            body_quaternion_xyzw=quaternion_wxyz_to_xyzw(
                                body_quaternion_wxyz_values
                            ),
                            sensor_position=tuple(sensor_position_values),
                            sensor_quaternion_xyzw=quaternion_wxyz_to_xyzw(
                                sensor_quaternion_values
                            ),
                            config_sha256=config_sha256,
                            point_count=point_count,
                            points_xyz_f32_be=point_bytes,
                        ))
                        sensor_message_type = MessageType.SENSOR_FRAME_V1
                    telemetry_sequence += 1
                    sent_sensor = telemetry_server.publish(
                        encode_frame(
                            sensor_message_type,
                            telemetry_sequence,
                            sensor_timestamp_ns,
                            sensor_payload,
                        )
                    )
                    dropped_frames += int(not sent_sensor)
                    if mid360_window is not None:
                        mid360_scan_index += 1
                    joint_state_payload = encode_joint_state_payload(
                        JointStateV1(
                            names=tuple(str(name) for name in robot.joint_names),
                            positions=tuple(_tensor_list(robot.data.joint_pos[0])),
                            velocities=tuple(_tensor_list(robot.data.joint_vel[0])),
                        )
                    )
                    telemetry_sequence += 1
                    sent_joint_state = telemetry_server.publish(
                        encode_frame(
                            MessageType.JOINT_STATE_V1,
                            telemetry_sequence,
                            sensor_timestamp_ns,
                            joint_state_payload,
                        )
                    )
                    dropped_frames += int(not sent_joint_state)
                    flags = 0
                    if contact_count >= 2:
                        flags |= int(StatusFlag.CONTACT_SUPPORTED)
                    if nonfoot_max >= args.collision_force_threshold:
                        flags |= int(StatusFlag.COLLISION)
                    if done:
                        flags |= int(StatusFlag.TERMINATED)
                    if not finite:
                        flags |= int(StatusFlag.NAN_DETECTED)
                    telemetry_sequence += 1
                    sent_status = telemetry_server.publish(
                        encode_frame(
                            MessageType.STATUS_V1,
                            telemetry_sequence,
                            int(float(base_env.sim.current_time) * 1.0e9),
                            encode_status_payload(
                                StatusV1(
                                    physics_hz=1.0 / float(base_env.physics_dt),
                                    policy_hz=1.0 / float(base_env.step_dt),
                                    sensor_hz=1.0 / args.sensor_period,
                                    bridge_latency_ms=command_age_ms,
                                    contact_count=contact_count,
                                    dropped_frames=dropped_frames,
                                    watchdog_events=snapshot.watchdog_events,
                                    flags=flags,
                                    termination_code=1 if done else 0,
                                )
                            ),
                        )
                    )
                    dropped_frames += int(not sent_status)
                if video_writer is not None and step % args.video_frame_stride == 0:
                    first_fallback_reason = None
                    if _office_enabled(args):
                        root_pos = robot.data.root_pos_w[0]
                        root_quat = robot.data.root_quat_w[0]
                        w = float(root_quat[0])
                        x = float(root_quat[1])
                        y = float(root_quat[2])
                        z = float(root_quat[3])
                        yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
                        rx, ry, rz = float(root_pos[0]), float(root_pos[1]), float(root_pos[2])
                        if review_first_view_pose is None:
                            raise AdapterFailure(
                                "Office preserved first-view pose is unavailable"
                            )
                        cam_eye, cam_target = review_first_view_pose(
                            rx, ry, rz, yaw
                        )
                        base_env.sim.set_camera_view(eye=cam_eye, target=cam_target)
                    if review_viewport_camera is not None:
                        with Usd.EditContext(
                            viewport_stage, viewport_stage.GetSessionLayer()
                        ):
                            focal_applied = review_viewport_camera.GetFocalLengthAttr().Set(
                                review_default_focal_length_mm
                            )
                            aperture_applied = (
                                review_viewport_camera.GetHorizontalApertureAttr().Set(
                                    review_default_horizontal_aperture_mm
                                )
                            )
                        if not focal_applied or not aperture_applied:
                            raise AdapterFailure(
                                "Office preserved first-view lens could not be authored"
                            )
                        first_observed_focal_length_mm = float(
                            review_viewport_camera.GetFocalLengthAttr().Get()
                        )
                        first_observed_horizontal_aperture_mm = float(
                            review_viewport_camera.GetHorizontalApertureAttr().Get()
                        )
                    if review_render_frame is None:
                        raise AdapterFailure("Office shared review renderer is unavailable")
                    video_frame = review_render_frame()
                    first_view_eye = cam_eye if _office_enabled(args) else None
                    first_view_target = cam_target if _office_enabled(args) else None
                    if _office_enabled(args) and not _rgb_scene_content(video_frame)["passed"]:
                        fallback_eye = (
                            rx - 1.2 * math.cos(yaw),
                            ry - 1.2 * math.sin(yaw),
                            min(max(rz + 2.40, 2.40), 2.90),
                        )
                        fallback_target = (rx, ry, rz + 0.10)
                        base_env.sim.set_camera_view(
                            eye=fallback_eye, target=fallback_target
                        )
                        video_frame = review_render_frame()
                        if not _rgb_scene_content(video_frame)["passed"]:
                            import cv2

                            rejected_frame_path = (
                                args.office_review_camera_trace_path.parent
                                / "first_view_rejected_frame.png"
                            )
                            if not rejected_frame_path.exists() and not rejected_frame_path.is_symlink():
                                cv2.imwrite(
                                    str(rejected_frame_path),
                                    cv2.cvtColor(video_frame, cv2.COLOR_RGB2BGR),
                                )
                            raise AdapterFailure(
                                "preserved first-view content gate failed; "
                                f"evidence={rejected_frame_path}"
                            )
                        first_fallback_reason = "content_gate_high_chase"
                        first_view_eye = fallback_eye
                        first_view_target = fallback_target
                        video_camera_fallback_sim_times.append(
                            float(base_env.sim.current_time)
                        )
                    video_writer.append_data(video_frame)
                    # --- Multi-Camera External Observers (same step, no env.step()) ---
                    sim_dt = float(base_env.step_dt) * args.video_frame_stride
                    side_desired_eye = (0.0, 0.0, 0.0)
                    side_desired_target = (0.0, 0.0, 0.0)
                    side_eye_disp = 0.0
                    side_tgt_disp = 0.0
                    side_max_allowed_eye = 0.0
                    side_max_allowed_tgt = 0.0
                    side_camera_cfg = review_side_camera_cfg or {}
                    if third_person_video_writer is not None and _office_enabled(args):
                        side_desired_eye, side_desired_target = review_side_desired_pose(
                            rx, ry, rz, yaw, side_camera_cfg,
                        )
                        if third_person_eye is None:
                            third_person_eye = side_desired_eye
                            third_person_target = side_desired_target
                            side_eye_disp = 0.0
                            side_tgt_disp = 0.0
                            side_max_allowed_eye = 0.0
                            side_max_allowed_tgt = 0.0
                        else:
                            (
                                third_person_eye,
                                third_person_target,
                                side_eye_disp,
                                side_tgt_disp,
                                side_max_allowed_eye,
                                side_max_allowed_tgt,
                            ) = review_smooth_pose_bounded(
                                third_person_eye,
                                third_person_target,
                                side_desired_eye,
                                side_desired_target,
                                dt=sim_dt,
                                smoothing_rate=float(side_camera_cfg["smoothing_rate"]),
                                max_eye_speed=float(side_camera_cfg["max_eye_speed_mps"]),
                                max_target_speed=float(side_camera_cfg["max_target_speed_mps"]),
                            )
                        # Render without advancing simulation. Ceiling actors
                        # are hidden only for this high-oblique presentation
                        # frame, then restored before any other view or step.
                        if review_viewport_camera is None:
                            raise AdapterFailure("Office side camera lens is unavailable")
                        base_env.sim.set_camera_view(
                            eye=third_person_eye, target=third_person_target
                        )
                        with Usd.EditContext(
                            viewport_stage, viewport_stage.GetSessionLayer()
                        ):
                            focal_applied = review_viewport_camera.GetFocalLengthAttr().Set(
                                float(side_camera_cfg["focal_length_mm"])
                            )
                            aperture_applied = (
                                review_viewport_camera.GetHorizontalApertureAttr().Set(
                                    review_default_horizontal_aperture_mm
                                )
                            )
                        if not focal_applied or not aperture_applied:
                            raise AdapterFailure(
                                "Office side camera lens could not be authored"
                            )
                        side_observed_focal_length_mm = float(
                            review_viewport_camera.GetFocalLengthAttr().Get()
                        )
                        if abs(
                            side_observed_focal_length_mm
                            - float(side_camera_cfg["focal_length_mm"])
                        ) > 1.0e-2:
                            raise AdapterFailure(
                                "Office side camera focal length did not apply: "
                                f"requested={side_camera_cfg['focal_length_mm']}, "
                                f"observed={side_observed_focal_length_mm}"
                            )
                        tp_frame = review_render_frame()
                        side_content = _rgb_scene_content(tp_frame)
                        if not side_content["passed"]:
                            import cv2

                            rejected_frame_path = (
                                args.office_review_camera_trace_path.parent
                                / "side_render_rejected_frame.png"
                            )
                            if rejected_frame_path.exists() or rejected_frame_path.is_symlink():
                                raise AdapterFailure(
                                    f"Office rejected-frame evidence already exists: {rejected_frame_path}"
                                )
                            if not cv2.imwrite(
                                str(rejected_frame_path),
                                cv2.cvtColor(tp_frame, cv2.COLOR_RGB2BGR),
                            ):
                                raise AdapterFailure(
                                    "Office rejected side frame could not be written"
                                )
                            side_content["rejected_frame_path"] = str(
                                rejected_frame_path
                            )
                            raise AdapterFailure(
                                f"side-follow camera content gate failed: {side_content}"
                            )
                        third_person_video_writer.append_data(tp_frame)

                    overview_desired_eye = (0.0, 0.0, 0.0)
                    overview_desired_target = (0.0, 0.0, 0.0)
                    overview_eye_disp = 0.0
                    overview_tgt_disp = 0.0
                    overview_max_allowed_eye = 0.0
                    overview_max_allowed_tgt = 0.0
                    overview_camera_cfg = review_overview_camera_cfg or {}
                    if overview_video_writer is not None and _office_enabled(args):
                        overview_desired_eye, overview_desired_target = review_overview_desired_pose(
                            rx, ry, rz, yaw, overview_camera_cfg,
                        )
                        if overview_eye is None:
                            overview_eye = overview_desired_eye
                            overview_target = overview_desired_target
                            overview_eye_disp = 0.0
                            overview_tgt_disp = 0.0
                            overview_max_allowed_eye = 0.0
                            overview_max_allowed_tgt = 0.0
                        else:
                            (
                                overview_eye,
                                overview_target,
                                overview_eye_disp,
                                overview_tgt_disp,
                                overview_max_allowed_eye,
                                overview_max_allowed_tgt,
                            ) = review_smooth_pose_bounded(
                                overview_eye,
                                overview_target,
                                overview_desired_eye,
                                overview_desired_target,
                                dt=sim_dt,
                                smoothing_rate=float(overview_camera_cfg["smoothing_rate"]),
                                max_eye_speed=float(overview_camera_cfg["max_eye_speed_mps"]),
                                max_target_speed=float(overview_camera_cfg["max_target_speed_mps"]),
                            )
                        # Restore the original viewport lens for the overview.
                        if review_viewport_camera is None:
                            raise AdapterFailure("Office overview camera lens is unavailable")
                        base_env.sim.set_camera_view(
                            eye=overview_eye, target=overview_target
                        )
                        with Usd.EditContext(
                            viewport_stage, viewport_stage.GetSessionLayer()
                        ):
                            focal_applied = review_viewport_camera.GetFocalLengthAttr().Set(
                                review_default_focal_length_mm
                            )
                            aperture_applied = (
                                review_viewport_camera.GetHorizontalApertureAttr().Set(
                                    review_default_horizontal_aperture_mm
                                )
                            )
                        if not focal_applied or not aperture_applied:
                            raise AdapterFailure(
                                "Office overview camera lens could not be authored"
                            )
                        overview_observed_focal_length_mm = float(
                            review_viewport_camera.GetFocalLengthAttr().Get()
                        )
                        over_frame = review_render_frame()
                        overview_content = _rgb_scene_content(over_frame)
                        if not overview_content["passed"]:
                            raise AdapterFailure(
                                f"overview camera content gate failed: {overview_content}"
                            )
                        overview_video_writer.append_data(over_frame)

                    # Record multi-view camera trace
                    if camera_trace_handle is not None and _office_enabled(args):
                        run_id_val = identity["config_sha256"]
                        snapshot_id = review_state_snapshot_identity(
                            step,
                            float(base_env.sim.current_time),
                            [rx, ry, rz],
                            [w, x, y, z],
                        )
                        trace_data = review_camera_trace_row(
                            frame_index=video_frame_count,
                            step=step,
                            sim_time_seconds=float(base_env.sim.current_time),
                            run_identity=run_id_val,
                            root_pos_w=[rx, ry, rz],
                            root_quat_w=[w, x, y, z],
                            first_eye=list(first_view_eye) if first_view_eye else [0, 0, 0],
                            first_target=list(first_view_target) if first_view_target else [0, 0, 0],
                            side_desired_eye=list(side_desired_eye),
                            side_desired_target=list(side_desired_target),
                            side_realized_eye=list(third_person_eye) if third_person_eye else [0, 0, 0],
                            side_realized_target=list(third_person_target) if third_person_target else [0, 0, 0],
                            side_config=side_camera_cfg,
                            overview_desired_eye=list(overview_desired_eye),
                            overview_desired_target=list(overview_desired_target),
                            overview_realized_eye=list(overview_eye) if overview_eye else [0, 0, 0],
                            overview_realized_target=list(overview_target) if overview_target else [0, 0, 0],
                            overview_config=overview_camera_cfg,
                            dt=sim_dt,
                            side_eye_displacement=side_eye_disp,
                            side_target_displacement=side_tgt_disp,
                            side_max_allowed_eye_displacement=side_max_allowed_eye,
                            side_max_allowed_target_displacement=side_max_allowed_tgt,
                            overview_eye_displacement=overview_eye_disp,
                            overview_target_displacement=overview_tgt_disp,
                            overview_max_allowed_eye_displacement=overview_max_allowed_eye,
                            overview_max_allowed_target_displacement=overview_max_allowed_tgt,
                            first_fallback_reason=first_fallback_reason,
                            renderer_settings=review_capture_profile,
                            snapshot_identity=snapshot_id,
                        )
                        trace_data["first_view"]["focal_length_mm"] = float(
                            first_observed_focal_length_mm
                        )
                        trace_data["first_view"]["horizontal_aperture_mm"] = float(
                            first_observed_horizontal_aperture_mm
                        )
                        trace_data["first_view"]["horizontal_fov_degrees"] = math.degrees(
                            2.0
                            * math.atan(
                                first_observed_horizontal_aperture_mm
                                / (2.0 * first_observed_focal_length_mm)
                            )
                        )
                        trace_data["first_view"]["render_cutaway"] = dict(
                            review_cutaway_audit or {}
                        )
                        trace_data["side_follow"]["focal_length_mm"] = float(
                            side_observed_focal_length_mm
                        )
                        trace_data["side_follow"]["render_cutaway"] = dict(
                            review_cutaway_audit or {}
                        )
                        trace_data["overview"]["focal_length_mm"] = float(
                            overview_observed_focal_length_mm
                        )
                        trace_data["overview"]["render_cutaway"] = dict(
                            review_cutaway_audit or {}
                        )
                        camera_trace_handle.write(
                            json.dumps(trace_data) + "\n"
                        )
                        camera_trace_handle.flush()
                    video_frame_count += 1
                if done or not finite:
                    raise AdapterFailure("V12 fallback terminated or became non-finite")
                step += 1
                next_tick += float(base_env.step_dt)
                time.sleep(max(0.0, next_tick - time.monotonic()))
                if time.monotonic() - tick_started > max_step_wall_seconds:
                    raise AdapterFailure("V12 simulation step exceeded wall-time safety limit")
    except BaseException as error:
        runtime_error = error
    finally:
        if sender is not None:
            sender.stop()
        command_server.stop()
        if sink is not None:
            sink.stop()
        telemetry_server.stop()
        if video_writer is not None:
            try:
                video_writer.close()
            except BaseException as error:
                if runtime_error is None:
                    runtime_error = error
        if third_person_video_writer is not None:
            try:
                third_person_video_writer.close()
            except BaseException as error:
                if runtime_error is None:
                    runtime_error = error
        if overview_video_writer is not None:
            try:
                overview_video_writer.close()
            except BaseException as error:
                if runtime_error is None:
                    runtime_error = error
        if camera_trace_handle is not None:
            try:
                camera_trace_handle.close()
            except BaseException:  # noqa: BLE001
                pass
        if wrapped_env is not None:
            wrapped_env.close()
        elif raw_env is not None:
            raw_env.close()

    if sink is not None and sink.error is not None and runtime_error is None:
        runtime_error = sink.error
    depth_artifact_metadata = None
    if sensor_rig and best_depth_frame is not None and best_depth_metadata is not None:
        try:
            depth_artifact_metadata = _write_depth_artifacts(
                output_dir,
                best_depth_frame,
                best_depth_metadata,
                args.depth_max_range,
            )
        except BaseException as error:
            if runtime_error is None:
                runtime_error = error
    sink_snapshot = sink.snapshot() if sink is not None else {}
    if args.mode == "external":
        external_checks = {
            "records_present": bool(records),
            "no_termination": bool(records) and not any(row["done"] for row in records),
            "finite_policy": bool(records) and all(row["finite"] for row in records),
            "command_connected": command_server.stats().accepted_connections > 0,
            "commands_received": command_server.stats().frames_received > 0,
            "telemetry_connected": telemetry_server.stats().accepted_connections > 0,
            "telemetry_sent": telemetry_server.stats().frames_sent > 0,
        }
        if _forest_navigation_enabled(args):
            navigation = forest_layout["identity"]["navigation"]
            external_checks.update(
                {
                    "forest_static_geometry": bool(
                        static_forest_geometry_checks
                        and static_forest_geometry_checks["passed"]
                    ),
                    "direct_path_blocked": bool(
                        navigation["direct_path_intersects_inflated_blocker"]
                    ),
                    "geometry_filter_active": bool(sensor_records)
                    and all(
                        row["planner_geometry_filter_enabled"]
                        for row in sensor_records
                    ),
                    "geometry_filter_removed_terrain": bool(sensor_records)
                    and max(
                        row["planner_geometry_filter_ground_hit_count"]
                        for row in sensor_records
                    )
                    > 0,
                }
            )
        if dynamic_obstacle is not None:
            dynamic_actual_positions = [
                row["dynamic_obstacle_actual_pos_w"] for row in records
            ]
            dynamic_travel = (
                math.dist(dynamic_actual_positions[0], dynamic_actual_positions[-1])
                if len(dynamic_actual_positions) >= 2
                else 0.0
            )
            external_checks.update(
                {
                    "dynamic_obstacle_geometry": bool(
                        dynamic_obstacle_geometry_checks
                        and dynamic_obstacle_geometry_checks["passed"]
                    ),
                    "dynamic_obstacle_motion": dynamic_travel
                    >= 0.90 * math.dist(dynamic_spec.start_xy, dynamic_spec.end_xy),
                    "dynamic_obstacle_pose_readback": bool(records)
                    and max(
                        row["dynamic_obstacle_pose_error_m"] for row in records
                    )
                    <= 0.05,
                    "dynamic_obstacle_terrain_clearance": bool(records)
                    and min(
                        row["dynamic_obstacle_bottom_clearance_m"]
                        for row in records
                    )
                    >= dynamic_spec.terrain_clearance_m - 0.01,
                    "dynamic_obstacle_lidar_observed": bool(sensor_records)
                    and max(
                        row.get("dynamic_obstacle_surface_hit_count", 0)
                        for row in sensor_records
                    )
                    > 0,
                    "dynamic_obstacle_depth_observed": bool(depth_records)
                    and max(
                        row.get("dynamic_obstacle_surface_pixel_count", 0)
                        for row in depth_records
                    )
                    > 0,
                }
            )
        report = {
            "schema_version": 1,
            "status": "PASS" if all(external_checks.values()) else "FAIL",
            "claim": "external bridge runtime only; closed-loop goal result evaluated separately",
            "checks": external_checks,
            "command_transport": command_server.stats().__dict__,
            "telemetry_transport": telemetry_server.stats().__dict__,
            "record_count": len(records),
            "static_geometry_checks": static_forest_geometry_checks,
            "dynamic_obstacle_geometry_checks": dynamic_obstacle_geometry_checks,
            "forest_navigation": (
                None
                if forest_layout is None
                else forest_layout["identity"].get("navigation")
            ),
        }
    elif forest_layout is not None:
        report = _forest_preview_report(
            records,
            sink_snapshot,
            command_server.stats(),
            telemetry_server.stats(),
            static_forest_geometry_checks,
        )
    else:
        report = _qualification_report(
            records, sink_snapshot, command_server.stats(), telemetry_server.stats()
        )
    sensor_checks, sensor_passed = _sensor_gate(sensor_records)
    report["sensor_checks"] = sensor_checks
    depth_checks, depth_passed = _depth_gate(depth_records)
    report["depth_checks"] = depth_checks
    report["depth_artifact"] = depth_artifact_metadata
    report["runtime_rates"] = runtime_rates
    if args.video_path is not None:
        report["video"] = {
            "path": str(args.video_path),
            "frame_count": video_frame_count,
            "fps": args.video_fps,
            "encoded_duration_seconds": video_frame_count / args.video_fps,
            "camera_occlusion_fallback_frame_count": len(
                video_camera_fallback_sim_times
            ),
            "camera_occlusion_fallback_sim_times": video_camera_fallback_sim_times,
            "bytes": args.video_path.stat().st_size if args.video_path.is_file() else 0,
            "sha256": _sha256(args.video_path) if args.video_path.is_file() else None,
        }
    side_v_path = _office_review_side_video_path(args)
    over_v_path = _office_review_overview_video_path(args)
    ros_events_snapshot_path = None

    if _office_review_presentation_enabled(args):
        from .office_review_presentation import (
            render_office_review_dashboard,
            validate_office_review_presentation,
            write_text_exclusive,
        )
        if (
            args.video_path is not None
            and args.video_path.is_file()
            and side_v_path is not None
            and side_v_path.is_file()
            and over_v_path is not None
            and over_v_path.is_file()
            and args.office_review_camera_trace_path is not None
            and args.office_review_camera_trace_path.is_file()
            and args.office_review_material_audit_path is not None
            and args.office_review_material_audit_path.is_file()
            and args.office_review_dashboard_video_path is not None
            and args.office_review_dashboard_metadata_path is not None
        ):
            try:
                ros_events_file = output_dir.parent / "ros_events.jsonl"
                ros_events_live = ros_events_file if ros_events_file.is_file() else (output_dir / "ros_events.jsonl")
                if not ros_events_live.is_file():
                    raise FileNotFoundError(f"live ROS event evidence is missing: {ros_events_live}")
                # The ROS monitor remains alive until qualification_report.json
                # appears, so its live JSONL can be flushed after dashboard
                # encoding. Freeze complete event rows first and use only this
                # immutable run-owned snapshot for rendering and validation.
                live_text = ros_events_live.read_text(encoding="utf-8")
                complete_lines = live_text.splitlines()
                if live_text and not live_text.endswith("\n"):
                    complete_lines = complete_lines[:-1]
                snapshot_rows = []
                for line_number, line in enumerate(complete_lines, 1):
                    if not line.strip():
                        continue
                    try:
                        snapshot_rows.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            f"ROS event row {line_number} is malformed during snapshot"
                        ) from exc
                if not snapshot_rows:
                    raise ValueError("ROS event snapshot cannot be empty")
                ros_events_snapshot_path = output_dir.parent / "office_review_ros_events_snapshot.jsonl"
                write_text_exclusive(
                    ros_events_snapshot_path,
                    "".join(json.dumps(row, sort_keys=True) + "\n" for row in snapshot_rows),
                )
                ros_events_target = ros_events_snapshot_path
                metrics_target = output_dir / "metrics.jsonl"
                run_identity_target = output_dir / "run_identity.json"

                render_office_review_dashboard(
                    first_video_path=args.video_path,
                    side_video_path=side_v_path,
                    overview_video_path=over_v_path,
                    camera_trace_path=args.office_review_camera_trace_path,
                    material_audit_path=args.office_review_material_audit_path,
                    ros_events_path=ros_events_target,
                    metrics_path=metrics_target,
                    run_identity_path=run_identity_target,
                    effective_input_path=args.office_review_effective_input_path,
                    acceptance_config_path=args.acceptance_config,
                    output_dashboard_video_path=args.office_review_dashboard_video_path,
                    output_dashboard_metadata_path=args.office_review_dashboard_metadata_path,
                )
                val_res = validate_office_review_presentation(
                    first_video_path=args.video_path,
                    side_video_path=side_v_path,
                    overview_video_path=over_v_path,
                    camera_trace_path=args.office_review_camera_trace_path,
                    material_audit_path=args.office_review_material_audit_path,
                    dashboard_video_path=args.office_review_dashboard_video_path,
                    dashboard_metadata_path=args.office_review_dashboard_metadata_path,
                    ros_events_path=ros_events_target,
                    metrics_path=metrics_target,
                    run_identity_path=run_identity_target,
                    effective_input_path=args.office_review_effective_input_path,
                    acceptance_config_path=args.acceptance_config,
                )
                write_text_exclusive(
                    args.office_review_validation_report_path,
                    json.dumps(val_res, indent=2),
                )
                report["office_review_presentation"] = {
                    "rendered": True,
                    "validated": val_res["passed"],
                    "validation_report": val_res,
                }
                if not val_res["passed"]:
                    report["status"] = "FAIL"
            except Exception as e:
                failure_validation = {
                    "passed": False,
                    "issues": [f"presentation packaging exception: {type(e).__name__}: {e}"],
                    "checks": {},
                }
                if (
                    args.office_review_validation_report_path is not None
                    and not os.path.lexists(args.office_review_validation_report_path)
                ):
                    write_text_exclusive(
                        args.office_review_validation_report_path,
                        json.dumps(failure_validation, indent=2),
                    )
                report["office_review_presentation"] = {
                    "rendered": False,
                    "validated": False,
                    "error": str(e),
                    "validation_report": failure_validation,
                }
                report["status"] = "FAIL"

    # Multi-view video and metadata report entries
    if side_v_path is not None and side_v_path.is_file():
        report["third_person_side_video"] = {
            "path": str(side_v_path),
            "frame_count": video_frame_count,
            "fps": args.video_fps,
            "encoded_duration_seconds": video_frame_count / args.video_fps,
            "bytes": side_v_path.stat().st_size,
            "sha256": _sha256(side_v_path),
        }
    if over_v_path is not None and over_v_path.is_file():
        report["overview_video"] = {
            "path": str(over_v_path),
            "frame_count": video_frame_count,
            "fps": args.video_fps,
            "encoded_duration_seconds": video_frame_count / args.video_fps,
            "bytes": over_v_path.stat().st_size,
            "sha256": _sha256(over_v_path),
        }
    if (
        args.office_review_camera_trace_path is not None
        and args.office_review_camera_trace_path.is_file()
    ):
        report["camera_trace"] = {
            "path": str(args.office_review_camera_trace_path),
            "frame_count": video_frame_count,
            "sha256": _sha256(args.office_review_camera_trace_path),
        }
    if (
        getattr(args, "office_review_material_audit_path", None) is not None
        and args.office_review_material_audit_path.is_file()
    ):
        report["material_audit"] = {
            "path": str(args.office_review_material_audit_path),
            "sha256": _sha256(args.office_review_material_audit_path),
        }
    if (
        getattr(args, "office_review_dashboard_video_path", None) is not None
        and args.office_review_dashboard_video_path.is_file()
    ):
        report["dashboard_video"] = {
            "path": str(args.office_review_dashboard_video_path),
            "bytes": args.office_review_dashboard_video_path.stat().st_size,
            "sha256": _sha256(args.office_review_dashboard_video_path),
        }
    if (
        getattr(args, "office_review_dashboard_metadata_path", None) is not None
        and args.office_review_dashboard_metadata_path.is_file()
    ):
        report["dashboard_metadata"] = {
            "path": str(args.office_review_dashboard_metadata_path),
            "sha256": _sha256(args.office_review_dashboard_metadata_path),
        }
    if (
        getattr(args, "office_review_validation_report_path", None) is not None
        and args.office_review_validation_report_path.is_file()
    ):
        report["presentation_validation_report"] = {
            "path": str(args.office_review_validation_report_path),
            "sha256": _sha256(args.office_review_validation_report_path),
        }
    if ros_events_snapshot_path is not None and ros_events_snapshot_path.is_file():
        report["presentation_ros_events_snapshot"] = {
            "path": str(ros_events_snapshot_path),
            "sha256": _sha256(ros_events_snapshot_path),
        }
    if args.mode == "sensor_qualification" and not sensor_passed:
        report["status"] = "FAIL"
    if sensor_rig and (not sensor_passed or not depth_passed):
        report["status"] = "FAIL"
    report["candidate"] = _candidate_name(args)
    report["runtime_error"] = None if runtime_error is None else {
        "type": type(runtime_error).__name__,
        "message": str(runtime_error),
    }
    if runtime_error is not None:
        report["status"] = "INSTRUMENTATION_ERROR"
    _write_json(output_dir / "qualification_report.json", report)
    print(json.dumps({"status": report["status"], "output_dir": str(output_dir)}), flush=True)
    return 0 if report["status"] == "PASS" else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("qualification", "sensor_qualification", "external"),
        default="qualification",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--vendored-rsl-rl", type=Path, required=True)
    parser.add_argument(
        "--robot-asset",
        type=Path,
        help="Pinned Isaac-safe Lite3 Pro sensor-rig URDF for the v3 composition",
    )
    parser.add_argument(
        "--canonical-robot-asset",
        type=Path,
        help="Canonical pre-Isaac sensor-rig URDF used to prove asset lineage",
    )
    parser.add_argument("--source-commit", default=PINNED_SOURCE_COMMIT)
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument(
        "--course",
        choices=(
            "flat",
            "single_box",
            "forest_gen",
            "forest_gen_nav",
            "forest_gen_nav_v6",
            "forest_gen_nav_v7_dynamic",
            "forest_gen_nav_v8_human",
            "forest_gen_nav_v8_official_human",
            "office_l0_static",
            "office_l0_crowd",
        ),
        default="flat",
    )
    parser.add_argument(
        "--office-usd-path",
        type=Path,
        help="Run-owned Office L0 source-mesh physics wrapper USD.",
    )
    parser.add_argument(
        "--office-usd-sha256",
        help="Required SHA-256 of --office-usd-path for the Office course.",
    )
    parser.add_argument("--office-route-path", type=Path)
    parser.add_argument("--office-route-sha256")
    parser.add_argument(
        "--office-pedestrian-motion-mode",
        choices=("single_pass", "background_ping_pong", "ping_pong"),
        default="single_pass",
        help=(
            "Office crowd root-motion schedule. background_ping_pong keeps the "
            "two route-crossing events single-pass while repeating only the six "
            "background routes; ping_pong repeats every frozen route."
        ),
    )
    parser.add_argument(
        "--office-pedestrian-turnaround-hold-seconds",
        type=float,
        default=0.0,
        help="Idle interval used to turn smoothly at each ping-pong endpoint.",
    )
    parser.add_argument("--office-start-xy", type=float, nargs=2)
    parser.add_argument("--office-start-yaw", type=float, default=-0.6435)
    parser.add_argument("--office-goal-xy", type=float, nargs=2)
    parser.add_argument("--forest-gen-root", type=Path)
    parser.add_argument("--stripe-kit-root", type=Path)
    parser.add_argument("--forest-asset-path", type=Path)
    parser.add_argument(
        "--official-human-animation-cache",
        type=Path,
        help=(
            "Runtime-generated NVIDIA Biped AnimationGraph retarget cache; "
            "required only by forest_gen_nav_v8_official_human"
        ),
    )
    parser.add_argument(
        "--official-human-animation-mode",
        choices=("phase_conditioned", "continuous_walk"),
        default="phase_conditioned",
        help=(
            "Official-human clip selection. continuous_walk loops the official "
            "walk clip even while the physical obstacle is stationary."
        ),
    )
    parser.add_argument("--forest-size", type=int, default=FOREST_SIZE_M)
    parser.add_argument("--forest-margin", type=int, default=FOREST_MARGIN_M)
    parser.add_argument("--forest-seed", type=int, default=FOREST_SEED)
    parser.add_argument(
        "--dynamic-obstacle-x",
        type=float,
        default=DYNAMIC_OBSTACLE_DEFAULT_X_M,
    )
    parser.add_argument(
        "--dynamic-obstacle-end-x",
        type=float,
        default=None,
        help="Optional endpoint x coordinate; omitted preserves a vertical route.",
    )
    parser.add_argument(
        "--dynamic-obstacle-start-y",
        type=float,
        default=DYNAMIC_OBSTACLE_DEFAULT_START_Y_M,
    )
    parser.add_argument(
        "--dynamic-obstacle-end-y",
        type=float,
        default=DYNAMIC_OBSTACLE_DEFAULT_END_Y_M,
    )
    parser.add_argument(
        "--dynamic-obstacle-wait-seconds",
        type=float,
        default=DYNAMIC_OBSTACLE_DEFAULT_WAIT_SECONDS,
    )
    parser.add_argument(
        "--dynamic-obstacle-schedule-trigger",
        choices=("first_nonzero_body_command", "run_start"),
        default="first_nonzero_body_command",
        help=(
            "Start the moving-obstacle schedule at the first accepted nonzero "
            "robot command, or immediately when the closed-loop run begins."
        ),
    )
    parser.add_argument(
        "--dynamic-obstacle-speed",
        type=float,
        default=DYNAMIC_OBSTACLE_DEFAULT_SPEED_MPS,
    )
    parser.add_argument(
        "--dynamic-obstacle-radius",
        type=float,
        default=DYNAMIC_OBSTACLE_DEFAULT_RADIUS_M,
    )
    parser.add_argument(
        "--dynamic-obstacle-height",
        type=float,
        default=DYNAMIC_OBSTACLE_DEFAULT_HEIGHT_M,
    )
    parser.add_argument(
        "--dynamic-obstacle-terrain-clearance",
        type=float,
        default=DYNAMIC_OBSTACLE_DEFAULT_TERRAIN_CLEARANCE_M,
    )
    parser.add_argument(
        "--dynamic-obstacle-hold-fraction",
        type=float,
        default=DYNAMIC_OBSTACLE_DEFAULT_HOLD_FRACTION,
    )
    parser.add_argument(
        "--dynamic-obstacle-hold-seconds",
        type=float,
        default=DYNAMIC_OBSTACLE_DEFAULT_HOLD_SECONDS,
    )
    parser.add_argument("--duration-seconds", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--command-host", default="127.0.0.1")
    parser.add_argument("--command-port", type=int, default=46001)
    parser.add_argument("--telemetry-host", default="127.0.0.1")
    parser.add_argument("--telemetry-port", type=int, default=46000)
    parser.add_argument(
        "--cloud-profile",
        choices=("legacy_planner_v1", "upstream_go2_reference"),
        default="legacy_planner_v1",
        help="Select legacy single-cloud or atomic raw/planning cloud telemetry.",
    )
    parser.add_argument("--max-vx", type=float, default=0.75)
    parser.add_argument("--max-vy", type=float, default=0.35)
    parser.add_argument("--max-wz", type=float, default=1.0)
    parser.add_argument("--watchdog-seconds", type=float, default=0.25)
    parser.add_argument("--sensor-period", type=float, default=0.10)
    parser.add_argument("--sensor-translation", type=float, nargs=3, default=(0.182399336, 0.0, 0.108541081))
    parser.add_argument("--sensor-pitch-degrees", type=float, default=15.0)
    parser.add_argument(
        "--lidar-pattern-mode",
        choices=("uniform", "livox_mid360"),
        default="uniform",
        help="Opt-in source-backed Livox pattern; uniform preserves legacy runs.",
    )
    parser.add_argument(
        "--lidar-pattern-csv",
        type=Path,
        help="Pinned Livox mid360.csv; required only for livox_mid360 mode.",
    )
    parser.add_argument("--lidar-channels", type=int, default=16)
    parser.add_argument("--lidar-vertical-min", type=float, default=-7.0)
    parser.add_argument("--lidar-vertical-max", type=float, default=52.0)
    parser.add_argument("--lidar-horizontal-resolution", type=float, default=2.0)
    parser.add_argument("--lidar-min-range", type=float, default=0.10)
    parser.add_argument("--lidar-max-range", type=float, default=12.0)
    parser.add_argument("--depth-period", type=float, default=0.10)
    parser.add_argument("--depth-width", type=int, default=87)
    parser.add_argument("--depth-height", type=int, default=58)
    parser.add_argument("--depth-focal-length", type=float, default=24.0)
    parser.add_argument("--depth-horizontal-aperture", type=float, default=45.55)
    parser.add_argument("--depth-min-range", type=float, default=0.10)
    parser.add_argument("--depth-max-range", type=float, default=5.0)
    parser.add_argument("--planner-floor-filter-max-z", type=float, default=0.05)
    parser.add_argument("--terrain-filter-cell-size", type=float, default=0.30)
    parser.add_argument(
        "--terrain-filter-height-threshold", type=float, default=0.22
    )
    parser.add_argument("--terrain-filter-neighbor-cells", type=int, default=1)
    parser.add_argument(
        "--terrain-filter-minimum-neighbor-cells", type=int, default=2
    )
    parser.add_argument("--video-path", type=Path)
    parser.add_argument("--video-fps", type=int, default=25)
    parser.add_argument("--video-frame-stride", type=int, default=2)
    parser.add_argument(
        "--office-review-presentation",
        action="store_true",
        default=False,
        help="Enable full 4-panel 3D review presentation pipeline for Office L0.",
    )
    parser.add_argument(
        "--office-review-third-person-side-video-path",
        type=Path,
        default=None,
        help="Opt-in path for external side-follow third-person video (closed_loop_third_person_side.mp4).",
    )
    parser.add_argument(
        "--office-review-third-person-video-path",
        type=Path,
        default=None,
        help="Backward-compatible alias for --office-review-third-person-side-video-path.",
    )
    parser.add_argument(
        "--office-review-overview-video-path",
        type=Path,
        default=None,
        help="Opt-in path for elevated wide-overview video (closed_loop_overview.mp4).",
    )
    parser.add_argument(
        "--office-review-camera-trace-path",
        type=Path,
        default=None,
        help=(
            "Path for camera_trace.jsonl recording multi-view poses per frame. "
            "Required when presentation or multi-view video is enabled."
        ),
    )
    parser.add_argument(
        "--office-review-material-audit-path",
        type=Path,
        default=None,
        help=(
            "Path for office_review_material_audit.json recording USD material override audit."
        ),
    )
    parser.add_argument(
        "--office-review-dashboard-video-path",
        type=Path,
        default=None,
        help=(
            "Path for 1920x1080 office_review_dashboard.mp4 review video."
        ),
    )
    parser.add_argument(
        "--office-review-dashboard-metadata-path",
        type=Path,
        default=None,
        help=(
            "Path for office_review_dashboard_metadata.json recording 3D projection info and SHA-256 digests."
        ),
    )
    parser.add_argument(
        "--office-review-validation-report-path",
        type=Path,
        default=None,
        help="Fresh output path for the structured presentation validation report.",
    )
    parser.add_argument(
        "--office-review-effective-input-path",
        type=Path,
        default=None,
        help="Launcher-written effective_input.txt bound into review provenance.",
    )
    parser.add_argument(
        "--office-review-launcher-path",
        type=Path,
        default=None,
        help="Task-owned launcher source hashed into review run identity.",
    )
    parser.add_argument(
        "--office-review-material",
        action="store_true",
        default=False,
        help=(
            "Apply a high-contrast review-only material override to the Lite3 "
            "visual meshes for Office human review. Does not change URDF, "
            "collision, mass, inertia, joints, or sensors."
        ),
    )
    parser.add_argument(
        "--office-review-camera-side",
        choices=("left", "right"),
        default="left",
        help="Side of the robot for the side-observer camera (left or right).",
    )
    parser.add_argument(
        "--office-review-camera-lateral-distance",
        type=float,
        default=3.0,
        help="Lateral offset of side-observer camera from robot heading (m).",
    )
    parser.add_argument(
        "--office-review-camera-trailing-bias",
        type=float,
        default=1.5,
        help="Distance behind robot for side-observer camera (m).",
    )
    parser.add_argument(
        "--office-review-camera-height",
        type=float,
        default=2.0,
        help="Height above ground for side-observer camera (m).",
    )
    parser.add_argument(
        "--office-review-camera-focal-length-mm",
        type=float,
        default=18.14756,
        help="Viewport focal length used only for the side-observer render (mm).",
    )
    parser.add_argument(
        "--office-review-camera-look-ahead",
        type=float,
        default=1.0,
        help="Look-at target distance ahead of robot heading (m).",
    )
    parser.add_argument(
        "--office-review-camera-look-height-offset",
        type=float,
        default=0.15,
        help="Look-at target height offset above robot root (m).",
    )
    parser.add_argument(
        "--office-review-camera-smoothing-rate",
        type=float,
        default=4.0,
        help="Exponential smoothing rate (1/s) for side-observer camera.",
    )
    parser.add_argument(
        "--office-review-camera-max-eye-speed",
        type=float,
        default=8.0,
        help="Maximum translation speed (m/s) for camera eye position.",
    )
    parser.add_argument(
        "--office-review-camera-max-target-speed",
        type=float,
        default=8.0,
        help="Maximum translation speed (m/s) for camera look-at target.",
    )
    parser.add_argument(
        "--office-review-overview-distance",
        type=float,
        default=6.5,
        help="Horizontal follow distance (m) for wide-overview camera.",
    )
    parser.add_argument(
        "--office-review-overview-azimuth-offset-deg",
        type=float,
        default=35.0,
        help="Azimuth angle offset (deg) relative to robot heading for overview camera.",
    )
    parser.add_argument(
        "--office-review-overview-height",
        type=float,
        default=4.5,
        help="Height above ground (m) for wide-overview camera.",
    )
    parser.add_argument(
        "--office-review-overview-look-ahead",
        type=float,
        default=2.0,
        help="Look-ahead distance (m) along robot heading for overview camera.",
    )
    parser.add_argument(
        "--office-review-overview-look-height-offset",
        type=float,
        default=0.20,
        help="Look-height offset (m) for overview camera.",
    )
    parser.add_argument(
        "--office-review-overview-smoothing-rate",
        type=float,
        default=3.0,
        help="Exponential smoothing rate (1/s) for overview camera.",
    )
    parser.add_argument(
        "--office-review-overview-max-eye-speed",
        type=float,
        default=6.0,
        help="Maximum translation speed (m/s) for overview eye.",
    )
    parser.add_argument(
        "--office-review-overview-max-target-speed",
        type=float,
        default=6.0,
        help="Maximum translation speed (m/s) for overview target.",
    )
    parser.add_argument(
        "--office-review-lighting-profile",
        choices=("default", "high_contrast"),
        default="high_contrast",
        help="Lighting preset for Office human review legibility.",
    )
    parser.add_argument(
        "--office-review-dome-light-intensity",
        type=float,
        default=1000.0,
        help="Dome light intensity for Office review.",
    )
    parser.add_argument(
        "--office-review-exposure",
        type=float,
        default=0.0,
        help="Camera exposure compensation for Office review.",
    )
    parser.add_argument("--acceptance-config", type=Path)
    parser.add_argument("--contact-force-threshold", type=float, default=5.0)
    parser.add_argument("--collision-force-threshold", type=float, default=75.0)
    parser.add_argument("--max-step-wall-seconds", type=float, default=5.0)
    parser.add_argument("--connection-ready-timeout-seconds", type=float, default=10.0)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    args.mid360_pattern_table = None
    if not args.checkpoint.is_file():
        raise SystemExit(f"required immutable checkpoint is missing: {args.checkpoint}")
    if not (args.vendored_rsl_rl / "rsl_rl" / "env" / "vec_env.py").is_file():
        raise SystemExit(
            f"required complete pinned V12 RSL-RL runtime is missing: {args.vendored_rsl_rl}"
        )
    if args.acceptance_config is not None and not args.acceptance_config.is_file():
        raise SystemExit(
            f"required frozen acceptance config is missing: {args.acceptance_config}"
        )
    if (args.robot_asset is None) != (args.canonical_robot_asset is None):
        raise SystemExit(
            "--robot-asset and --canonical-robot-asset must be supplied together"
        )
    if _official_mid360_enabled(args):
        if not _sensor_rig_enabled(args):
            raise SystemExit(
                "livox_mid360 requires the pinned Lite3 MID-360 sensor-rig URDF"
            )
        if args.lidar_pattern_csv is None:
            raise SystemExit("livox_mid360 requires --lidar-pattern-csv")
        if abs(float(args.sensor_period) - 1.0 / MID360_SCAN_HZ) > 1.0e-9:
            raise SystemExit("livox_mid360 requires a 0.1 s sensor period")
        if abs(float(args.lidar_min_range) - MID360_MIN_RANGE_M) > 1.0e-9:
            raise SystemExit("livox_mid360 requires the 0.1 m blind-zone filter")
        if abs(float(args.lidar_max_range) - MID360_MAX_RANGE_M) > 1.0e-9:
            raise SystemExit("livox_mid360 requires the conservative 40 m range")
        try:
            args.mid360_pattern_table = load_mid360_pattern(args.lidar_pattern_csv)
        except Mid360PatternError as error:
            raise SystemExit(f"invalid livox_mid360 pattern: {error}") from error
        if args.mid360_pattern_table.points_per_scan != MID360_POINTS_PER_SCAN:
            raise SystemExit(
                "livox_mid360 pattern does not produce exactly 20,000 rays per scan"
            )
    elif args.lidar_pattern_csv is not None:
        raise SystemExit(
            "--lidar-pattern-csv is valid only with --lidar-pattern-mode livox_mid360"
        )
    if _sensor_rig_enabled(args):
        if args.task != DEFAULT_TASK:
            raise SystemExit("the v3 sensor-rig composition requires the pinned V12 task")
        if not args.robot_asset.is_file():
            raise SystemExit(f"sensor-rig Isaac asset is missing: {args.robot_asset}")
        if not args.canonical_robot_asset.is_file():
            raise SystemExit(
                f"canonical sensor-rig asset is missing: {args.canonical_robot_asset}"
            )
        if _sha256(args.robot_asset) != PINNED_SENSOR_RIG_ISAAC_SHA256:
            raise SystemExit("sensor-rig Isaac asset hash mismatch")
        if (
            _sha256(args.canonical_robot_asset)
            != PINNED_SENSOR_RIG_CANONICAL_SHA256
        ):
            raise SystemExit("canonical sensor-rig asset hash mismatch")
        if abs(args.depth_period - args.sensor_period) > 1.0e-9:
            raise SystemExit("v3 lidar and depth periods must match")
        if args.depth_width <= 0 or args.depth_height <= 0:
            raise SystemExit("depth dimensions must be positive")
        if (
            args.depth_min_range < 0.0
            or args.depth_max_range <= args.depth_min_range
            or not all(
                math.isfinite(value)
                for value in (
                    args.depth_period,
                    args.depth_focal_length,
                    args.depth_horizontal_aperture,
                    args.depth_min_range,
                    args.depth_max_range,
                )
            )
        ):
            raise SystemExit("depth sensor parameters are invalid")
    if _forest_enabled(args):
        if not _sensor_rig_enabled(args):
            raise SystemExit("forest courses require the pinned V3 sensor-rig URDFs")
        if _forest_preview_enabled(args) and args.mode != "qualification":
            raise SystemExit("forest preview is a standalone qualification run")
        if (
            _forest_navigation_enabled(args)
            and args.mode != "external"
            and not (
                _forest_v8_official_enabled(args)
                and args.mode == "qualification"
            )
        ):
            raise SystemExit("forest navigation requires the external SCAN loop")
        if (
            args.forest_size != FOREST_SIZE_M
            or args.forest_margin != FOREST_MARGIN_M
            or args.forest_seed != FOREST_SEED
        ):
            raise SystemExit(
                "forest courses require the pinned size=32, margin=10, seed=14"
            )
        for name in ("forest_gen_root", "stripe_kit_root", "forest_asset_path"):
            value = getattr(args, name)
            if value is None or not value.is_dir():
                raise SystemExit(f"required forest directory is missing: {name}")
        expected_asset_root = args.forest_gen_root.resolve() / "models"
        if args.forest_asset_path.resolve() != expected_asset_root:
            raise SystemExit(
                "forest asset path must be the models directory of the pinned forest_gen"
            )
    if _office_enabled(args):
        if not _sensor_rig_enabled(args):
            raise SystemExit("Office L0 requires the pinned V3 sensor-rig URDFs")
        expected_mode = "external" if _office_crowd_enabled(args) else "qualification"
        if args.mode != expected_mode:
            raise SystemExit(f"{args.course} requires {expected_mode} mode")
        if args.office_usd_path is None or not args.office_usd_path.is_file():
            raise SystemExit("Office L0 physics wrapper USD is missing")
        if not args.office_usd_sha256:
            raise SystemExit("Office L0 physics wrapper SHA-256 is required")
        if _sha256(args.office_usd_path) != args.office_usd_sha256:
            raise SystemExit("Office L0 physics wrapper SHA-256 mismatch")
        if args.office_route_path is None or not args.office_route_path.is_file():
            raise SystemExit("Office L0 route preflight is missing")
        if not args.office_route_sha256:
            raise SystemExit("Office L0 route preflight SHA-256 is required")
        if _sha256(args.office_route_path) != args.office_route_sha256:
            raise SystemExit("Office L0 route preflight SHA-256 mismatch")
        if args.office_start_xy is None or args.office_goal_xy is None:
            raise SystemExit("Office L0 start and goal coordinates are required")
        route_contract = json.loads(args.office_route_path.read_text(encoding="utf-8"))
        if route_contract.get("status") != "office_l0_conservative_route_preflight_pass":
            raise SystemExit("Office L0 route preflight status is not pass")
        for name, supplied in (
            ("start_xy_m", args.office_start_xy),
            ("goal_xy_m", args.office_goal_xy),
        ):
            expected = route_contract.get(name)
            if expected is None or any(
                abs(float(expected[index]) - float(supplied[index])) > 1.0e-9
                for index in range(2)
            ):
                raise SystemExit(f"Office L0 {name} does not match the route preflight")
        if not math.isfinite(args.office_pedestrian_turnaround_hold_seconds):
            raise SystemExit("Office pedestrian turnaround hold must be finite")
        if (
            args.office_pedestrian_motion_mode != "single_pass"
            and args.office_pedestrian_turnaround_hold_seconds <= 0.0
        ):
            raise SystemExit(
                "ping-pong Office pedestrians require a positive turnaround hold"
            )
        if (
            args.office_pedestrian_motion_mode != "single_pass"
            and args.official_human_animation_mode != "phase_conditioned"
        ):
            raise SystemExit(
                "ping-pong Office pedestrians require phase-conditioned animation"
            )
    elif any(
        value is not None
        for value in (
            args.office_usd_path,
            args.office_usd_sha256,
            args.office_route_path,
            args.office_route_sha256,
            args.office_start_xy,
            args.office_goal_xy,
        )
    ):
        raise SystemExit("Office arguments are valid only for office_l0_static")
    if not _office_crowd_enabled(args) and (
        args.office_pedestrian_motion_mode != "single_pass"
        or args.office_pedestrian_turnaround_hold_seconds != 0.0
    ):
        raise SystemExit(
            "Office pedestrian motion arguments are valid only for office_l0_crowd"
        )
    if _forest_navigation_enabled(args) or _dual_cloud_geometry_enabled(args):
        if (
            not math.isfinite(args.terrain_filter_cell_size)
            or args.terrain_filter_cell_size <= 0.0
            or not math.isfinite(args.terrain_filter_height_threshold)
            or args.terrain_filter_height_threshold <= 0.0
            or args.terrain_filter_neighbor_cells < 0
            or args.terrain_filter_minimum_neighbor_cells <= 0
        ):
            raise SystemExit("geometry terrain-filter parameters are invalid")
    if _dual_cloud_geometry_enabled(args):
        if not _official_mid360_enabled(args):
            raise SystemExit("upstream_go2_reference requires the pinned MID-360 pattern")
        if not _sensor_rig_enabled(args):
            raise SystemExit("upstream_go2_reference requires the pinned sensor rig")
        if abs(float(args.max_vx) - 0.50) > 1.0e-9:
            raise SystemExit("upstream_go2_reference requires the frozen 0.50 m/s Lite3 limit")
    if _forest_review_geometry_enabled(args) and abs(float(args.max_vx) - 1.0) > 1.0e-9:
        raise SystemExit("V6/V7/V8 requires the Isaac forward command limit to equal 1.0 m/s")
    if _dynamic_obstacle_enabled(args):
        try:
            _dynamic_obstacle_spec(args)
        except ValueError as error:
            raise SystemExit(f"invalid dynamic obstacle contract: {error}") from error
    elif args.dynamic_obstacle_schedule_trigger != "first_nonzero_body_command":
        raise SystemExit(
            "--dynamic-obstacle-schedule-trigger is valid only for a dynamic course"
        )
    if _forest_v8_official_enabled(args) and (
        abs(float(args.dynamic_obstacle_height) - OFFICIAL_HUMAN_CAPSULE_HEIGHT_M)
        > 1.0e-9
        or abs(float(args.dynamic_obstacle_radius) - OFFICIAL_HUMAN_CAPSULE_RADIUS_M)
        > 1.0e-9
    ):
        raise SystemExit(
            "official human requires the frozen 1.70 m x 0.30 m capsule contract"
        )
    if _forest_v8_official_enabled(args) or _office_crowd_enabled(args):
        if (
            args.official_human_animation_cache is None
            or not args.official_human_animation_cache.is_file()
        ):
            raise SystemExit(
                "official human requires a runtime-generated Biped retarget cache"
            )
    elif args.official_human_animation_cache is not None:
        raise SystemExit(
            "--official-human-animation-cache is valid only for the official-human course"
        )
    if (
        not (_forest_v8_official_enabled(args) or _office_crowd_enabled(args))
        and args.official_human_animation_mode != "phase_conditioned"
    ):
        raise SystemExit(
            "--official-human-animation-mode is valid only for the official-human course"
        )
    if _office_review_presentation_enabled(args):
        if not _office_enabled(args):
            raise SystemExit("Office review presentation is valid only for Office L0 courses")
        side_video_target = _office_review_side_video_path(args)
        overview_video_target = _office_review_overview_video_path(args)
        presentation_paths = {
            "--video-path": args.video_path,
            "--office-review-third-person-side-video-path": side_video_target,
            "--office-review-overview-video-path": overview_video_target,
            "--office-review-camera-trace-path": args.office_review_camera_trace_path,
            "--office-review-material-audit-path": args.office_review_material_audit_path,
            "--office-review-dashboard-video-path": args.office_review_dashboard_video_path,
            "--office-review-dashboard-metadata-path": args.office_review_dashboard_metadata_path,
            "--office-review-validation-report-path": args.office_review_validation_report_path,
        }
        for flag_name, path_val in presentation_paths.items():
            if path_val is None:
                raise SystemExit(f"Office review presentation requires {flag_name}")
            p_str = str(path_val.resolve(strict=False)).lower()
            if "candidate38" in p_str or "candidate39" in p_str:
                raise SystemExit(f"Office review presentation output {flag_name}={path_val} cannot target immutable candidate38/39")
            if os.path.lexists(path_val):
                raise SystemExit(f"Office review presentation output {flag_name}={path_val} already exists")

        review_inputs = {
            "--office-review-effective-input-path": args.office_review_effective_input_path,
            "--office-review-launcher-path": args.office_review_launcher_path,
            "--acceptance-config": args.acceptance_config,
            "--robot-asset": args.robot_asset,
        }
        for flag_name, path_val in review_inputs.items():
            if path_val is None or not path_val.is_file() or path_val.is_symlink():
                raise SystemExit(f"Office review presentation requires regular input {flag_name}")

        # Verify all output paths are distinct
        resolved = [p.resolve() for p in presentation_paths.values()]
        if len(set(resolved)) != len(resolved):
            raise SystemExit("Office review presentation output paths must all be distinct")
        input_resolved = {path.resolve() for path in review_inputs.values()}
        if any(path in input_resolved for path in resolved):
            raise SystemExit("Office review presentation outputs must not alias mandatory inputs")
        if args.video_fps < 25:
            raise SystemExit("Office review presentation requires --video-fps >= 25")
        if args.office_review_lighting_profile == "high_contrast" and (
            not math.isfinite(args.office_review_dome_light_intensity)
            or not 100.0 <= args.office_review_dome_light_intensity <= 1200.0
        ):
            raise SystemExit("Office review dome-light intensity must be within [100, 1200]")
        if not math.isfinite(args.office_review_exposure) or not -4.0 <= args.office_review_exposure <= 4.0:
            raise SystemExit("Office review exposure must be within [-4, 4]")

        # Validate side and overview camera configs
        from .office_review_presentation import (
            validate_overview_camera_config,
            validate_side_camera_config,
        )
        try:
            validate_side_camera_config({
                "side": args.office_review_camera_side,
                "lateral_distance_m": args.office_review_camera_lateral_distance,
                "trailing_bias_m": args.office_review_camera_trailing_bias,
                "height_m": args.office_review_camera_height,
                "focal_length_mm": args.office_review_camera_focal_length_mm,
                "look_ahead_m": args.office_review_camera_look_ahead,
                "look_height_offset_m": args.office_review_camera_look_height_offset,
                "smoothing_rate": args.office_review_camera_smoothing_rate,
                "max_eye_speed_mps": args.office_review_camera_max_eye_speed,
                "max_target_speed_mps": args.office_review_camera_max_target_speed,
            })
            validate_overview_camera_config({
                "distance_m": args.office_review_overview_distance,
                "azimuth_offset_deg": args.office_review_overview_azimuth_offset_deg,
                "height_m": args.office_review_overview_height,
                "look_ahead_m": args.office_review_overview_look_ahead,
                "look_height_offset_m": args.office_review_overview_look_height_offset,
                "smoothing_rate": args.office_review_overview_smoothing_rate,
                "max_eye_speed_mps": args.office_review_overview_max_eye_speed,
                "max_target_speed_mps": args.office_review_overview_max_target_speed,
            })
        except ValueError as err:
            raise SystemExit(f"invalid Office review camera configuration: {err}") from err

    from isaaclab.app import AppLauncher

    launcher_kwargs = {
        "headless": True,
        "enable_cameras": args.video_path is not None or _sensor_rig_enabled(args),
        "device": args.device,
    }
    simulation_app = AppLauncher(
        **launcher_kwargs,
    ).app
    try:
        return _run(args)
    finally:
        simulation_app.close()


if __name__ == "__main__":
    raise SystemExit(main())

"""Opt-in Office L0 high-quality multi-view human-review presentation.

Provides:
1. Validated camera geometry and bounded smoothing for:
   - Preserved Office chase-camera render (first_view)
   - High-oblique global-follow cutaway view (side_follow schema key)
   - Elevated wide overview (overview)
2. Lite3 real visual material classification, USD binding, and independently measured before/after stage inventory audit.
3. Synchronized 3D multi-view review dashboard rendering with real world-frame XYZ trajectories and causal events.
4. Fail-closed aggregate presentation validation.
"""

from __future__ import annotations

import argparse
import fractions
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, TypeVar

import cv2
import numpy as np

from .trajectory_review import (
    ACTUAL_COLOR_BGR,
    PLAN_COLOR_BGR,
    SCAN_OCCUPANCY_COLOR_BGR,
    associate_bspline_sim_times,
    sample_uniform_bspline,
)


# ---------------------------------------------------------------------------
# Constants & Quality Profiles
# ---------------------------------------------------------------------------

DASHBOARD_WIDTH = 1920
DASHBOARD_HEIGHT = 1080

PANEL_CAM_WIDTH = 640
PANEL_CAM_HEIGHT = 360

PANEL_3D_WIDTH = 960
PANEL_3D_HEIGHT = 720

PANEL_TELEM_WIDTH = 960
PANEL_TELEM_HEIGHT = 720

REVIEW_MATERIAL_TORSO_RGB: Tuple[float, float, float] = (1.0, 1.0, 1.0)
REVIEW_MATERIAL_LIMB_RGB: Tuple[float, float, float] = (1.0, 1.0, 1.0)
PRESERVED_FIRST_VIEW_CAMERA_MODEL = "preserved_candidate38_39_chase_v1"
SIDE_VIEW_CAMERA_MODEL = "high_oblique_l0_global_cutaway_v3_height8m"

OFFICE_L0_CUTAWAY_STAGE_PREFIXES: Tuple[str, ...] = (
    "/World/Environment/",
    "/World/ground/",
)
OFFICE_L0_CUTAWAY_ROOT_PREFIXES: Tuple[str, ...] = (
    "SM_Ceiling_",
    "BP_CeilingLight",
)
OFFICE_FLOOR_ROOT_PREFIXES: Tuple[str, ...] = ("SM_Floor_", "SM_Floor")

TORSO_KEYWORDS: Tuple[str, ...] = ("torso", "trunk", "body", "carrier", "base")
LIMB_KEYWORDS: Tuple[str, ...] = ("hip", "thigh", "shank", "calf", "foot", "knee", "leg")

SIDE_CAMERA_DEFAULTS: Dict[str, Any] = {
    "side": "left",                  # "left" (-1.0) or "right" (1.0)
    "lateral_distance_m": 3.0,       # lateral offset from robot heading (m)
    "trailing_bias_m": 1.5,          # distance behind robot (m)
    "height_m": 2.0,                 # camera height above ground (m)
    "look_ahead_m": 1.0,             # look-at target distance ahead of robot (m)
    "look_height_offset_m": 0.15,    # look-at target height offset above root (m)
    "focal_length_mm": 18.14756,     # viewport-camera focal length (mm)
    "smoothing_rate": 4.0,           # exponential smoothing rate (1/s)
    "max_eye_speed_mps": 8.0,        # maximum eye translation speed (m/s)
    "max_target_speed_mps": 8.0,     # maximum target translation speed (m/s)
}

OVERVIEW_CAMERA_DEFAULTS: Dict[str, Any] = {
    "distance_m": 6.5,               # horizontal distance offset from robot (m)
    "azimuth_offset_deg": 35.0,      # angle relative to robot heading (deg)
    "height_m": 4.5,                 # camera elevation above ground (m)
    "look_ahead_m": 2.0,             # look-at target distance ahead of robot (m)
    "look_height_offset_m": 0.20,    # look-at target height offset above root (m)
    "smoothing_rate": 3.0,           # exponential smoothing rate (1/s)
    "max_eye_speed_mps": 6.0,        # maximum eye translation speed (m/s)
    "max_target_speed_mps": 6.0,     # maximum target translation speed (m/s)
}

FROZEN_QUALITY_PROFILE: Dict[str, Any] = {
    "resolution_width": 2560,
    "resolution_height": 1440,
    "min_fps": 25,
    "codec": "h264",
    "profile": "high",
    "pixel_format": "yuv420p",
    "crf": 14,
    "preset": "medium",
    "color_primaries": "bt709",
    "color_transfer": "bt709",
    "color_matrix": "bt709",
    "color_range": "tv",
    "renderer_anti_aliasing": "dlaa_native_resolution",
    "renderer_anti_aliasing_mode": 4,
    "renderer_dlss_frame_generation": False,
    "renderer_auto_exposure": False,
    "renderer_base_film_iso": 100.0,
    # Each view shares the viewport renderer.  After changing its camera pose,
    # discard transient DLAA/RTX frames before encoding the settled image.
    "renderer_settle_render_count": 3,
    "renderer_scale": 1.0,
    "exposure": 0.0,
    "tone_mapping": "isaac_default_aces",
    "motion_blur": False,
}


def frozen_quality_profile() -> Dict[str, Any]:
    """Return a defensive copy of the one review-quality source of truth."""
    return dict(FROZEN_QUALITY_PROFILE)


def review_film_iso(exposure_ev: float, base_film_iso: float = 100.0) -> float:
    """Convert a bounded review exposure offset into a fixed film ISO."""
    exposure = float(exposure_ev)
    base_iso = float(base_film_iso)
    if not math.isfinite(exposure) or not -4.0 <= exposure <= 4.0:
        raise ValueError("review exposure must be finite and within [-4, 4] EV")
    if not math.isfinite(base_iso) or base_iso <= 0.0:
        raise ValueError("base film ISO must be finite and positive")
    return base_iso * (2.0 ** exposure)


SettledFrame = TypeVar("SettledFrame")


def render_temporally_settled_frame(
    render_once: Callable[[], SettledFrame],
    render_count: int,
) -> SettledFrame:
    """Render one unchanged simulator state repeatedly and return the last image.

    The repeated calls update only renderer history.  The caller owns the
    simulator-state and cutaway boundaries and must not advance physics here.
    """
    if isinstance(render_count, bool) or not isinstance(render_count, int):
        raise ValueError("renderer settle count must be an integer")
    if render_count < 1 or render_count > 8:
        raise ValueError("renderer settle count must be within [1, 8]")
    frame = render_once()
    for _ in range(1, render_count):
        frame = render_once()
    return frame


def office_l0_cutaway_root_paths(prim_paths: Sequence[str]) -> List[str]:
    """Select only Office L0 ceiling and ceiling-light actor roots.

    The returned roots are intended for a render-only session-layer visibility
    override around the high-oblique review render. Floors, walls, furniture,
    pedestrians, the robot, physics, and sensor targets are deliberately out of
    scope.
    """
    selected = set()
    for raw_path in prim_paths:
        prim_path = str(raw_path)
        if not prim_path.startswith(OFFICE_L0_CUTAWAY_STAGE_PREFIXES):
            continue
        components = [component for component in prim_path.split("/") if component]
        for component_index, component in enumerate(components):
            if component.startswith(OFFICE_L0_CUTAWAY_ROOT_PREFIXES):
                selected.add("/" + "/".join(components[:component_index + 1]))
                break
    return sorted(selected)


def office_floor_root_paths(prim_paths: Sequence[str]) -> List[str]:
    """Return Office floor actor roots for runtime floor-level filtering."""
    selected = set()
    for raw_path in prim_paths:
        prim_path = str(raw_path)
        if not prim_path.startswith(OFFICE_L0_CUTAWAY_STAGE_PREFIXES):
            continue
        components = [component for component in prim_path.split("/") if component]
        for component_index, component in enumerate(components):
            if component.startswith(OFFICE_FLOOR_ROOT_PREFIXES):
                selected.add("/" + "/".join(components[:component_index + 1]))
                break
    return sorted(selected)


def office_actor_root_paths(
    prim_paths: Sequence[str], known_actor_roots: Sequence[str]
) -> List[str]:
    """Find direct Office actor siblings using known ceiling/floor anchors."""
    actor_parents = {
        str(actor_root).rsplit("/", 1)[0]
        for actor_root in known_actor_roots
        if "/" in str(actor_root).rstrip("/")
    }
    selected = set()
    for raw_path in prim_paths:
        prim_path = str(raw_path)
        for actor_parent in actor_parents:
            prefix = actor_parent + "/"
            if prim_path.startswith(prefix):
                actor_name = prim_path[len(prefix):].split("/", 1)[0]
                if actor_name:
                    selected.add(prefix + actor_name)
    return sorted(selected)


class DirectH264Writer:
    """One-generation RGB-to-H.264 writer with a fail-closed frozen profile."""

    def __init__(self, output_path: Path, fps: int, profile: Mapping[str, Any] = FROZEN_QUALITY_PROFILE):
        self.output_path = Path(output_path)
        self.profile = dict(profile)
        self.fps = int(fps)
        self.frame_count = 0
        if self.fps < int(self.profile["min_fps"]):
            raise ValueError(f"review video fps {self.fps} is below {self.profile['min_fps']}")
        if self.output_path.exists() or self.output_path.is_symlink():
            raise FileExistsError(f"review video output already exists: {self.output_path}")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise RuntimeError("ffmpeg is required for review video encoding")
        width = int(self.profile["resolution_width"])
        height = int(self.profile["resolution_height"])
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-n",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{width}x{height}", "-pix_fmt", "rgb24", "-r", str(self.fps),
            "-i", "-", "-an", "-c:v", "libx264",
            "-profile:v", str(self.profile["profile"]),
            "-preset", str(self.profile["preset"]),
            "-crf", str(int(self.profile["crf"])),
            "-pix_fmt", str(self.profile["pixel_format"]),
            "-color_range", str(self.profile["color_range"]),
            "-color_primaries", str(self.profile["color_primaries"]),
            "-color_trc", str(self.profile["color_transfer"]),
            "-colorspace", str(self.profile["color_matrix"]),
            "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1",
            "-movflags", "+faststart", str(self.output_path),
        ]
        self._process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    def append_data(self, frame: np.ndarray) -> None:
        if self._process.stdin is None:
            raise RuntimeError("review video writer is closed")
        expected_shape = (
            int(self.profile["resolution_height"]),
            int(self.profile["resolution_width"]),
            3,
        )
        rgb = np.asarray(frame, dtype=np.uint8)
        if rgb.shape != expected_shape:
            raise ValueError(f"rendered frame shape {rgb.shape} != native review shape {expected_shape}")
        try:
            self._process.stdin.write(np.ascontiguousarray(rgb).tobytes())
        except BrokenPipeError as exc:
            stderr = self._process.stderr.read().decode("utf-8", "replace") if self._process.stderr else ""
            raise RuntimeError(f"ffmpeg review writer failed: {stderr.strip()}") from exc
        self.frame_count += 1

    def close(self) -> None:
        if self._process.stdin is not None and not self._process.stdin.closed:
            self._process.stdin.close()
        stderr = self._process.stderr.read().decode("utf-8", "replace") if self._process.stderr else ""
        return_code = self._process.wait()
        if self._process.stderr is not None:
            self._process.stderr.close()
        if return_code != 0:
            raise RuntimeError(f"ffmpeg review writer exited {return_code}: {stderr.strip()}")
        if self.frame_count <= 0 or not self.output_path.is_file():
            raise RuntimeError("review writer produced no frames")


def state_snapshot_identity(
    step: int,
    sim_time_seconds: float,
    root_pos_w: Sequence[float],
    root_quat_w: Sequence[float],
) -> str:
    """Hash the immutable simulator state shared by all three renders."""
    payload = {
        "step": int(step),
        "sim_time_seconds": float(sim_time_seconds),
        "root_pos_w": [float(value) for value in root_pos_w],
        "root_quat_w": [float(value) for value in root_quat_w],
    }
    if (
        len(payload["root_pos_w"]) != 3
        or len(payload["root_quat_w"]) != 4
        or not all(
            math.isfinite(value)
            for value in [payload["sim_time_seconds"], *payload["root_pos_w"], *payload["root_quat_w"]]
        )
    ):
        raise ValueError("state snapshot must contain finite time, root position, and quaternion")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# ---------------------------------------------------------------------------
# Camera Configuration & Math
# ---------------------------------------------------------------------------

def normalize_side(side_val: Any) -> float:
    """Normalize camera side specification to -1.0 (left) or 1.0 (right)."""
    if isinstance(side_val, (int, float)):
        val = float(side_val)
        if abs(val - (-1.0)) < 1e-4:
            return -1.0
        if abs(val - 1.0) < 1e-4:
            return 1.0
        raise ValueError(f"side must be -1.0 (left) or 1.0 (right), got {side_val}")
    if isinstance(side_val, str):
        s = side_val.strip().lower()
        if s in ("left", "-1", "-1.0"):
            return -1.0
        if s in ("right", "1", "+1", "1.0", "+1.0"):
            return 1.0
        raise ValueError(f"unknown side specification: {side_val!r}")
    raise ValueError(f"invalid side type: {type(side_val)}")


def side_name(side_val: Any) -> str:
    """Return 'left' or 'right' string for side specification."""
    norm = normalize_side(side_val)
    return "left" if norm < 0.0 else "right"


def validate_side_camera_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Strictly validate side-camera configuration and return typed dictionary.

    Fails closed on missing, non-finite, negative, or out-of-range parameters.
    """
    validated: Dict[str, Any] = {}
    side_raw = config.get("side", SIDE_CAMERA_DEFAULTS["side"])
    validated["side_value"] = normalize_side(side_raw)
    validated["side"] = side_name(side_raw)

    bounds: Dict[str, Tuple[float, float, bool]] = {
        "lateral_distance_m": (0.5, 20.0, True),
        "trailing_bias_m": (0.0, 15.0, False),
        "height_m": (0.5, 10.0, True),
        "look_ahead_m": (0.0, 10.0, False),
        "look_height_offset_m": (-2.0, 2.0, False),
        "focal_length_mm": (4.0, 100.0, True),
        "smoothing_rate": (0.1, 50.0, True),
        "max_eye_speed_mps": (0.1, 50.0, True),
        "max_target_speed_mps": (0.1, 50.0, True),
    }

    for key, (min_v, max_v, strict_pos) in bounds.items():
        if key not in config:
            val = float(SIDE_CAMERA_DEFAULTS[key])
        else:
            raw_val = config[key]
            try:
                val = float(raw_val)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid non-numeric value for {key}: {raw_val}") from exc

        if not math.isfinite(val):
            raise ValueError(f"non-finite value for {key}: {val}")
        if strict_pos and val <= 0.0:
            raise ValueError(f"{key} must be strictly positive, got {val}")
        if not (min_v <= val <= max_v):
            raise ValueError(f"{key}={val} out of bounds [{min_v}, {max_v}]")
        validated[key] = val

    return validated


def validate_overview_camera_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Strictly validate overview camera configuration and return typed dictionary."""
    validated: Dict[str, Any] = {}

    bounds: Dict[str, Tuple[float, float, bool]] = {
        "distance_m": (1.0, 30.0, True),
        "azimuth_offset_deg": (-180.0, 180.0, False),
        "height_m": (1.0, 20.0, True),
        "look_ahead_m": (-5.0, 15.0, False),
        "look_height_offset_m": (-2.0, 5.0, False),
        "smoothing_rate": (0.1, 50.0, True),
        "max_eye_speed_mps": (0.1, 50.0, True),
        "max_target_speed_mps": (0.1, 50.0, True),
    }

    for key, (min_v, max_v, strict_pos) in bounds.items():
        if key not in config:
            val = float(OVERVIEW_CAMERA_DEFAULTS[key])
        else:
            raw_val = config[key]
            try:
                val = float(raw_val)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid non-numeric value for {key}: {raw_val}") from exc

        if not math.isfinite(val):
            raise ValueError(f"non-finite value for {key}: {val}")
        if strict_pos and val <= 0.0:
            raise ValueError(f"{key} must be strictly positive, got {val}")
        if not (min_v <= val <= max_v):
            raise ValueError(f"{key}={val} out of bounds [{min_v}, {max_v}]")
        validated[key] = val

    return validated


def side_follow_desired_pose(
    root_x: float,
    root_y: float,
    root_z: float,
    yaw_rad: float,
    config: Mapping[str, Any],
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Compute desired eye and target for external lateral side-follow camera."""
    for name, v in (("root_x", root_x), ("root_y", root_y), ("root_z", root_z), ("yaw_rad", yaw_rad)):
        if not math.isfinite(float(v)):
            raise ValueError(f"non-finite robot pose component {name}={v}")

    cfg = validate_side_camera_config(config)
    lateral = float(cfg["lateral_distance_m"])
    trail = float(cfg["trailing_bias_m"])
    height = float(cfg["height_m"])
    look_ahead = float(cfg["look_ahead_m"])
    look_z_off = float(cfg["look_height_offset_m"])
    side_mult = float(cfg["side_value"])

    cos_yaw = math.cos(yaw_rad)
    sin_yaw = math.sin(yaw_rad)

    # Perpendicular vector: side=-1 -> left of heading (+sin, -cos)
    perp_x = sin_yaw * side_mult
    perp_y = -cos_yaw * side_mult

    eye = (
        float(root_x - trail * cos_yaw + lateral * perp_x),
        float(root_y - trail * sin_yaw + lateral * perp_y),
        float(height),
    )
    target = (
        float(root_x + look_ahead * cos_yaw),
        float(root_y + look_ahead * sin_yaw),
        float(root_z + look_z_off),
    )
    return eye, target


def overview_desired_pose(
    root_x: float,
    root_y: float,
    root_z: float,
    yaw_rad: float,
    config: Mapping[str, Any],
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Compute desired eye and target for elevated wide-overview camera."""
    for name, v in (("root_x", root_x), ("root_y", root_y), ("root_z", root_z), ("yaw_rad", yaw_rad)):
        if not math.isfinite(float(v)):
            raise ValueError(f"non-finite robot pose component {name}={v}")

    cfg = validate_overview_camera_config(config)
    dist = float(cfg["distance_m"])
    azimuth_rad = math.radians(float(cfg["azimuth_offset_deg"]))
    height = float(cfg["height_m"])
    look_ahead = float(cfg["look_ahead_m"])
    look_z_off = float(cfg["look_height_offset_m"])

    cam_angle = yaw_rad + azimuth_rad
    eye = (
        float(root_x - dist * math.cos(cam_angle)),
        float(root_y - dist * math.sin(cam_angle)),
        float(root_z + height),
    )
    target = (
        float(root_x + look_ahead * math.cos(yaw_rad)),
        float(root_y + look_ahead * math.sin(yaw_rad)),
        float(root_z + look_z_off),
    )
    return eye, target


def side_observer_desired_pose(
    root_x: float,
    root_y: float,
    root_z: float,
    yaw_rad: float,
    config: Mapping[str, Any],
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Backward-compatible alias for side_follow_desired_pose."""
    return side_follow_desired_pose(root_x, root_y, root_z, yaw_rad, config)


def smooth_pose_bounded(
    current_eye: Tuple[float, float, float],
    current_target: Tuple[float, float, float],
    desired_eye: Tuple[float, float, float],
    desired_target: Tuple[float, float, float],
    dt: float,
    smoothing_rate: float,
    max_eye_speed: float,
    max_target_speed: float,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], float, float, float, float]:
    """Exponentially smooth eye and target with strict per-frame speed limits.

    Returns:
        (realized_eye, realized_target, eye_disp, target_disp, max_allowed_eye, max_allowed_target)

    Raises:
        ValueError: If dt <= 0, smoothing_rate <= 0, speed limits <= 0, or any coordinate is non-finite.
    """
    if not math.isfinite(dt) or dt <= 0.0:
        raise ValueError(f"dt must be finite and strictly positive, got {dt}")
    if not math.isfinite(smoothing_rate) or smoothing_rate <= 0.0:
        raise ValueError(f"smoothing_rate must be finite and strictly positive, got {smoothing_rate}")
    if not math.isfinite(max_eye_speed) or max_eye_speed <= 0.0:
        raise ValueError(f"max_eye_speed must be finite and strictly positive, got {max_eye_speed}")
    if not math.isfinite(max_target_speed) or max_target_speed <= 0.0:
        raise ValueError(f"max_target_speed must be finite and strictly positive, got {max_target_speed}")

    for name, pose in (
        ("current_eye", current_eye),
        ("current_target", current_target),
        ("desired_eye", desired_eye),
        ("desired_target", desired_target),
    ):
        if len(pose) != 3 or not all(math.isfinite(float(x)) for x in pose):
            raise ValueError(f"non-finite coordinates in {name}: {pose}")

    alpha = 1.0 - math.exp(-smoothing_rate * dt)
    alpha = max(0.0, min(1.0, alpha))

    # Candidate exponential interpolation
    cand_eye = tuple(current_eye[i] + alpha * (desired_eye[i] - current_eye[i]) for i in range(3))
    cand_target = tuple(current_target[i] + alpha * (desired_target[i] - current_target[i]) for i in range(3))

    # Eye displacement clamping
    eye_delta = tuple(cand_eye[i] - current_eye[i] for i in range(3))
    eye_dist = math.sqrt(sum(d * d for d in eye_delta))
    max_allowed_eye = max_eye_speed * dt

    if eye_dist > max_allowed_eye and eye_dist > 1e-9:
        scale = max_allowed_eye / eye_dist
        realized_eye = tuple(current_eye[i] + eye_delta[i] * scale for i in range(3))
        eye_disp = max_allowed_eye
    else:
        realized_eye = cand_eye
        eye_disp = eye_dist

    # Target displacement clamping
    target_delta = tuple(cand_target[i] - current_target[i] for i in range(3))
    target_dist = math.sqrt(sum(d * d for d in target_delta))
    max_allowed_target = max_target_speed * dt

    if target_dist > max_allowed_target and target_dist > 1e-9:
        scale = max_allowed_target / target_dist
        realized_target = tuple(current_target[i] + target_delta[i] * scale for i in range(3))
        target_disp = max_allowed_target
    else:
        realized_target = cand_target
        target_disp = target_dist

    return (
        (float(realized_eye[0]), float(realized_eye[1]), float(realized_eye[2])),
        (float(realized_target[0]), float(realized_target[1]), float(realized_target[2])),
        float(eye_disp),
        float(target_disp),
        float(max_allowed_eye),
        float(max_allowed_target),
    )


def smooth_pose(
    current_eye: Tuple[float, float, float],
    current_target: Tuple[float, float, float],
    desired_eye: Tuple[float, float, float],
    desired_target: Tuple[float, float, float],
    dt: float,
    smoothing_rate: float,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Legacy compatibility exponential smoother."""
    if dt <= 0.0 or smoothing_rate <= 0.0:
        return desired_eye, desired_target
    re_eye, re_target, _, _, _, _ = smooth_pose_bounded(
        current_eye, current_target, desired_eye, desired_target,
        dt=dt, smoothing_rate=smoothing_rate,
        max_eye_speed=SIDE_CAMERA_DEFAULTS["max_eye_speed_mps"],
        max_target_speed=SIDE_CAMERA_DEFAULTS["max_target_speed_mps"],
    )
    return re_eye, re_target


def preserved_first_view_pose(
    root_x: float,
    root_y: float,
    root_z: float,
    yaw: float,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Return the exact Office chase-camera geometry accepted as first view.

    Dr Sun's task terminology calls this the first-person view.  It is kept as
    the pre-existing 2.2 m root-relative chase composition and must not be
    replaced by a D435i or other robot-mounted camera.
    """
    values = (root_x, root_y, root_z, yaw)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("preserved first-view pose values must be finite")
    eye = (
        float(root_x) - 2.2 * math.cos(float(yaw)),
        float(root_y) - 2.2 * math.sin(float(yaw)),
        min(max(float(root_z) + 1.80, 1.80), 2.40),
    )
    target = (
        float(root_x) + 0.60 * math.cos(float(yaw)),
        float(root_y) + 0.60 * math.sin(float(yaw)),
        float(root_z) + 0.16,
    )
    return eye, target


def camera_trace_row(
    frame_index: int,
    step: int,
    sim_time_seconds: float,
    run_identity: str,
    root_pos_w: Sequence[float],
    root_quat_w: Sequence[float],
    first_eye: Sequence[float],
    first_target: Sequence[float],
    side_desired_eye: Sequence[float],
    side_desired_target: Sequence[float],
    side_realized_eye: Sequence[float],
    side_realized_target: Sequence[float],
    side_config: Mapping[str, Any],
    overview_desired_eye: Sequence[float],
    overview_desired_target: Sequence[float],
    overview_realized_eye: Sequence[float],
    overview_realized_target: Sequence[float],
    overview_config: Mapping[str, Any],
    dt: float,
    side_eye_displacement: float = 0.0,
    side_target_displacement: float = 0.0,
    side_max_allowed_eye_displacement: float = 0.0,
    side_max_allowed_target_displacement: float = 0.0,
    overview_eye_displacement: float = 0.0,
    overview_target_displacement: float = 0.0,
    overview_max_allowed_eye_displacement: float = 0.0,
    overview_max_allowed_target_displacement: float = 0.0,
    first_fallback_reason: Optional[str] = None,
    renderer_settings: Optional[Mapping[str, Any]] = None,
    snapshot_identity: Optional[str] = None,
) -> Dict[str, Any]:
    """Build one schema-valid row of camera_trace.jsonl for all 3 views."""
    if not run_identity or not isinstance(run_identity, str) or not run_identity.strip():
        raise ValueError("run_identity must be a non-empty string in camera_trace_row")

    side_cfg = validate_side_camera_config(side_config)
    over_cfg = validate_overview_camera_config(overview_config)
    if frame_index < 0 or step < 0 or not math.isfinite(float(sim_time_seconds)):
        raise ValueError("camera trace frame, step, and simulator time must be valid")
    root_pos = [float(v) for v in root_pos_w]
    root_quat = [float(v) for v in root_quat_w]
    computed_snapshot_identity = state_snapshot_identity(
        step, sim_time_seconds, root_pos, root_quat
    )
    if snapshot_identity is not None and snapshot_identity != computed_snapshot_identity:
        raise ValueError("provided snapshot identity does not match the root-state snapshot")
    capture_settings = dict(renderer_settings or FROZEN_QUALITY_PROFILE)

    return {
        "schema_version": 4,
        "frame_index": int(frame_index),
        "step": int(step),
        "sim_time_seconds": float(sim_time_seconds),
        "run_identity": str(run_identity),
        "state_snapshot_identity": computed_snapshot_identity,
        "root_pos_w": root_pos,
        "root_quat_w": root_quat,
        "capture_settings": capture_settings,
        "first_view": {
            "camera_model": PRESERVED_FIRST_VIEW_CAMERA_MODEL,
            "eye": [float(v) for v in first_eye],
            "target": [float(v) for v in first_target],
            "fallback_reason": str(first_fallback_reason) if first_fallback_reason else None,
        },
        "side_follow": {
            "camera_model": SIDE_VIEW_CAMERA_MODEL,
            "side": side_cfg["side"],
            "configured_side": float(side_cfg["side_value"]),
            "focal_length_mm": float(side_cfg["focal_length_mm"]),
            "desired_eye": [float(v) for v in side_desired_eye],
            "desired_target": [float(v) for v in side_desired_target],
            "realized_eye": [float(v) for v in side_realized_eye],
            "realized_target": [float(v) for v in side_realized_target],
            "dt": float(dt),
            "smoothing_rate": float(side_cfg["smoothing_rate"]),
            "max_eye_speed_mps": float(side_cfg["max_eye_speed_mps"]),
            "max_target_speed_mps": float(side_cfg["max_target_speed_mps"]),
            "eye_displacement_m": float(side_eye_displacement),
            "target_displacement_m": float(side_target_displacement),
            "max_allowed_eye_displacement_m": float(side_max_allowed_eye_displacement),
            "max_allowed_target_displacement_m": float(side_max_allowed_target_displacement),
        },
        "overview": {
            "desired_eye": [float(v) for v in overview_desired_eye],
            "desired_target": [float(v) for v in overview_desired_target],
            "realized_eye": [float(v) for v in overview_realized_eye],
            "realized_target": [float(v) for v in overview_realized_target],
            "dt": float(dt),
            "smoothing_rate": float(over_cfg["smoothing_rate"]),
            "max_eye_speed_mps": float(over_cfg["max_eye_speed_mps"]),
            "max_target_speed_mps": float(over_cfg["max_target_speed_mps"]),
            "eye_displacement_m": float(overview_eye_displacement),
            "target_displacement_m": float(overview_target_displacement),
            "max_allowed_eye_displacement_m": float(overview_max_allowed_eye_displacement),
            "max_allowed_target_displacement_m": float(overview_max_allowed_target_displacement),
        },
    }


# ---------------------------------------------------------------------------
# Review Material Classification, Stage Query & Real Audit
# ---------------------------------------------------------------------------

def classify_mesh_part(prim_path: str) -> str:
    """Classify a visual mesh prim as 'torso', 'limb', or 'unknown'."""
    lower = prim_path.lower()
    for keyword in TORSO_KEYWORDS:
        if keyword in lower:
            return "torso"
    for keyword in LIMB_KEYWORDS:
        if keyword in lower:
            return "limb"
    return "unknown"


def review_material_color(part_class: str) -> Tuple[float, float, float]:
    """Return linear RGB color for a part classification."""
    if part_class == "torso":
        return REVIEW_MATERIAL_TORSO_RGB
    if part_class == "limb":
        return REVIEW_MATERIAL_LIMB_RGB
    return REVIEW_MATERIAL_TORSO_RGB


def query_stage_robot_inventory(
    stage: Any,
    robot_root_path: str = "/World/envs/env_0/Robot",
    *,
    query_phase: str,
    robot_asset_sha256: str,
    referenced_mesh_sha256: Mapping[str, str],
) -> Dict[str, Any]:
    """Independently query robot physical, sensor, visual, and asset identity."""
    if query_phase not in ("before_binding", "after_binding"):
        raise ValueError(f"invalid inventory query phase: {query_phase}")
    if not str(robot_asset_sha256).strip():
        raise ValueError("robot asset SHA-256 is required for stage inventory")
    referenced_hashes = {str(key): str(value) for key, value in referenced_mesh_sha256.items()}
    if not referenced_hashes or any(not value for value in referenced_hashes.values()):
        raise ValueError("referenced mesh SHA-256 inventory cannot be empty")

    try:
        from pxr import Usd, UsdGeom, UsdPhysics, UsdShade  # type: ignore
    except ImportError:
        robot_prim = stage.GetPrimAtPath(robot_root_path) if hasattr(stage, "GetPrimAtPath") else None
        if robot_prim is None or not getattr(robot_prim, "IsValid", lambda: True)():
            raise ValueError(f"robot root prim {robot_root_path} is invalid on stage")
        body_paths = list(getattr(stage, "mock_body_paths", []))
        joint_paths = list(getattr(stage, "mock_joint_paths", []))
        collision_paths = list(getattr(stage, "mock_collision_paths", []))
        visual_paths = list(getattr(stage, "mock_visual_mesh_paths", []))
        material_bindings = dict(getattr(stage, "mock_material_bindings", {}))
        return {
            "query_phase": query_phase,
            "robot_root_path": robot_root_path,
            "robot_asset_sha256": str(robot_asset_sha256),
            "referenced_mesh_sha256": referenced_hashes,
            "body_paths": body_paths,
            "body_records": [{"path": path, "type": "RigidBody"} for path in body_paths],
            "joint_paths": joint_paths,
            "joint_records": [{"path": path, "type": "RevoluteJoint"} for path in joint_paths],
            "collision_prim_paths": collision_paths,
            "visual_mesh_paths": visual_paths,
            "visual_mesh_records": [
                {
                    "path": path,
                    "visibility": "inherited",
                    "collision_api": False,
                    "material_binding": material_bindings.get(path),
                }
                for path in visual_paths
            ],
            "material_bindings": material_bindings,
            "mass_properties": dict(getattr(stage, "mock_mass_properties", {"total_mass_kg": 12.5})),
            "inertia_properties": dict(getattr(stage, "mock_inertia_properties", {"base": [1.0, 1.0, 1.0]})),
            "sensor_target_paths": list(getattr(stage, "mock_sensor_target_paths", [f"{robot_root_path}/mid360_scan_frame", f"{robot_root_path}/d435i_depth_optical_frame"])),
        }

    robot_prim = stage.GetPrimAtPath(robot_root_path)
    if not robot_prim.IsValid():
        raise ValueError(f"robot root prim {robot_root_path} is invalid on USD stage")

    body_paths: List[str] = []
    body_records: List[Dict[str, Any]] = []
    joint_paths: List[str] = []
    joint_records: List[Dict[str, Any]] = []
    collision_prim_paths: List[str] = []
    visual_mesh_paths: List[str] = []
    visual_mesh_records: List[Dict[str, Any]] = []
    material_bindings: Dict[str, str] = {}
    mass_properties: Dict[str, Any] = {}
    inertia_properties: Dict[str, Any] = {}
    sensor_target_paths: List[str] = []

    for prim in Usd.PrimRange(robot_prim, Usd.TraverseInstanceProxies()):
        p_path = str(prim.GetPath())
        if not (p_path == robot_root_path or p_path.startswith(robot_root_path + "/")):
            continue
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            collision_prim_paths.append(p_path)
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            body_paths.append(p_path)
            body_records.append({"path": p_path, "type": str(prim.GetTypeName())})
        if prim.IsA(UsdPhysics.Joint):
            joint_paths.append(p_path)
            joint_records.append({"path": p_path, "type": str(prim.GetTypeName())})
        if prim.HasAPI(UsdPhysics.MassAPI):
            mass_api = UsdPhysics.MassAPI(prim)
            mass = mass_api.GetMassAttr().Get()
            inertia = mass_api.GetDiagonalInertiaAttr().Get()
            if mass is not None:
                mass_properties[p_path] = float(mass)
            if inertia is not None:
                inertia_properties[p_path] = [float(value) for value in inertia]
        lower_path = p_path.lower()
        if any(token in lower_path for token in ("mid360", "d435i", "sensor_carrier", "s410_guard", "pro_interface")):
            sensor_target_paths.append(p_path)
        if prim.IsA(UsdGeom.Mesh) or prim.GetTypeName() == "Mesh":
            is_collision = prim.HasAPI(UsdPhysics.CollisionAPI)
            visibility_attr = prim.GetAttribute("visibility") if prim.HasAttribute("visibility") else None
            visibility = visibility_attr.Get() if visibility_attr else "inherited"
            if not is_collision and visibility != "invisible":
                visual_mesh_paths.append(p_path)
                bound_mat, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
                if bound_mat:
                    material_bindings[p_path] = str(bound_mat.GetPath())
                visual_mesh_records.append({
                    "path": p_path,
                    "visibility": str(visibility),
                    "collision_api": False,
                    "material_binding": material_bindings.get(p_path),
                })

    return {
        "query_phase": query_phase,
        "robot_root_path": robot_root_path,
        "robot_asset_sha256": str(robot_asset_sha256),
        "referenced_mesh_sha256": referenced_hashes,
        "body_paths": sorted(body_paths),
        "body_records": sorted(body_records, key=lambda row: row["path"]),
        "joint_paths": sorted(joint_paths),
        "joint_records": sorted(joint_records, key=lambda row: row["path"]),
        "collision_prim_paths": sorted(collision_prim_paths),
        "visual_mesh_paths": sorted(visual_mesh_paths),
        "visual_mesh_records": sorted(visual_mesh_records, key=lambda row: row["path"]),
        "material_bindings": dict(sorted(material_bindings.items())),
        "mass_properties": dict(sorted(mass_properties.items())),
        "inertia_properties": dict(sorted(inertia_properties.items())),
        "sensor_target_paths": sorted(set(sensor_target_paths)),
    }


_PHYSICAL_INVENTORY_KEYS = (
    "robot_root_path", "robot_asset_sha256", "referenced_mesh_sha256",
    "body_paths", "body_records", "joint_paths", "joint_records",
    "collision_prim_paths", "visual_mesh_paths", "mass_properties",
    "inertia_properties", "sensor_target_paths",
)


def _physical_inventory_projection(inventory: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: inventory.get(key) for key in _PHYSICAL_INVENTORY_KEYS}


def build_material_audit(
    robot_root_path: str,
    affected_prims: Sequence[Mapping[str, Any]],
    pre_inventory: Mapping[str, Any],
    post_inventory: Mapping[str, Any],
    robot_asset_sha256: str,
) -> Dict[str, Any]:
    """Build complete, auditable material record asserting untouched physics/sensors."""
    if not robot_asset_sha256 or not isinstance(robot_asset_sha256, str) or not robot_asset_sha256.strip():
        raise ValueError("robot_asset_sha256 must be a non-empty string in material audit")

    if not affected_prims:
        raise ValueError("affected_prims list cannot be empty")

    for prim in affected_prims:
        path = str(prim.get("prim_path", ""))
        if not (path == robot_root_path or path.startswith(robot_root_path + "/")):
            raise ValueError(f"affected prim {path} is outside robot root {robot_root_path}")
        if "floor" in path.lower() or "office" in path.lower():
            raise ValueError(f"affected prim {path} targets non-robot scene geometry")
        opacity = float(prim.get("opacity", 1.0))
        emission = float(prim.get("emission", 0.0))
        if abs(opacity - 1.0) > 1e-4:
            raise ValueError(f"material opacity must be 1.0, got {opacity}")
        if abs(emission - 0.0) > 1e-4:
            raise ValueError(f"material emission must be 0.0, got {emission}")

    pre_inv = dict(pre_inventory or {})
    post_inv = dict(post_inventory or {})

    if pre_inv.get("query_phase") != "before_binding" or post_inv.get("query_phase") != "after_binding":
        raise ValueError("material audit requires independent before/after inventory queries")
    for key in _PHYSICAL_INVENTORY_KEYS:
        if pre_inv.get(key) in (None, [], {}) or post_inv.get(key) in (None, [], {}):
            raise ValueError(f"material inventory field {key} cannot be empty")

    physics_unchanged = _physical_inventory_projection(pre_inv) == _physical_inventory_projection(post_inv)
    if not physics_unchanged:
        raise ValueError("material binding changed measured physical or sensor inventory")
    pre_bindings = dict(pre_inv.get("material_bindings") or {})
    post_bindings = dict(post_inv.get("material_bindings") or {})
    for prim in affected_prims:
        path = str(prim["prim_path"])
        declared_material = str(prim.get("material_path", ""))
        if not declared_material or post_bindings.get(path) != declared_material:
            raise ValueError(f"post-inventory material binding for {path} does not match audit")
        if pre_bindings.get(path) == post_bindings.get(path):
            raise ValueError(f"material binding for {path} did not change")

    torso_count = sum(1 for p in affected_prims if p.get("part_class") == "torso")
    limb_count = sum(1 for p in affected_prims if p.get("part_class") == "limb")
    unknown_count = sum(1 for p in affected_prims if p.get("part_class") == "unknown")

    return {
        "schema_version": 3,
        "mode": "office_review_material_override",
        "scope": "visual_mesh_prims_only",
        "claim": (
            "Opaque (opacity=1.0) non-emissive (emission=0.0) review-only visual material "
            "applied strictly to Lite3 visual mesh prims for Office human review legibility. "
            "Does not modify URDF, collision meshes, mass, inertia, joints, policy, or sensors."
        ),
        "robot_root_path": robot_root_path,
        "robot_asset_sha256": robot_asset_sha256,
        "referenced_mesh_sha256": dict(pre_inv["referenced_mesh_sha256"]),
        "torso_color_linear_rgb": list(REVIEW_MATERIAL_TORSO_RGB),
        "limb_color_linear_rgb": list(REVIEW_MATERIAL_LIMB_RGB),
        "opacity": 1.0,
        "emission": 0.0,
        "torso_prim_count": torso_count,
        "limb_prim_count": limb_count,
        "unknown_prim_count": unknown_count,
        "total_affected_prims": len(affected_prims),
        "affected_prims": list(affected_prims),
        "physics_inventory_unchanged": bool(physics_unchanged),
        "pre_inventory": pre_inv,
        "post_inventory": post_inv,
    }


def apply_office_review_material_usd(
    stage: Any,
    robot_prim_path: str = "/World/envs/env_0/Robot",
    audit_output_path: Optional[Path] = None,
    robot_asset_sha256: str = "",
    referenced_mesh_sha256: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Bind opaque, non-emissive USD review materials to Lite3 visual meshes on stage.

    Independently queries pre-inventory, applies materials strictly to visible visual
    meshes under robot root, independently queries post-inventory, and writes audit JSON.
    """
    mesh_hashes = dict(referenced_mesh_sha256 or {})
    pre_inventory = query_stage_robot_inventory(
        stage,
        robot_prim_path,
        query_phase="before_binding",
        robot_asset_sha256=robot_asset_sha256,
        referenced_mesh_sha256=mesh_hashes,
    )

    try:
        from pxr import Sdf, Usd, UsdGeom, UsdPhysics, UsdShade  # type: ignore
    except ImportError:
        # Mock stage testing path
        affected_prims = [
            {
                "prim_path": f"{robot_prim_path}/torso/visual",
                "part_class": "torso",
                "material_path": "/World/Looks/Lite3_Review_Torso_Material",
                "color_rgb": list(REVIEW_MATERIAL_TORSO_RGB),
                "opacity": 1.0,
                "emission": 0.0,
            },
            {
                "prim_path": f"{robot_prim_path}/FL_thigh/visual",
                "part_class": "limb",
                "material_path": "/World/Looks/Lite3_Review_Limb_Material",
                "color_rgb": list(REVIEW_MATERIAL_LIMB_RGB),
                "opacity": 1.0,
                "emission": 0.0,
            },
        ]
        if hasattr(stage, "mock_material_bindings"):
            for affected in affected_prims:
                stage.mock_material_bindings[affected["prim_path"]] = affected["material_path"]
        post_inventory = query_stage_robot_inventory(
            stage,
            robot_prim_path,
            query_phase="after_binding",
            robot_asset_sha256=robot_asset_sha256,
            referenced_mesh_sha256=mesh_hashes,
        )
        audit = build_material_audit(
            robot_root_path=robot_prim_path,
            affected_prims=affected_prims,
            pre_inventory=pre_inventory,
            post_inventory=post_inventory,
            robot_asset_sha256=robot_asset_sha256,
        )
        if audit_output_path is not None:
            if audit_output_path.exists():
                raise FileExistsError(f"material audit output already exists: {audit_output_path}")
            write_text_exclusive(audit_output_path, json.dumps(audit, indent=2))
        return audit

    robot_prim = stage.GetPrimAtPath(robot_prim_path)
    if not robot_prim.IsValid():
        raise ValueError(f"robot root prim {robot_prim_path} is invalid on USD stage")

    looks_path = "/World/Looks"
    if not stage.GetPrimAtPath(looks_path).IsValid():
        stage.DefinePrim(looks_path, "Scope")

    torso_mat_path = f"{looks_path}/Lite3_Review_Torso_Material"
    limb_mat_path = f"{looks_path}/Lite3_Review_Limb_Material"

    def _create_pbr_material(mat_path: str, color_rgb: Tuple[float, float, float]) -> Any:
        mat_prim = stage.DefinePrim(mat_path, "Material")
        mat = UsdShade.Material(mat_prim)
        shader = UsdShade.Shader.Define(stage, f"{mat_path}/PBRShader")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(color_rgb)
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.35)
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
        shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(1.0)
        shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set((0.0, 0.0, 0.0))
        mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        return mat

    torso_mat = _create_pbr_material(torso_mat_path, REVIEW_MATERIAL_TORSO_RGB)
    limb_mat = _create_pbr_material(limb_mat_path, REVIEW_MATERIAL_LIMB_RGB)

    affected_prims: List[Dict[str, Any]] = []
    binding_targets: Dict[str, str] = {}

    for prim in Usd.PrimRange(robot_prim, Usd.TraverseInstanceProxies()):
        prim_path_str = str(prim.GetPath())
        if not (prim_path_str == robot_prim_path or prim_path_str.startswith(robot_prim_path + "/")):
            raise ValueError(f"prim {prim_path_str} is outside robot root {robot_prim_path}")

        # Exclude collision prims and invisible prims
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            continue
        vis_attr = prim.GetAttribute("visibility") if prim.HasAttribute("visibility") else None
        if vis_attr and vis_attr.Get() == "invisible":
            continue

        if prim.IsA(UsdGeom.Mesh) or prim.GetTypeName() == "Mesh":
            part_class = classify_mesh_part(prim_path_str)
            target_mat = torso_mat if part_class in ("torso", "unknown") else limb_mat
            target_color = review_material_color(part_class)
            target_mat_name = torso_mat_path if part_class in ("torso", "unknown") else limb_mat_path

            # Imported URDF visuals can be instance proxies. USD forbids
            # authoring a binding on a proxy, so bind the closest authorable
            # instance root and verify the effective material again on the
            # original mesh during the independent post query.
            binding_prim = prim
            while binding_prim.IsInstanceProxy():
                binding_prim = binding_prim.GetParent()
            if not binding_prim.IsValid() or not (
                str(binding_prim.GetPath()) == robot_prim_path
                or str(binding_prim.GetPath()).startswith(robot_prim_path + "/")
            ):
                raise ValueError(f"no authorable robot binding target for {prim_path_str}")
            binding_path = str(binding_prim.GetPath())
            previous_material = binding_targets.get(binding_path)
            if previous_material is not None and previous_material != target_mat_name:
                raise ValueError(
                    f"instance binding target {binding_path} spans incompatible part classes"
                )
            if previous_material is None:
                UsdShade.MaterialBindingAPI(binding_prim).Bind(
                    target_mat,
                    bindingStrength=UsdShade.Tokens.strongerThanDescendants,
                )
                binding_targets[binding_path] = target_mat_name

            affected_prims.append({
                "prim_path": prim_path_str,
                "binding_target_path": binding_path,
                "part_class": part_class,
                "material_path": target_mat_name,
                "color_rgb": list(target_color),
                "opacity": 1.0,
                "emission": 0.0,
            })

    if not affected_prims:
        raise ValueError(f"no eligible visual mesh prims found under robot root {robot_prim_path}")

    # Re-query post inventory
    post_inventory = query_stage_robot_inventory(
        stage,
        robot_prim_path,
        query_phase="after_binding",
        robot_asset_sha256=robot_asset_sha256,
        referenced_mesh_sha256=mesh_hashes,
    )

    audit = build_material_audit(
        robot_root_path=robot_prim_path,
        affected_prims=affected_prims,
        pre_inventory=pre_inventory,
        post_inventory=post_inventory,
        robot_asset_sha256=robot_asset_sha256,
    )

    if audit_output_path is not None:
        if audit_output_path.exists():
            raise FileExistsError(f"material audit output already exists: {audit_output_path}")
        write_text_exclusive(audit_output_path, json.dumps(audit, indent=2))

    return audit


# ---------------------------------------------------------------------------
# 3D Isometric Projection Math
# ---------------------------------------------------------------------------

def isometric_project(
    x: float,
    y: float,
    z: float,
    center_x: float,
    center_y: float,
    scale_px_per_m: float,
    panel_cx: float,
    panel_cy: float,
) -> Tuple[float, float]:
    """Project a world XYZ point to 2D panel coordinates using a true isometric projection.

    Standard isometric projection:
    Screen X = panel_cx + (dx - dy) * cos(30 deg) * scale
    Screen Y = panel_cy - ((dx + dy) * sin(30 deg) + z) * scale (where +Z points upwards)
    """
    for v in (x, y, z, center_x, center_y, scale_px_per_m, panel_cx, panel_cy):
        if not math.isfinite(float(v)):
            raise ValueError("non-finite value passed to isometric_project")

    dx = x - center_x
    dy = y - center_y

    cos30 = math.cos(math.radians(30))
    sin30 = math.sin(math.radians(30))

    sx = (dx - dy) * cos30
    sy = (dx + dy) * sin30 + z

    px = panel_cx + sx * scale_px_per_m
    py = panel_cy - sy * scale_px_per_m  # screen Y points downwards in 2D image coordinates
    return px, py


def compute_3d_panel_bounds(
    plan_points_xyz: Sequence[Sequence[float]],
    actual_points_xyz: Sequence[Sequence[float]],
    occupancy_points_xyz: Sequence[Sequence[float]],
    panel_width: int = PANEL_3D_WIDTH,
    panel_height: int = PANEL_3D_HEIGHT,
) -> Dict[str, Any]:
    """Compute projection center, scale, and XYZ bounds for the 3D panel."""
    all_pts: List[Tuple[float, float, float]] = []
    for pts in (plan_points_xyz, actual_points_xyz, occupancy_points_xyz):
        for p in pts:
            if len(p) >= 3 and all(math.isfinite(float(v)) for v in p[:3]):
                all_pts.append((float(p[0]), float(p[1]), float(p[2])))

    if not all_pts:
        raise ValueError("cannot compute 3D panel bounds on empty point sets")

    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    zs = [p[2] for p in all_pts]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0

    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    span_z = max(zs) - min(zs)
    span = max(span_x, span_y, span_z, 1.0)

    usable_extent = min(panel_width, panel_height) * 0.70
    scale = usable_extent / span

    return {
        "center_x": cx,
        "center_y": cy,
        "scale_px_per_m": scale,
        "x_range": [min(xs), max(xs)],
        "y_range": [min(ys), max(ys)],
        "z_range": [min(zs), max(zs)],
        "z_span": span_z,
    }


def downsample_occupancy_points(
    points_xyz: Sequence[Sequence[float]],
    max_points: int = 1200,
) -> List[Tuple[float, float, float]]:
    """Deterministically downsample occupancy point cloud."""
    valid_points = [
        (float(p[0]), float(p[1]), float(p[2]))
        for p in points_xyz
        if len(p) >= 3 and all(math.isfinite(float(v)) for v in p[:3])
    ]
    if len(valid_points) <= max_points:
        return valid_points

    stride = max(1, len(valid_points) // max_points)
    selected = valid_points[::stride][:max_points]
    return selected


def write_text_exclusive(path: Path, text_value: str) -> None:
    """Create an evidence text file atomically; never follow or replace a path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text_value)
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# 3D Multi-View Dashboard Renderer
# ---------------------------------------------------------------------------

def render_office_review_dashboard(
    first_video_path: Path,
    side_video_path: Path,
    overview_video_path: Path,
    camera_trace_path: Path,
    material_audit_path: Path,
    ros_events_path: Path,
    metrics_path: Path,
    run_identity_path: Path,
    effective_input_path: Path,
    acceptance_config_path: Path,
    output_dashboard_video_path: Path,
    output_dashboard_metadata_path: Path,
) -> Dict[str, Any]:
    """Render synchronized 3-camera + 3D Trajectory multi-view review dashboard.

    Layout (1920x1080):
        Top Row (3 x 640x360):
            Tile 1: Preserved Office First View
            Tile 2: High-Oblique Global Camera (Ceiling cutaway)
            Tile 3: Wide Overview Camera (Elevated context)
        Bottom Row (2 x 960x720):
            Left: 3D World-Frame Trajectory & Inflated Occupancy (True Isometric)
            Right: Live Telemetry HUD & Causal Event Context
    """
    for name, p in (
        ("first_video", first_video_path),
        ("side_video", side_video_path),
        ("overview_video", overview_video_path),
        ("camera_trace", camera_trace_path),
        ("material_audit", material_audit_path),
        ("ros_events", ros_events_path),
        ("metrics", metrics_path),
        ("run_identity", run_identity_path),
        ("effective_input", effective_input_path),
        ("acceptance_config", acceptance_config_path),
    ):
        if not p.is_file():
            raise FileNotFoundError(f"required dashboard input {name} is missing: {p}")

    # Enforce strict never-overwrite policy
    for out_p in (output_dashboard_video_path, output_dashboard_metadata_path):
        out_str = str(out_p)
        if "candidate38" in out_str or "candidate39" in out_str:
            raise ValueError(f"output path cannot target candidate38/39: {out_p}")
        if out_p.exists() or out_p.is_symlink():
            raise FileExistsError(f"output file already exists (overwrite forbidden): {out_p}")

    output_dashboard_video_path.parent.mkdir(parents=True, exist_ok=True)
    output_dashboard_metadata_path.parent.mkdir(parents=True, exist_ok=True)

    # Ingest data
    with ros_events_path.open("r", encoding="utf-8") as fh:
        events = [json.loads(line) for line in fh if line.strip()]
    with metrics_path.open("r", encoding="utf-8") as fh:
        metrics = [json.loads(line) for line in fh if line.strip()]
    identity = json.loads(run_identity_path.read_text(encoding="utf-8"))
    with camera_trace_path.open("r", encoding="utf-8") as fh:
        trace_rows = [json.loads(line) for line in fh if line.strip()]

    if not events:
        raise ValueError("ros_events cannot be empty for dashboard rendering")
    if not metrics:
        raise ValueError("metrics cannot be empty for dashboard rendering")
    if not trace_rows:
        raise ValueError("camera_trace cannot be empty for dashboard rendering")
    if not isinstance(identity, dict) or not str(identity.get("config_sha256", "")).strip():
        raise ValueError("run_identity.json is missing config_sha256")

    # Plan extraction (requires valid time association)
    plans = associate_bspline_sim_times(events)
    if not plans:
        raise ValueError("no valid SCAN B-spline plans found in ros_events")
    trajectory_ids = [int(p["trajectory_id"]) for p in plans if "trajectory_id" in p]

    # Collect occupancy points
    occupancy_points_all: List[Tuple[float, float, float]] = []
    for ev in events:
        if ev.get("kind") == "occupancy_inflate":
            pts = ev.get("points_xyz") or []
            for pt in pts:
                if len(pt) >= 3 and all(math.isfinite(float(v)) for v in pt[:3]):
                    occupancy_points_all.append((float(pt[0]), float(pt[1]), float(pt[2])))

    if not occupancy_points_all:
        raise ValueError("no occupancy_inflate points found in ros_events")

    downsampled_occupancy = downsample_occupancy_points(occupancy_points_all, max_points=1200)

    # Ingest all 3 video captures
    cap_first = cv2.VideoCapture(str(first_video_path))
    cap_side = cv2.VideoCapture(str(side_video_path))
    cap_over = cv2.VideoCapture(str(overview_video_path))

    fps1 = float(cap_first.get(cv2.CAP_PROP_FPS))
    fps2 = float(cap_side.get(cv2.CAP_PROP_FPS))
    fps3 = float(cap_over.get(cv2.CAP_PROP_FPS))
    fc1 = int(cap_first.get(cv2.CAP_PROP_FRAME_COUNT))
    fc2 = int(cap_side.get(cv2.CAP_PROP_FRAME_COUNT))
    fc3 = int(cap_over.get(cv2.CAP_PROP_FRAME_COUNT))

    if not (fc1 > 0 and fc1 == fc2 == fc3 and abs(fps1 - fps2) < 0.001 and abs(fps1 - fps3) < 0.001):
        cap_first.release()
        cap_side.release()
        cap_over.release()
        raise ValueError(f"video stream mismatch: first(fps={fps1}, frames={fc1}), side(fps={fps2}, frames={fc2}), overview(fps={fps3}, frames={fc3})")

    frame_count = fc1
    fps = fps1
    if len(trace_rows) != frame_count:
        cap_first.release()
        cap_side.release()
        cap_over.release()
        raise ValueError(f"camera trace rows {len(trace_rows)} != raw frame count {frame_count}")

    all_plan_points: List[Tuple[float, float, float]] = []
    for plan in plans:
        pts = plan.get("sampled_points") or plan.get("sampled_points_xyz") or []
        all_plan_points.extend(pts)

    all_actual_points: List[Tuple[float, float, float]] = [
        (float(m["root_pos_w"][0]), float(m["root_pos_w"][1]), float(m["root_pos_w"][2]))
        for m in metrics
        if "root_pos_w" in m and len(m["root_pos_w"]) >= 3
    ]
    if not all_actual_points:
        raise ValueError("metrics contains no valid root_pos_w series")

    panel_bounds = compute_3d_panel_bounds(
        all_plan_points,
        all_actual_points,
        downsampled_occupancy,
        panel_width=PANEL_3D_WIDTH,
        panel_height=PANEL_3D_HEIGHT,
    )

    # Launch direct H.264 high quality encoder via ffmpeg pipe
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required for direct single-generation H.264 dashboard encoding")

    cmd = [
        ffmpeg,
        "-hide_banner", "-loglevel", "error", "-n",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{DASHBOARD_WIDTH}x{DASHBOARD_HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(int(round(fps))),
        "-i", "-",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-preset", "medium",
        "-crf", "16",
        "-pix_fmt", "yuv420p",
        "-color_range", "tv",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-colorspace", "bt709",
        "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1",
        "-movflags", "+faststart",
        str(output_dashboard_video_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    try:
        active_plan_idx = -1
        accumulated_actual_xyz: List[Tuple[float, float, float]] = []

        for frame_idx in range(frame_count):
            r1, f1 = cap_first.read()
            r2, f2 = cap_side.read()
            r3, f3 = cap_over.read()
            if not r1 or not r2 or not r3 or f1 is None or f2 is None or f3 is None:
                raise ValueError(f"failed to read frame {frame_idx} from one of the raw video streams")

            if frame_idx < len(trace_rows):
                sim_time = float(trace_rows[frame_idx]["sim_time_seconds"])
                step_val = int(trace_rows[frame_idx]["step"])
                root_pos = trace_rows[frame_idx]["root_pos_w"]
            else:
                sim_time = float(frame_idx) / fps
                step_val = frame_idx * 2
                root_pos = all_actual_points[min(frame_idx, len(all_actual_points) - 1)]

            metric_row = metrics[min(step_val, len(metrics) - 1)] if metrics else {}
            accumulated_actual_xyz.append((float(root_pos[0]), float(root_pos[1]), float(root_pos[2])))

            while active_plan_idx + 1 < len(plans) and plans[active_plan_idx + 1]["effective_sim_time_seconds"] <= sim_time:
                active_plan_idx += 1

            active_plan = plans[active_plan_idx] if active_plan_idx >= 0 else None
            active_traj_id = active_plan["trajectory_id"] if active_plan else "unknown"
            # 1. Top Row: 3 Camera Tiles (each 640x360)
            t1 = cv2.resize(f1, (PANEL_CAM_WIDTH, PANEL_CAM_HEIGHT))
            cv2.rectangle(t1, (10, 10), (320, 36), (20, 20, 20), -1)
            cv2.putText(t1, "1. Preserved Office First View", (18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

            t2 = cv2.resize(f2, (PANEL_CAM_WIDTH, PANEL_CAM_HEIGHT))
            cv2.rectangle(t2, (10, 10), (575, 36), (20, 20, 20), -1)
            cv2.putText(t2, "2. High-Oblique Global View (Ceiling Cutaway)", (18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2, cv2.LINE_AA)

            t3 = cv2.resize(f3, (PANEL_CAM_WIDTH, PANEL_CAM_HEIGHT))
            cv2.rectangle(t3, (10, 10), (320, 36), (20, 20, 20), -1)
            cv2.putText(t3, "3. Elevated Overview", (18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

            # 2. Bottom-Left: 3D Trajectory Panel (960x720)
            p3d = np.full((PANEL_3D_HEIGHT, PANEL_3D_WIDTH, 3), (28, 32, 42), dtype=np.uint8)
            panel_cx = PANEL_3D_WIDTH / 2.0
            panel_cy = PANEL_3D_HEIGHT / 2.0 + 40.0
            scale_px = panel_bounds["scale_px_per_m"]
            cx = panel_bounds["center_x"]
            cy = panel_bounds["center_y"]

            # Draw 3D isometric axes
            origin_px = isometric_project(cx, cy, 0.0, cx, cy, scale_px, panel_cx, panel_cy)
            axis_x_px = isometric_project(cx + 2.0, cy, 0.0, cx, cy, scale_px, panel_cx, panel_cy)
            axis_y_px = isometric_project(cx, cy + 2.0, 0.0, cx, cy, scale_px, panel_cx, panel_cy)
            axis_z_px = isometric_project(cx, cy, 1.5, cx, cy, scale_px, panel_cx, panel_cy)

            cv2.line(p3d, (int(origin_px[0]), int(origin_px[1])), (int(axis_x_px[0]), int(axis_x_px[1])), (80, 80, 240), 2, cv2.LINE_AA)
            cv2.putText(p3d, "+X (2m)", (int(axis_x_px[0]) + 5, int(axis_x_px[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 240), 1, cv2.LINE_AA)

            cv2.line(p3d, (int(origin_px[0]), int(origin_px[1])), (int(axis_y_px[0]), int(axis_y_px[1])), (80, 240, 80), 2, cv2.LINE_AA)
            cv2.putText(p3d, "+Y (2m)", (int(axis_y_px[0]) + 5, int(axis_y_px[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 240, 80), 1, cv2.LINE_AA)

            cv2.line(p3d, (int(origin_px[0]), int(origin_px[1])), (int(axis_z_px[0]), int(axis_z_px[1])), (240, 180, 80), 2, cv2.LINE_AA)
            cv2.putText(p3d, "+Z (1.5m)", (int(axis_z_px[0]), int(axis_z_px[1]) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (240, 180, 80), 1, cv2.LINE_AA)

            # Draw inflated occupancy voxels
            for pt in downsampled_occupancy:
                px, py = isometric_project(pt[0], pt[1], pt[2], cx, cy, scale_px, panel_cx, panel_cy)
                if 0 <= px < PANEL_3D_WIDTH and 0 <= py < PANEL_3D_HEIGHT:
                    cv2.circle(p3d, (int(px), int(py)), 2, SCAN_OCCUPANCY_COLOR_BGR, -1)

            # Draw accumulated actual physical path
            if len(accumulated_actual_xyz) >= 2:
                actual_proj = [
                    isometric_project(pt[0], pt[1], pt[2], cx, cy, scale_px, panel_cx, panel_cy)
                    for pt in accumulated_actual_xyz
                ]
                for p1, p2 in zip(actual_proj, actual_proj[1:]):
                    cv2.line(p3d, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), ACTUAL_COLOR_BGR, 2, cv2.LINE_AA)

            # Current robot position
            curr_pos_px = isometric_project(root_pos[0], root_pos[1], root_pos[2], cx, cy, scale_px, panel_cx, panel_cy)
            cv2.circle(p3d, (int(curr_pos_px[0]), int(curr_pos_px[1])), 6, ACTUAL_COLOR_BGR, -1)
            cv2.circle(p3d, (int(curr_pos_px[0]), int(curr_pos_px[1])), 8, (255, 255, 255), 1)

            # Active planned B-spline
            if active_plan is not None:
                plan_pts = active_plan.get("sampled_points") or active_plan.get("sampled_points_xyz") or []
                if len(plan_pts) >= 2:
                    plan_proj = [
                        isometric_project(pt[0], pt[1], pt[2], cx, cy, scale_px, panel_cx, panel_cy)
                        for pt in plan_pts
                    ]
                    for p1, p2 in zip(plan_proj, plan_proj[1:]):
                        cv2.line(p3d, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), PLAN_COLOR_BGR, 3, cv2.LINE_AA)

            # 3D Panel Titles & Legend
            cv2.rectangle(p3d, (10, 10), (480, 42), (20, 20, 20), -1)
            cv2.putText(p3d, "3D World Trajectory (True Isometric)", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)

            cv2.line(p3d, (20, 60), (45, 60), PLAN_COLOR_BGR, 3, cv2.LINE_AA)
            cv2.putText(p3d, "SCAN Planned B-Spline (World XYZ)", (52, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)
            cv2.line(p3d, (20, 80), (45, 80), ACTUAL_COLOR_BGR, 2, cv2.LINE_AA)
            cv2.putText(p3d, "Physical Root Actual (World XYZ)", (52, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)
            cv2.circle(p3d, (32, 100), 3, SCAN_OCCUPANCY_COLOR_BGR, -1)
            cv2.putText(p3d, "Captured Inflated Occupancy (World XYZ)", (52, 104), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)

            # 3. Bottom-Right: Telemetry & Causal Events Panel (960x720)
            ptelem = np.full((PANEL_TELEM_HEIGHT, PANEL_TELEM_WIDTH, 3), (20, 24, 30), dtype=np.uint8)
            cv2.rectangle(ptelem, (10, 10), (480, 42), (20, 20, 20), -1)
            cv2.putText(ptelem, "Telemetry & Causal Event Context", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)

            # Read actual metric fields or show 'unknown'
            lin_vel = metric_row.get("root_lin_vel_w")
            speed_str = f"{math.hypot(float(lin_vel[0]), float(lin_vel[1])):5.2f} m/s" if lin_vel else "unknown"
            cmd = metric_row.get("applied_command")
            cmd_str = f"vx={float(cmd[0]):+4.2f}, vy={float(cmd[1]):+4.2f}, wz={float(cmd[2]):+4.2f}" if cmd else "unknown"
            contact_val = metric_row.get("supported_contact_ratio")
            contact_str = f"{float(contact_val) * 100:5.1f}%" if contact_val is not None else "unknown"
            nonfoot_force_val = metric_row.get("nonfoot_contact_max_force_n")
            nonfoot_str = f"{float(nonfoot_force_val):5.1f} N" if nonfoot_force_val is not None else "unknown"

            lines = [
                f"Simulation Time:    {sim_time:6.2f} s   (Physics Step {step_val})",
                f"Physical Root Pose: X={root_pos[0]:+6.2f} m, Y={root_pos[1]:+6.2f} m, Z={root_pos[2]:+6.2f} m",
                f"Physical Speed:     {speed_str}",
                f"Applied Command:    {cmd_str}",
                f"Contact Support:    {contact_str}  (Compliant 4-foot ground contact)",
                f"Max Nonfoot Force:  {nonfoot_str}",
                "----------------------------------------------------------------",
                f"Active SCAN Plan:   ID={active_traj_id}  (Total plans: {len(plans)})",
                f"Occupancy Samples:  {len(downsampled_occupancy)} points (from {len(occupancy_points_all)} raw)",
                "Claim Boundary:     Moving-occupancy B-spline replanning evaluation only.",
            ]

            y_offset = 80
            for line in lines:
                color = (255, 220, 100) if "Active SCAN" in line else (220, 220, 220)
                cv2.putText(ptelem, line, (24, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.50, color, 1, cv2.LINE_AA)
                y_offset += 38

            # Assemble full 1920x1080 canvas
            canvas = np.zeros((DASHBOARD_HEIGHT, DASHBOARD_WIDTH, 3), dtype=np.uint8)
            canvas[0:PANEL_CAM_HEIGHT, 0:PANEL_CAM_WIDTH] = t1
            canvas[0:PANEL_CAM_HEIGHT, PANEL_CAM_WIDTH:PANEL_CAM_WIDTH*2] = t2
            canvas[0:PANEL_CAM_HEIGHT, PANEL_CAM_WIDTH*2:DASHBOARD_WIDTH] = t3
            canvas[PANEL_CAM_HEIGHT:DASHBOARD_HEIGHT, 0:PANEL_3D_WIDTH] = p3d
            canvas[PANEL_CAM_HEIGHT:DASHBOARD_HEIGHT, PANEL_3D_WIDTH:DASHBOARD_WIDTH] = ptelem

            proc.stdin.write(canvas.tobytes())

    finally:
        cap_first.release()
        cap_side.release()
        cap_over.release()
        if proc.stdin:
            proc.stdin.close()
        proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg dashboard encoding exited with error code {proc.returncode}")

    input_hashes = {
        "first_video": sha256_file(first_video_path),
        "side_video": sha256_file(side_video_path),
        "overview_video": sha256_file(overview_video_path),
        "camera_trace": sha256_file(camera_trace_path),
        "material_audit": sha256_file(material_audit_path),
        "ros_events": sha256_file(ros_events_path),
        "metrics": sha256_file(metrics_path),
        "run_identity": sha256_file(run_identity_path),
        "effective_input": sha256_file(effective_input_path),
        "acceptance_config": sha256_file(acceptance_config_path),
    }
    output_hash = sha256_file(output_dashboard_video_path)

    metadata = {
        "schema_version": 4,
        "layout": "three_cameras_and_two_bottom_panels_1920x1080",
        "resolution": [DASHBOARD_WIDTH, DASHBOARD_HEIGHT],
        "projection": {
            "type": "isometric",
            "center_xy_m": [float(panel_bounds["center_x"]), float(panel_bounds["center_y"])],
            "scale_px_per_m": float(panel_bounds["scale_px_per_m"]),
            "x_range_m": panel_bounds["x_range"],
            "y_range_m": panel_bounds["y_range"],
            "z_range_m": panel_bounds["z_range"],
            "z_span_m": float(panel_bounds["z_span"]),
        },
        "input_sha256": input_hashes,
        "output_sha256": output_hash,
        "frame_count": int(frame_count),
        "r_frame_rate": f"{int(round(fps))}/1",
        "fps": float(fps),
        "quality_profile": dict(
            (identity.get("office_review_presentation") or {}).get(
                "quality_profile"
            )
            or frozen_quality_profile()
        ),
        "frame_to_simulator_time": [
            {
                "frame_index": int(row["frame_index"]),
                "step": int(row["step"]),
                "sim_time_seconds": float(row["sim_time_seconds"]),
                "state_snapshot_identity": str(row["state_snapshot_identity"]),
            }
            for row in trace_rows
        ],
        "trajectory_ids": [int(t) for t in trajectory_ids],
        "plan_sample_count": sum(len(plan["sampled_points"]) for plan in plans),
        "root_sample_count": len(all_actual_points),
        "occupancy_raw_count": len(occupancy_points_all),
        "occupancy_sample_count": len(downsampled_occupancy),
        "occupancy_sampling": {"algorithm": "stable_input_order_stride", "maximum_count": 1200, "seed": None},
        "source_hashes": identity.get("office_review_presentation", {}).get("source_hashes", {}),
        "encoder": "ffmpeg libx264 high crf16 yuv420p bt709 direct stream",
        "claim_boundary": (
            "Deterministic multi-view review dashboard generated strictly from raw MP4 streams, "
            "SCAN B-spline plans, Isaac physical root poses, and captured SCAN inflated occupancy."
        ),
    }

    write_text_exclusive(output_dashboard_metadata_path, json.dumps(metadata, indent=2))
    return metadata


# ---------------------------------------------------------------------------
# Aggregate Fail-Closed Presentation Validator
# ---------------------------------------------------------------------------

def _probe_video_strict(video_path: Path) -> Dict[str, Any]:
    """Probe video stream using ffprobe with strict rational frame rate."""
    if not video_path.is_file():
        raise FileNotFoundError(f"video file not found: {video_path}")

    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_name,pix_fmt,width,height,nb_frames,r_frame_rate,duration",
        "-of", "json", str(video_path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except Exception as e:
        raise ValueError(f"ffprobe failed for {video_path}: {e}") from e

    data = json.loads(res.stdout)
    streams = data.get("streams", [])
    if not streams:
        raise ValueError(f"no video streams in {video_path}")

    s = streams[0]
    r_fps_str = s.get("r_frame_rate", "0/0")
    try:
        r_frac = fractions.Fraction(r_fps_str)
        fps_float = float(r_frac)
    except Exception:
        fps_float = 0.0

    return {
        "codec": s.get("codec_name"),
        "pix_fmt": s.get("pix_fmt"),
        "width": int(s.get("width", 0)),
        "height": int(s.get("height", 0)),
        "nb_frames": int(s.get("nb_frames", 0)),
        "r_frame_rate": r_fps_str,
        "fps": fps_float,
        "duration": float(s.get("duration", 0.0)),
    }


def _full_decode_video_frames(video_path: Path) -> int:
    """Perform full frame-by-frame decode check. Returns total decoded frames."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"cannot open video for decoding: {video_path}")
    count = 0
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        count += 1
    cap.release()
    return count


def _validate_office_review_presentation_legacy(
    first_video_path: Path,
    side_video_path: Path,
    overview_video_path: Path,
    camera_trace_path: Path,
    material_audit_path: Path,
    dashboard_video_path: Path,
    dashboard_metadata_path: Path,
    ros_events_path: Path,
    metrics_path: Path,
    run_identity_path: Path,
) -> Dict[str, Any]:
    """Aggregate fail-closed presentation validator."""
    issues: List[str] = []
    checks: Dict[str, Any] = {}

    mandatory_paths = {
        "first_video": first_video_path,
        "side_video": side_video_path,
        "overview_video": overview_video_path,
        "camera_trace": camera_trace_path,
        "material_audit": material_audit_path,
        "dashboard_video": dashboard_video_path,
        "dashboard_metadata": dashboard_metadata_path,
        "ros_events": ros_events_path,
        "metrics": metrics_path,
        "run_identity": run_identity_path,
    }

    # 1. Target & Existence check
    for name, p in mandatory_paths.items():
        if p is None:
            issues.append(f"mandatory path {name} is None")
            continue
        p_str = str(p)
        if "candidate38" in p_str or "candidate39" in p_str:
            issues.append(f"path targets immutable candidate38/39: {p}")
        if not p.is_file():
            issues.append(f"mandatory presentation file is missing: {p}")

    if issues:
        return {"passed": False, "issues": issues, "checks": checks}

    # 2. Video Probing & Format Verification
    try:
        p_first = _probe_video_strict(first_video_path)
        p_side = _probe_video_strict(side_video_path)
        p_over = _probe_video_strict(overview_video_path)
        p_dash = _probe_video_strict(dashboard_video_path)
    except Exception as e:
        return {"passed": False, "issues": [f"video probe failed: {e}"], "checks": checks}

    checks["probes"] = {"first": p_first, "side": p_side, "overview": p_over, "dashboard": p_dash}

    for name, pr in (("first", p_first), ("side", p_side), ("overview", p_over), ("dashboard", p_dash)):
        if pr["codec"] != "h264":
            issues.append(f"{name} video codec is not h264: {pr['codec']}")
        if pr["pix_fmt"] != "yuv420p":
            issues.append(f"{name} video pix_fmt is not yuv420p: {pr['pix_fmt']}")

    profile = frozen_quality_profile()
    if not (
        p_first["width"]
        == p_side["width"]
        == p_over["width"]
        == int(profile["resolution_width"])
    ):
        issues.append(f"raw video width mismatch: first={p_first['width']}, side={p_side['width']}, over={p_over['width']}")
    if not (
        p_first["height"]
        == p_side["height"]
        == p_over["height"]
        == int(profile["resolution_height"])
    ):
        issues.append(f"raw video height mismatch: first={p_first['height']}, side={p_side['height']}, over={p_over['height']}")
    if p_dash["width"] != DASHBOARD_WIDTH or p_dash["height"] != DASHBOARD_HEIGHT:
        issues.append(f"dashboard resolution mismatch: {p_dash['width']}x{p_dash['height']} != {DASHBOARD_WIDTH}x{DASHBOARD_HEIGHT}")

    if not (p_first["r_frame_rate"] == p_side["r_frame_rate"] == p_over["r_frame_rate"]):
        issues.append(f"raw video r_frame_rate mismatch: first={p_first['r_frame_rate']}, side={p_side['r_frame_rate']}, over={p_over['r_frame_rate']}")

    # 3. Full Frame-by-Frame Video Decoding
    try:
        dec_first = _full_decode_video_frames(first_video_path)
        dec_side = _full_decode_video_frames(side_video_path)
        dec_over = _full_decode_video_frames(overview_video_path)
        dec_dash = _full_decode_video_frames(dashboard_video_path)
    except Exception as e:
        issues.append(f"full video decode failed: {e}")
        dec_first, dec_side, dec_over, dec_dash = 0, 0, 0, 0

    checks["decoded_frames"] = {"first": dec_first, "side": dec_side, "overview": dec_over, "dashboard": dec_dash}
    if dec_first <= 0 or dec_side <= 0 or dec_over <= 0 or dec_dash <= 0:
        issues.append("one or more video streams decoded 0 frames")
    if not (dec_first == dec_side == dec_over == dec_dash):
        issues.append(f"decoded frame count mismatch: first={dec_first}, side={dec_side}, over={dec_over}, dash={dec_dash}")

    # 4. Content Distinction (3 views cannot be identical copies)
    h_first = sha256_file(first_video_path)
    h_side = sha256_file(side_video_path)
    h_over = sha256_file(overview_video_path)
    if h_first == h_side:
        issues.append("side video has identical SHA-256 to first video (duplicate camera stream detected)")
    if h_first == h_over:
        issues.append("overview video has identical SHA-256 to first video (duplicate camera stream detected)")
    if h_side == h_over:
        issues.append("overview video has identical SHA-256 to side video (duplicate camera stream detected)")

    # 5. Camera Trace Validation
    try:
        with camera_trace_path.open("r", encoding="utf-8") as fh:
            trace_lines = [json.loads(line) for line in fh if line.strip()]
    except Exception as e:
        issues.append(f"failed to read camera_trace.jsonl: {e}")
        trace_lines = []

    checks["trace_row_count"] = len(trace_lines)
    if len(trace_lines) != dec_first:
        issues.append(f"camera trace row count ({len(trace_lines)}) != decoded video frames ({dec_first})")

    expected_run_id = None
    last_step = -1
    last_sim_time = -1.0
    last_side_eye = None
    last_over_eye = None
    first_side = None

    for idx, row in enumerate(trace_lines):
        if row.get("frame_index") != idx:
            issues.append(f"trace row {idx} frame_index mismatch: {row.get('frame_index')} != {idx}")
            break

        run_id = row.get("run_identity")
        if not run_id or not isinstance(run_id, str) or not run_id.strip():
            issues.append(f"trace row {idx} missing or empty run_identity")
        elif expected_run_id is None:
            expected_run_id = run_id
        elif run_id != expected_run_id:
            issues.append(f"trace row {idx} run_identity mismatch: {run_id} != {expected_run_id}")

        step = row.get("step")
        sim_time = row.get("sim_time_seconds")
        if step is None or not isinstance(step, int) or step < last_step:
            issues.append(f"trace row {idx} non-monotonic step: {step} (previous {last_step})")
        if sim_time is None or not math.isfinite(float(sim_time)) or (idx > 0 and float(sim_time) <= last_sim_time):
            issues.append(f"trace row {idx} non-monotonic sim_time: {sim_time} (previous {last_sim_time})")

        last_step = step if step is not None else last_step
        last_sim_time = float(sim_time) if sim_time is not None else last_sim_time

        # Validate view poses
        first_v = row.get("first_view", {})
        side_v = row.get("side_follow", {})
        over_v = row.get("overview", {})

        for vname, vdata in (("first_view", first_v), ("side_follow", side_v), ("overview", over_v)):
            re_eye = vdata.get("eye") or vdata.get("realized_eye")
            re_tgt = vdata.get("target") or vdata.get("realized_target")
            if not re_eye or len(re_eye) != 3 or not all(math.isfinite(float(v)) for v in re_eye):
                issues.append(f"trace row {idx} {vname} invalid eye: {re_eye}")
            if not re_tgt or len(re_tgt) != 3 or not all(math.isfinite(float(v)) for v in re_tgt):
                issues.append(f"trace row {idx} {vname} invalid target: {re_tgt}")

        # Side constancy
        side_val = side_v.get("configured_side")
        if side_val is None:
            issues.append(f"trace row {idx} missing side_follow.configured_side")
        elif first_side is None:
            first_side = float(side_val)
        elif abs(float(side_val) - first_side) > 1e-4:
            issues.append(f"trace row {idx} side flipped mid-run: {side_val} != {first_side}")

        # Motion bounds
        if idx > 0:
            dt = float(side_v.get("dt", 0.0))
            if not math.isfinite(dt) or dt <= 0.0:
                issues.append(f"trace row {idx} invalid dt: {dt}")

            max_eye_speed = float(side_v.get("max_eye_speed_mps", SIDE_CAMERA_DEFAULTS["max_eye_speed_mps"]))
            side_re_eye = side_v.get("realized_eye", [0, 0, 0])
            if last_side_eye is not None and len(side_re_eye) == 3:
                actual_disp = math.sqrt(sum((float(side_re_eye[k]) - last_side_eye[k]) ** 2 for k in range(3)))
                max_allowed = max_eye_speed * dt + 1e-3
                if actual_disp > max_allowed:
                    issues.append(f"trace row {idx} side eye displacement {actual_disp:.4f}m exceeds max allowed {max_allowed:.4f}m")

            over_max_eye_speed = float(over_v.get("max_eye_speed_mps", OVERVIEW_CAMERA_DEFAULTS["max_eye_speed_mps"]))
            over_re_eye = over_v.get("realized_eye", [0, 0, 0])
            if last_over_eye is not None and len(over_re_eye) == 3:
                over_disp = math.sqrt(sum((float(over_re_eye[k]) - last_over_eye[k]) ** 2 for k in range(3)))
                over_max_allowed = over_max_eye_speed * dt + 1e-3
                if over_disp > over_max_allowed:
                    issues.append(f"trace row {idx} overview eye displacement {over_disp:.4f}m exceeds max allowed {over_max_allowed:.4f}m")

        if side_v.get("realized_eye"):
            last_side_eye = (float(side_v["realized_eye"][0]), float(side_v["realized_eye"][1]), float(side_v["realized_eye"][2]))
        if over_v.get("realized_eye"):
            last_over_eye = (float(over_v["realized_eye"][0]), float(over_v["realized_eye"][1]), float(over_v["realized_eye"][2]))

    # 6. Provenance & Z Sensitivity
    try:
        with ros_events_path.open("r", encoding="utf-8") as fh:
            events = [json.loads(line) for line in fh if line.strip()]
        with metrics_path.open("r", encoding="utf-8") as fh:
            metrics = [json.loads(line) for line in fh if line.strip()]
    except Exception as e:
        issues.append(f"failed to read events/metrics: {e}")
        events, metrics = [], []

    if not events:
        issues.append("ros_events is empty")
    if not metrics:
        issues.append("metrics is empty")

    plans = []
    if events:
        try:
            plans = associate_bspline_sim_times(events)
        except Exception as e:
            issues.append(f"B-spline time association failed: {e}")

    if not plans:
        issues.append("no valid SCAN B-spline plans in ros_events")

    occupancy_pts = []
    for ev in events:
        if ev.get("kind") == "occupancy_inflate":
            for pt in ev.get("points_xyz") or []:
                if len(pt) >= 3 and all(math.isfinite(float(v)) for v in pt[:3]):
                    occupancy_pts.append(pt)

    if not occupancy_pts:
        issues.append("no occupancy_inflate points in ros_events")

    actual_roots = [m.get("root_pos_w") for m in metrics if m.get("root_pos_w") and len(m["root_pos_w"]) >= 3]
    if not actual_roots:
        issues.append("no valid root_pos_w series in metrics")

    # Real Z variation check
    all_zs = [p[2] for plan in plans for p in plan.get("sampled_points_xyz", [])] + [r[2] for r in actual_roots]
    if all_zs:
        z_span = max(all_zs) - min(all_zs)
        if z_span < 1e-4:
            issues.append("zero Z variation across planned/actual trajectory (flat 2D masquerading as 3D)")

    # 7. Material Audit Verification
    try:
        audit_data = json.loads(material_audit_path.read_text(encoding="utf-8"))
    except Exception as e:
        issues.append(f"failed to parse material audit: {e}")
        audit_data = {}

    if not audit_data.get("robot_asset_sha256"):
        issues.append("material audit missing robot_asset_sha256")
    if audit_data.get("total_affected_prims", 0) <= 0:
        issues.append("material audit has 0 affected prims")
    if not audit_data.get("physics_inventory_unchanged", False):
        issues.append("material audit reports modified physics/collision inventory")

    for prim in audit_data.get("affected_prims", []):
        p_path = str(prim.get("prim_path", ""))
        if "floor" in p_path.lower() or "office" in p_path.lower():
            issues.append(f"material audit contains non-robot scene prim: {p_path}")

    # 8. Metadata Hashes
    try:
        meta_data = json.loads(dashboard_metadata_path.read_text(encoding="utf-8"))
    except Exception as e:
        issues.append(f"failed to parse dashboard metadata: {e}")
        meta_data = {}

    meta_input_hashes = meta_data.get("input_sha256", {})
    expected_input_hashes = {
        "first_video": h_first,
        "side_video": h_side,
        "overview_video": h_over,
        "camera_trace": sha256_file(camera_trace_path),
        "material_audit": sha256_file(material_audit_path),
        "ros_events": sha256_file(ros_events_path),
        "metrics": sha256_file(metrics_path),
        "run_identity": sha256_file(run_identity_path),
    }

    for k, exp_h in expected_input_hashes.items():
        rec_h = meta_input_hashes.get(k)
        if rec_h != exp_h:
            issues.append(f"metadata input_sha256 mismatch for {k}: {rec_h} != {exp_h}")

    actual_out_h = sha256_file(dashboard_video_path)
    rec_out_h = meta_data.get("output_sha256")
    if rec_out_h != actual_out_h:
        issues.append(f"metadata output_sha256 mismatch: {rec_out_h} != {actual_out_h}")

    passed = len(issues) == 0
    return {
        "passed": passed,
        "issues": issues,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Strict evidence validator (schema v4)
# ---------------------------------------------------------------------------

def _probe_video_evidence(video_path: Path) -> Dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe is required for presentation validation")
    result = subprocess.run(
        [
            ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries",
            "stream=codec_name,profile,pix_fmt,width,height,nb_frames,nb_read_frames,r_frame_rate,color_range,color_space,color_transfer,color_primaries",
            "-of", "json", str(video_path),
        ],
        capture_output=True, text=True, check=True,
    )
    streams = json.loads(result.stdout).get("streams") or []
    if len(streams) != 1:
        raise ValueError(f"expected one video stream in {video_path}, got {len(streams)}")
    stream = streams[0]
    rate = str(stream.get("r_frame_rate", "0/0"))
    fps = float(fractions.Fraction(rate))
    def _integer(name: str) -> int:
        value = stream.get(name)
        return 0 if value in (None, "N/A") else int(value)
    return {
        "codec": stream.get("codec_name"),
        "profile": stream.get("profile"),
        "pix_fmt": stream.get("pix_fmt"),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "nb_frames": _integer("nb_frames"),
        "nb_read_frames": _integer("nb_read_frames"),
        "r_frame_rate": rate,
        "fps": fps,
        "color_range": stream.get("color_range"),
        "color_space": stream.get("color_space"),
        "color_transfer": stream.get("color_transfer"),
        "color_primaries": stream.get("color_primaries"),
    }


def _decode_video_evidence(video_path: Path) -> int:
    """Decode every frame with ffmpeg -xerror and count framemd5 records."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required for presentation validation")
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-xerror", "-i", str(video_path),
         "-map", "0:v:0", "-f", "framemd5", "-"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"error-sensitive decode failed for {video_path}: {result.stderr.strip()}")
    return sum(1 for line in result.stdout.splitlines() if line and not line.startswith("#"))


def _sample_video_content(video_path: Path, frame_count: int) -> np.ndarray:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"cannot open video for content comparison: {video_path}")
    samples: List[np.ndarray] = []
    try:
        for index in sorted({0, max(0, frame_count // 2), max(0, frame_count - 1)}):
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok or frame is None:
                raise ValueError(f"cannot decode comparison frame {index} from {video_path}")
            gray = cv2.cvtColor(cv2.resize(frame, (96, 54)), cv2.COLOR_BGR2GRAY)
            samples.append(gray.astype(np.float32))
    finally:
        capture.release()
    return np.stack(samples)


def _finite_vector(value: Any, length: int) -> Optional[List[float]]:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        return None
    try:
        converted = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    return converted if all(math.isfinite(item) for item in converted) else None


def _read_jsonl_strict(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            rows.append(row)
    return rows


def _motion_distance(left: Sequence[float], right: Sequence[float]) -> float:
    return math.sqrt(sum((float(left[index]) - float(right[index])) ** 2 for index in range(3)))


def validate_office_review_presentation(
    first_video_path: Path,
    side_video_path: Path,
    overview_video_path: Path,
    camera_trace_path: Path,
    material_audit_path: Path,
    dashboard_video_path: Path,
    dashboard_metadata_path: Path,
    ros_events_path: Path,
    metrics_path: Path,
    run_identity_path: Path,
    effective_input_path: Path,
    acceptance_config_path: Path,
) -> Dict[str, Any]:
    """Validate the complete review evidence package without propagating malformed-input errors."""
    issues: List[str] = []
    checks: Dict[str, Any] = {}
    paths = {
        "first_video": first_video_path, "side_video": side_video_path,
        "overview_video": overview_video_path, "camera_trace": camera_trace_path,
        "material_audit": material_audit_path, "dashboard_video": dashboard_video_path,
        "dashboard_metadata": dashboard_metadata_path, "ros_events": ros_events_path,
        "metrics": metrics_path, "run_identity": run_identity_path,
        "effective_input": effective_input_path, "acceptance_config": acceptance_config_path,
    }
    try:
        for name, path in paths.items():
            if path is None:
                issues.append(f"mandatory path {name} is None")
                continue
            if any(token in str(path).lower() for token in ("candidate38", "candidate39")):
                issues.append(f"path targets immutable candidate evidence: {path}")
            if not path.is_file() or path.is_symlink():
                issues.append(f"mandatory regular file {name} is missing or a symlink: {path}")
        if issues:
            return {"passed": False, "issues": issues, "checks": checks}

        profile = frozen_quality_profile()
        probes: Dict[str, Dict[str, Any]] = {}
        decoded: Dict[str, int] = {}
        video_paths = {
            "first": first_video_path, "side": side_video_path,
            "overview": overview_video_path, "dashboard": dashboard_video_path,
        }
        for name, path in video_paths.items():
            probe = _probe_video_evidence(path)
            probes[name] = probe
            decoded[name] = _decode_video_evidence(path)
            if probe["codec"] != profile["codec"]:
                issues.append(f"{name} codec {probe['codec']} != {profile['codec']}")
            if str(probe["profile"]).lower() != str(profile["profile"]).lower():
                issues.append(f"{name} profile {probe['profile']} != High")
            if probe["pix_fmt"] != profile["pixel_format"]:
                issues.append(f"{name} pixel format {probe['pix_fmt']} != {profile['pixel_format']}")
            expected_resolution = (
                (DASHBOARD_WIDTH, DASHBOARD_HEIGHT)
                if name == "dashboard"
                else (
                    int(profile["resolution_width"]),
                    int(profile["resolution_height"]),
                )
            )
            if (probe["width"], probe["height"]) != expected_resolution:
                issues.append(
                    f"{name} resolution {probe['width']}x{probe['height']} is not "
                    f"{expected_resolution[0]}x{expected_resolution[1]}"
                )
            if probe["fps"] < float(profile["min_fps"]):
                issues.append(f"{name} frame rate {probe['r_frame_rate']} is below {profile['min_fps']} fps")
            for field, expected in (
                ("color_range", profile["color_range"]), ("color_space", profile["color_matrix"]),
                ("color_transfer", profile["color_transfer"]), ("color_primaries", profile["color_primaries"]),
            ):
                if probe[field] != expected:
                    issues.append(f"{name} {field} {probe[field]} != {expected}")
            declared = probe["nb_read_frames"] or probe["nb_frames"]
            if declared <= 0 or decoded[name] != declared:
                issues.append(f"{name} decoded frame count {decoded[name]} != declared {declared}")
        checks["video_probes"] = probes
        checks["decoded_frames"] = decoded
        exact_rates = {probe["r_frame_rate"] for probe in probes.values()}
        frame_counts = set(decoded.values())
        if len(exact_rates) != 1:
            issues.append(f"video rational frame rates differ: {sorted(exact_rates)}")
        if len(frame_counts) != 1:
            issues.append(f"video decoded frame counts differ: {decoded}")

        hashes = {name: sha256_file(path) for name, path in video_paths.items()}
        raw_hashes = [hashes[name] for name in ("first", "side", "overview")]
        if len(set(raw_hashes)) != 3:
            issues.append("raw camera video hashes are not distinct")
        signatures = {
            name: _sample_video_content(video_paths[name], decoded[name])
            for name in ("first", "side", "overview")
        }
        content_mae: Dict[str, float] = {}
        for left, right in (("first", "side"), ("first", "overview"), ("side", "overview")):
            mae = float(np.mean(np.abs(signatures[left] - signatures[right])))
            content_mae[f"{left}_vs_{right}"] = mae
            if mae < 2.0:
                issues.append(f"{left} and {right} image content is not measurably distinct (MAE={mae:.3f})")
        checks["content_mae"] = content_mae

        identity = json.loads(run_identity_path.read_text(encoding="utf-8"))
        acceptance = json.loads(acceptance_config_path.read_text(encoding="utf-8"))
        effective_input = effective_input_path.read_text(encoding="utf-8").strip()
        effective_values: Dict[str, str] = {}
        for line in effective_input.splitlines():
            key, separator, value = line.partition("=")
            if separator:
                effective_values[key.strip()] = value.strip()
        try:
            requested_duration_seconds = float(effective_values["duration_seconds"])
        except (KeyError, TypeError, ValueError):
            requested_duration_seconds = 0.0
            issues.append("effective input duration_seconds is missing or invalid")
        if not math.isfinite(requested_duration_seconds) or requested_duration_seconds <= 0.0:
            issues.append("effective input duration_seconds must be finite and positive")
        declared_profile = (
            (identity.get("office_review_presentation") or {}).get(
                "quality_profile"
            )
            or profile
        )
        if not isinstance(declared_profile, dict):
            issues.append("run identity quality profile is not an object")
            declared_profile = profile
        else:
            for key, expected in profile.items():
                if key == "exposure":
                    continue
                if declared_profile.get(key) != expected:
                    issues.append(
                        f"run identity quality profile {key} does not match frozen profile"
                    )
            try:
                declared_exposure = float(declared_profile["exposure"])
                declared_film_iso = float(declared_profile["renderer_film_iso"])
            except (KeyError, TypeError, ValueError):
                issues.append("run identity fixed-exposure evidence is missing")
            else:
                expected_film_iso = review_film_iso(
                    declared_exposure,
                    float(declared_profile["renderer_base_film_iso"]),
                )
                if abs(declared_film_iso - expected_film_iso) > 1.0e-4:
                    issues.append("run identity fixed film ISO does not match exposure EV")
        expected_run_id = str(identity.get("config_sha256", ""))
        expected_side_focal = (
            ((identity.get("office_review_presentation") or {}).get("side_camera_config") or {}).get(
                "focal_length_mm"
            )
        )
        expected_side_model = (
            (identity.get("office_review_presentation") or {}).get("side_view_model")
        )
        expected_first_model = (
            (identity.get("office_review_presentation") or {}).get("first_view_model")
        )
        expected_first_config = (
            (identity.get("office_review_presentation") or {}).get("first_view") or {}
        )
        if not expected_run_id:
            issues.append("run_identity.json has no config_sha256")
        if identity.get("acceptance_config_sha256") != sha256_file(acceptance_config_path):
            issues.append("run identity acceptance_config_sha256 does not match acceptance config")
        if not isinstance(acceptance, dict) or not acceptance:
            issues.append("acceptance config is empty")
        if not effective_input:
            issues.append("effective input is empty")

        trace = _read_jsonl_strict(camera_trace_path)
        checks["trace_row_count"] = len(trace)
        if len(trace) != decoded["first"]:
            issues.append(f"trace rows {len(trace)} != video frames {decoded['first']}")
        if requested_duration_seconds > 0.0:
            required_frame_count = int(
                math.ceil(requested_duration_seconds * probes["first"]["fps"] - 1.0e-9)
            )
            checks["requested_duration"] = {
                "seconds": requested_duration_seconds,
                "minimum_frame_count": required_frame_count,
            }
            if decoded["first"] < required_frame_count:
                issues.append(
                    f"first video has {decoded['first']} frames, below the {required_frame_count} "
                    f"frames required for {requested_duration_seconds:g} requested seconds"
                )
        previous_step: Optional[int] = None
        previous_time: Optional[float] = None
        previous_pose: Dict[str, Tuple[List[float], List[float]]] = {}
        configured_side: Optional[float] = None
        for index, row in enumerate(trace):
            if row.get("schema_version") != 4 or row.get("frame_index") != index:
                issues.append(f"trace row {index} schema/frame index is invalid")
                continue
            step = row.get("step")
            sim_time = row.get("sim_time_seconds")
            if not isinstance(step, int) or (previous_step is not None and step <= previous_step):
                issues.append(f"trace row {index} physics step is not strictly increasing")
            if not isinstance(sim_time, (int, float)) or not math.isfinite(float(sim_time)) or (previous_time is not None and float(sim_time) <= previous_time):
                issues.append(f"trace row {index} simulator time is not finite and strictly increasing")
            root_pos = _finite_vector(row.get("root_pos_w"), 3)
            root_quat = _finite_vector(row.get("root_quat_w"), 4)
            if row.get("run_identity") != expected_run_id:
                issues.append(f"trace row {index} run identity does not match run_identity.json")
            if root_pos is None or root_quat is None:
                issues.append(f"trace row {index} root state is invalid")
            elif row.get("state_snapshot_identity") != state_snapshot_identity(step, float(sim_time), root_pos, root_quat):
                issues.append(f"trace row {index} state snapshot identity mismatch")
            capture_settings = row.get("capture_settings") or {}
            for key, expected in declared_profile.items():
                if capture_settings.get(key) != expected:
                    issues.append(f"trace row {index} capture setting {key} mismatch")
                    break
            if capture_settings.get("fps") != probes["first"]["fps"]:
                issues.append(f"trace row {index} capture fps mismatch")
            if expected_side_focal is not None:
                try:
                    first_focal = float((row.get("first_view") or {})["focal_length_mm"])
                    side_focal = float((row.get("side_follow") or {})["focal_length_mm"])
                    overview_focal = float((row.get("overview") or {})["focal_length_mm"])
                except (KeyError, TypeError, ValueError):
                    issues.append(f"trace row {index} focal-length evidence is missing")
                else:
                    if not all(math.isfinite(value) and value > 0.0 for value in (first_focal, side_focal, overview_focal)):
                        issues.append(f"trace row {index} focal-length evidence is invalid")
                    elif (
                        expected_first_config.get("focal_length_mm") is not None
                        and abs(
                            first_focal
                            - float(expected_first_config["focal_length_mm"])
                        )
                        > 1e-2
                    ):
                        issues.append(f"trace row {index} first-view focal length does not match run identity")
                    elif abs(side_focal - float(expected_side_focal)) > 1e-2:
                        issues.append(f"trace row {index} side focal length does not match run identity")
                    elif side_focal >= first_focal or side_focal > overview_focal:
                        issues.append(f"trace row {index} side lens is not wider than the other review views")
            if expected_first_model is not None:
                first_trace = row.get("first_view") or {}
                if first_trace.get("camera_model") != expected_first_model:
                    issues.append(f"trace row {index} first-view camera model does not match run identity")
                if first_trace.get("fallback_reason") not in (
                    None,
                    "content_gate_high_chase",
                ):
                    issues.append(f"trace row {index} first-view fallback reason is invalid")
                try:
                    aperture = float(first_trace["horizontal_aperture_mm"])
                    horizontal_fov = float(first_trace["horizontal_fov_degrees"])
                except (KeyError, TypeError, ValueError):
                    issues.append(f"trace row {index} first-view lens evidence is missing")
                else:
                    if (
                        not math.isfinite(aperture)
                        or aperture <= 0.0
                        or not math.isfinite(horizontal_fov)
                        or not 1.0 < horizontal_fov < 179.0
                    ):
                        issues.append(f"trace row {index} first-view lens evidence is invalid")
            if expected_side_model is not None:
                side_trace = row.get("side_follow") or {}
                if side_trace.get("camera_model") != expected_side_model:
                    issues.append(f"trace row {index} side camera model does not match run identity")
                cutaway = side_trace.get("render_cutaway") or {}
                if (
                    cutaway.get("scope") != "all_review_camera_views_render_only"
                    or not isinstance(cutaway.get("prim_count"), int)
                    or int(cutaway.get("prim_count", 0)) <= 0
                    or len(str(cutaway.get("prim_paths_sha256", ""))) != 64
                    or cutaway.get("restore_before_next_view_and_physics_step") is not True
                    or cutaway.get("navigation_sensor_and_planner_inputs_unchanged") is not True
                ):
                    issues.append(f"trace row {index} side cutaway audit is missing or invalid")
                for view_name in ("first_view", "overview"):
                    if (row.get(view_name) or {}).get("render_cutaway") != cutaway:
                        issues.append(
                            f"trace row {index} {view_name} does not use the same render cutaway"
                        )

            view_poses: Dict[str, Tuple[List[float], List[float]]] = {}
            for view_name in ("first_view", "side_follow", "overview"):
                view = row.get(view_name) or {}
                eye = _finite_vector(view.get("eye") or view.get("realized_eye"), 3)
                target = _finite_vector(view.get("target") or view.get("realized_target"), 3)
                if eye is None or target is None:
                    issues.append(f"trace row {index} {view_name} pose is invalid")
                else:
                    view_poses[view_name] = (eye, target)
            if root_pos is not None and len(view_poses) == 3:
                first_eye = view_poses["first_view"][0]
                side_eye = view_poses["side_follow"][0]
                overview_eye = view_poses["overview"][0]
                if _motion_distance(side_eye, root_pos) < 0.5 or _motion_distance(overview_eye, root_pos) < 1.0:
                    issues.append(f"trace row {index} external camera collapsed onto robot")
                if min(_motion_distance(first_eye, side_eye), _motion_distance(first_eye, overview_eye), _motion_distance(side_eye, overview_eye)) < 0.5:
                    issues.append(f"trace row {index} camera poses are not geometrically distinct")

            side_value = (row.get("side_follow") or {}).get("configured_side")
            try:
                side_value = normalize_side(side_value)
            except ValueError:
                issues.append(f"trace row {index} side is invalid")
                side_value = None
            if side_value is not None:
                if configured_side is None:
                    configured_side = side_value
                elif side_value != configured_side:
                    issues.append(f"trace row {index} side flipped")

            for view_name in ("side_follow", "overview"):
                view = row.get(view_name) or {}
                if index > 0 and view_name in view_poses and view_name in previous_pose:
                    numeric_fields = ("dt", "smoothing_rate", "max_eye_speed_mps", "max_target_speed_mps",
                                      "eye_displacement_m", "target_displacement_m",
                                      "max_allowed_eye_displacement_m", "max_allowed_target_displacement_m")
                    values: Dict[str, float] = {}
                    for field in numeric_fields:
                        try:
                            values[field] = float(view[field])
                        except (KeyError, TypeError, ValueError):
                            values[field] = float("nan")
                    if any(not math.isfinite(value) for value in values.values()) or any(values[field] <= 0.0 for field in ("dt", "smoothing_rate", "max_eye_speed_mps", "max_target_speed_mps")):
                        issues.append(f"trace row {index} {view_name} timing or motion limits are invalid")
                    else:
                        eye_disp = _motion_distance(previous_pose[view_name][0], view_poses[view_name][0])
                        target_disp = _motion_distance(previous_pose[view_name][1], view_poses[view_name][1])
                        expected_eye_max = values["max_eye_speed_mps"] * values["dt"]
                        expected_target_max = values["max_target_speed_mps"] * values["dt"]
                        if abs(values["eye_displacement_m"] - eye_disp) > 1e-3 or abs(values["target_displacement_m"] - target_disp) > 1e-3:
                            issues.append(f"trace row {index} {view_name} recorded displacement mismatch")
                        if abs(values["max_allowed_eye_displacement_m"] - expected_eye_max) > 1e-6 or abs(values["max_allowed_target_displacement_m"] - expected_target_max) > 1e-6:
                            issues.append(f"trace row {index} {view_name} recorded motion bound mismatch")
                        if eye_disp > expected_eye_max + 1e-3 or target_disp > expected_target_max + 1e-3:
                            issues.append(f"trace row {index} {view_name} exceeded motion bound")
            previous_pose = view_poses
            previous_step = step if isinstance(step, int) else previous_step
            previous_time = float(sim_time) if isinstance(sim_time, (int, float)) and math.isfinite(float(sim_time)) else previous_time

        if requested_duration_seconds > 0.0:
            frame_period_seconds = 1.0 / probes["first"]["fps"]
            minimum_last_sim_time = requested_duration_seconds - frame_period_seconds - 1.0e-6
            checks["requested_duration"]["minimum_last_sim_time_seconds"] = minimum_last_sim_time
            checks["requested_duration"]["actual_last_sim_time_seconds"] = previous_time
            if previous_time is None or previous_time < minimum_last_sim_time:
                issues.append(
                    f"camera trace ends at {previous_time}, before the requested "
                    f"{requested_duration_seconds:g} simulator seconds"
                )

        events = _read_jsonl_strict(ros_events_path)
        metrics = _read_jsonl_strict(metrics_path)
        plans = associate_bspline_sim_times(events)
        plan_points = [point for plan in plans for point in plan["sampled_points"]]
        root_points = [row.get("root_pos_w") for row in metrics]
        occupancy_points = [point for event in events if event.get("kind") == "occupancy_inflate" for point in (event.get("points_xyz") or [])]
        series = {"plan": plan_points, "root": root_points, "occupancy": occupancy_points}
        for name, points in series.items():
            if not points or any(_finite_vector(point, 3) is None for point in points):
                issues.append(f"{name} XYZ provenance is empty or non-finite")
        if plan_points and root_points and occupancy_points:
            for name, points in (("plan", plan_points), ("root", root_points)):
                z_values = [float(point[2]) for point in points]
                if max(z_values) - min(z_values) < 1e-4:
                    issues.append(f"{name} XYZ provenance has zero Z variation")
        trajectory_ids = [int(plan["trajectory_id"]) for plan in plans]
        if not trajectory_ids:
            issues.append("no valid SCAN trajectory ID")

        audit = json.loads(material_audit_path.read_text(encoding="utf-8"))
        pre_inventory = audit.get("pre_inventory") or {}
        post_inventory = audit.get("post_inventory") or {}
        robot_root = str(audit.get("robot_root_path", ""))
        if not robot_root or not str(audit.get("robot_asset_sha256", "")) or not audit.get("referenced_mesh_sha256"):
            issues.append("material audit robot asset identity is incomplete")
        if pre_inventory.get("query_phase") != "before_binding" or post_inventory.get("query_phase") != "after_binding":
            issues.append("material audit does not contain separate before/after queries")
        if any(pre_inventory.get(key) in (None, [], {}) or post_inventory.get(key) in (None, [], {}) for key in _PHYSICAL_INVENTORY_KEYS):
            issues.append("material audit contains an empty physical or sensor inventory")
        elif _physical_inventory_projection(pre_inventory) != _physical_inventory_projection(post_inventory):
            issues.append("material audit physical or sensor inventory changed")
        affected = audit.get("affected_prims") or []
        if not affected or int(audit.get("total_affected_prims", 0)) != len(affected):
            issues.append("material audit affected prim inventory is invalid")
        for prim in affected:
            path = str(prim.get("prim_path", ""))
            if not robot_root or not path.startswith(robot_root + "/"):
                issues.append(f"material prim is outside robot root: {path}")
            if float(prim.get("opacity", float("nan"))) != 1.0 or float(prim.get("emission", float("nan"))) != 0.0:
                issues.append(f"material prim is translucent or emissive: {path}")
            material_path = str(prim.get("material_path", ""))
            if (post_inventory.get("material_bindings") or {}).get(path) != material_path or (pre_inventory.get("material_bindings") or {}).get(path) == material_path:
                issues.append(f"material binding change is not measured for {path}")

        metadata = json.loads(dashboard_metadata_path.read_text(encoding="utf-8"))
        expected_hashes = {
            "first_video": hashes["first"], "side_video": hashes["side"],
            "overview_video": hashes["overview"], "camera_trace": sha256_file(camera_trace_path),
            "material_audit": sha256_file(material_audit_path), "ros_events": sha256_file(ros_events_path),
            "metrics": sha256_file(metrics_path), "run_identity": sha256_file(run_identity_path),
            "effective_input": sha256_file(effective_input_path), "acceptance_config": sha256_file(acceptance_config_path),
        }
        if metadata.get("input_sha256") != expected_hashes:
            issues.append("dashboard metadata input hashes do not exactly match mandatory inputs")
        if metadata.get("output_sha256") != hashes["dashboard"]:
            issues.append("dashboard metadata output hash mismatch")
        if metadata.get("resolution") != [DASHBOARD_WIDTH, DASHBOARD_HEIGHT] or metadata.get("frame_count") != decoded["dashboard"]:
            issues.append("dashboard metadata resolution or frame count mismatch")
        if (
            metadata.get("r_frame_rate") != probes["dashboard"]["r_frame_rate"]
            or metadata.get("quality_profile") != declared_profile
        ):
            issues.append("dashboard metadata quality profile or rational rate mismatch")
        if metadata.get("trajectory_ids") != trajectory_ids or int(metadata.get("plan_sample_count", 0)) != len(plan_points) or int(metadata.get("root_sample_count", 0)) != len(root_points) or int(metadata.get("occupancy_raw_count", 0)) != len(occupancy_points):
            issues.append("dashboard metadata provenance counts or trajectory IDs mismatch")
    except BaseException as exc:  # malformed evidence must become a structured failure
        issues.append(f"validation exception: {type(exc).__name__}: {exc}")
    return {"passed": not issues, "issues": issues, "checks": checks}


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Office review presentation renderer and validator.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Render
    render_parser = subparsers.add_parser("render", help="Render 3-camera 3D review dashboard.")
    render_parser.add_argument("--first-video", type=Path, required=True)
    render_parser.add_argument("--side-video", type=Path, required=True)
    render_parser.add_argument("--overview-video", type=Path, required=True)
    render_parser.add_argument("--camera-trace", type=Path, required=True)
    render_parser.add_argument("--material-audit", type=Path, required=True)
    render_parser.add_argument("--ros-events", type=Path, required=True)
    render_parser.add_argument("--metrics", type=Path, required=True)
    render_parser.add_argument("--run-identity", type=Path, required=True)
    render_parser.add_argument("--effective-input", type=Path, required=True)
    render_parser.add_argument("--acceptance-config", type=Path, required=True)
    render_parser.add_argument("--output-video", type=Path, required=True)
    render_parser.add_argument("--output-metadata", type=Path, required=True)

    # Validate
    val_parser = subparsers.add_parser("validate", help="Validate review presentation artifacts.")
    val_parser.add_argument("--first-video", type=Path, required=True)
    val_parser.add_argument("--side-video", type=Path, required=True)
    val_parser.add_argument("--overview-video", type=Path, required=True)
    val_parser.add_argument("--camera-trace", type=Path, required=True)
    val_parser.add_argument("--material-audit", type=Path, required=True)
    val_parser.add_argument("--dashboard-video", type=Path, required=True)
    val_parser.add_argument("--dashboard-metadata", type=Path, required=True)
    val_parser.add_argument("--ros-events", type=Path, required=True)
    val_parser.add_argument("--metrics", type=Path, required=True)
    val_parser.add_argument("--run-identity", type=Path, required=True)
    val_parser.add_argument("--effective-input", type=Path, required=True)
    val_parser.add_argument("--acceptance-config", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "render":
        render_office_review_dashboard(
            first_video_path=args.first_video,
            side_video_path=args.side_video,
            overview_video_path=args.overview_video,
            camera_trace_path=args.camera_trace,
            material_audit_path=args.material_audit,
            ros_events_path=args.ros_events,
            metrics_path=args.metrics,
            run_identity_path=args.run_identity,
            effective_input_path=args.effective_input,
            acceptance_config_path=args.acceptance_config,
            output_dashboard_video_path=args.output_video,
            output_dashboard_metadata_path=args.output_metadata,
        )
        print(f"Dashboard successfully rendered to {args.output_video}")
        return 0

    elif args.command == "validate":
        report = validate_office_review_presentation(
            first_video_path=args.first_video,
            side_video_path=args.side_video,
            overview_video_path=args.overview_video,
            camera_trace_path=args.camera_trace,
            material_audit_path=args.material_audit,
            dashboard_video_path=args.dashboard_video,
            dashboard_metadata_path=args.dashboard_metadata,
            ros_events_path=args.ros_events,
            metrics_path=args.metrics,
            run_identity_path=args.run_identity,
            effective_input_path=args.effective_input,
            acceptance_config_path=args.acceptance_config,
        )
        print(json.dumps(report, indent=2))
        return 0 if report["passed"] else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

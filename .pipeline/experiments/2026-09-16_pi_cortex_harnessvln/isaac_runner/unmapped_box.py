#!/usr/bin/env python3
"""CPU geometry for one unmapped cuboid in the Building LiDAR cloud.

Pure Python; no Isaac, Torch or ROS import. `materialize_runner_patch.py`
inserts the text between the two body markers verbatim into the patched runner.

Ports the surveyed fallback AABB pad (0.01 m) and Isaac Lab sibling-prim extra
target. Pose is PRD D3: 0.4 x 0.4 x 0.8 m, 2.5 m along start yaw, centre z =
ground z + 0.4 m. Robot overlap uses the 09-14 URDF torso plus 0.25 m.

Task: .trellis/tasks/09-20-isaac-lidar-unmapped-box-hits
"""

from __future__ import annotations

# >>> unmapped_box runner body begin
import math

UNMAPPED_BOX_MODES = ("off", "spawn", "lidar")
UNMAPPED_BOX_PRIM = "/World/unmapped_box"
UNMAPPED_BOX_SIZE_XYZ_M = (0.4, 0.4, 0.8)
UNMAPPED_BOX_OFFSET_M = 2.5
UNMAPPED_BOX_HALF_HEIGHT_M = 0.4
UNMAPPED_BOX_AABB_PAD_M = 0.01
# Pinned Lite3 URDF torso extents (09-14 survey) plus 0.25 m conservative pad.
ROBOT_TORSO_MIN_XYZ_M = (-0.269, -0.109, -0.10)
ROBOT_TORSO_MAX_XYZ_M = (0.279, 0.109, 0.10)
ROBOT_AABB_EXPAND_M = 0.25


class UnmappedBoxError(ValueError):
    """Invalid mode or a spawn that intersects the robot AABB."""


def box_pose_from_stand(start_ground_xyz_m, start_tangent_yaw, offset_m=UNMAPPED_BOX_OFFSET_M):
    """World cuboid pose from the frozen stand start and D3 offset."""
    start = tuple(float(value) for value in start_ground_xyz_m)
    yaw = float(start_tangent_yaw)
    offset = float(offset_m)
    if len(start) != 3 or not all(math.isfinite(value) for value in start + (yaw, offset)):
        raise UnmappedBoxError("stand start pose is not three finite metres plus a finite yaw")
    center = (
        start[0] + offset * math.cos(yaw),
        start[1] + offset * math.sin(yaw),
        start[2] + UNMAPPED_BOX_HALF_HEIGHT_M,
    )
    return {
        "prim": UNMAPPED_BOX_PRIM,
        "center_xyz_m": center,
        "size_xyz_m": UNMAPPED_BOX_SIZE_XYZ_M,
        "offset_m": offset,
        "start_ground_xyz_m": start,
        "start_tangent_yaw": yaw,
    }


def expanded_aabb(center_xyz_m, size_xyz_m, pad_m=UNMAPPED_BOX_AABB_PAD_M):
    """Axis-aligned box with the fallback 0.01 m pad on every side."""
    center = tuple(float(value) for value in center_xyz_m)
    size = tuple(float(value) for value in size_xyz_m)
    pad = float(pad_m)
    if len(center) != 3 or len(size) != 3 or any(value <= 0.0 for value in size) or pad < 0.0:
        raise UnmappedBoxError("AABB centre, size and pad must be finite with positive size")
    if not all(math.isfinite(value) for value in center + size + (pad,)):
        raise UnmappedBoxError("AABB centre, size and pad must be finite")
    half = (size[0] / 2.0, size[1] / 2.0, size[2] / 2.0)
    return {
        "min_xyz_m": (center[0] - half[0] - pad, center[1] - half[1] - pad, center[2] - half[2] - pad),
        "max_xyz_m": (center[0] + half[0] + pad, center[1] + half[1] + pad, center[2] + half[2] + pad),
        "pad_m": pad,
    }


def point_in_aabb(point_xyz_m, aabb_min_xyz_m, aabb_max_xyz_m):
    point = tuple(float(value) for value in point_xyz_m)
    lo = tuple(float(value) for value in aabb_min_xyz_m)
    hi = tuple(float(value) for value in aabb_max_xyz_m)
    return all(lo[i] <= point[i] <= hi[i] for i in range(3))


def aabbs_intersect(first, second):
    for axis in range(3):
        if first["max_xyz_m"][axis] < second["min_xyz_m"][axis]:
            return False
        if second["max_xyz_m"][axis] < first["min_xyz_m"][axis]:
            return False
    return True


def robot_aabb_world(start_ground_xyz_m, start_tangent_yaw, body_height_m,
                     expand_m=ROBOT_AABB_EXPAND_M):
    """World AABB of the URDF torso expanded by 0.25 m at the spawn pose."""
    start = tuple(float(value) for value in start_ground_xyz_m)
    yaw = float(start_tangent_yaw)
    height = float(body_height_m)
    expand = float(expand_m)
    origin = (start[0], start[1], start[2] + height)
    mins = [ROBOT_TORSO_MIN_XYZ_M[i] - expand for i in range(3)]
    maxs = [ROBOT_TORSO_MAX_XYZ_M[i] + expand for i in range(3)]
    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)
    xs = []
    ys = []
    zs = []
    for x in (mins[0], maxs[0]):
        for y in (mins[1], maxs[1]):
            for z in (mins[2], maxs[2]):
                xs.append(origin[0] + cos_yaw * x - sin_yaw * y)
                ys.append(origin[1] + sin_yaw * x + cos_yaw * y)
                zs.append(origin[2] + z)
    return {"min_xyz_m": (min(xs), min(ys), min(zs)), "max_xyz_m": (max(xs), max(ys), max(zs))}


def require_no_robot_overlap(box_aabb, robot_aabb):
    if aabbs_intersect(box_aabb, robot_aabb):
        raise UnmappedBoxError("unmapped box AABB intersects the robot AABB at spawn")


def rotate_vector_wxyz(quaternion_wxyz, vector_xyz):
    w, x, y, z = [float(value) for value in quaternion_wxyz]
    vx, vy, vz = [float(value) for value in vector_xyz]
    ux = 2.0 * (y * vz - z * vy)
    uy = 2.0 * (z * vx - x * vz)
    uz = 2.0 * (x * vy - y * vx)
    return (
        vx + w * ux + (y * uz - z * uy),
        vy + w * uy + (z * ux - x * uz),
        vz + w * uz + (x * uy - y * ux),
    )


def sensor_points_to_world(points_sensor_frame, sensor_position, sensor_quaternion_wxyz):
    """Rotate sensor-frame xyz by wxyz, then add sensor_position."""
    origin = tuple(float(value) for value in sensor_position)
    world = []
    for point in points_sensor_frame:
        rotated = rotate_vector_wxyz(sensor_quaternion_wxyz, point)
        world.append((rotated[0] + origin[0], rotated[1] + origin[1], rotated[2] + origin[2]))
    return world


def aabb_hit_count(world_points, aabb):
    lo = aabb["min_xyz_m"]
    hi = aabb["max_xyz_m"]
    return sum(1 for point in world_points if point_in_aabb(point, lo, hi))


def lidar_mesh_prim_paths(base_paths, mode):
    """Append the sibling prim string only in lidar mode. Never wrap RaycastTargetCfg."""
    if mode not in UNMAPPED_BOX_MODES:
        raise UnmappedBoxError("unsupported --unmapped-box value: %r" % (mode,))
    paths = list(base_paths)
    if mode == "lidar":
        paths.append(UNMAPPED_BOX_PRIM)
    return paths


def unmapped_box_identity(mode, start_ground_xyz_m, start_tangent_yaw, body_height_m,
                          offset_m=UNMAPPED_BOX_OFFSET_M):
    if mode not in UNMAPPED_BOX_MODES:
        raise UnmappedBoxError("unsupported --unmapped-box value: %r" % (mode,))
    pose = box_pose_from_stand(start_ground_xyz_m, start_tangent_yaw, offset_m=offset_m)
    box_aabb = expanded_aabb(pose["center_xyz_m"], pose["size_xyz_m"])
    robot_aabb = robot_aabb_world(start_ground_xyz_m, start_tangent_yaw, body_height_m)
    intersects = aabbs_intersect(box_aabb, robot_aabb)
    return {
        "schema_version": 1,
        "mode": mode,
        "prim": UNMAPPED_BOX_PRIM,
        "center_xyz_m": list(pose["center_xyz_m"]),
        "size_xyz_m": list(UNMAPPED_BOX_SIZE_XYZ_M),
        "aabb_pad_m": UNMAPPED_BOX_AABB_PAD_M,
        "offset_m": float(offset_m),
        "spawn": mode in ("spawn", "lidar"),
        "lidar_target": mode == "lidar",
        "robot_overlap": {
            "intersects": intersects,
            "robot_aabb": {
                "min_xyz_m": list(robot_aabb["min_xyz_m"]),
                "max_xyz_m": list(robot_aabb["max_xyz_m"]),
            },
            "box_aabb": {
                "min_xyz_m": list(box_aabb["min_xyz_m"]),
                "max_xyz_m": list(box_aabb["max_xyz_m"]),
            },
        },
    }
# <<< unmapped_box runner body end

"""Isaac-independent helpers for the Lite3 physical simulation adapter."""

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class QualificationSegment:
    name: str
    duration_seconds: float
    command: Tuple[float, float, float]
    connected: bool = True

    def __post_init__(self) -> None:
        if not self.name or not math.isfinite(self.duration_seconds):
            raise ValueError("qualification segment needs a name and finite duration")
        if self.duration_seconds <= 0.0 or len(self.command) != 3:
            raise ValueError("qualification segment duration and command are invalid")
        if not all(math.isfinite(float(value)) for value in self.command):
            raise ValueError("qualification command must be finite")
        if not self.connected and any(float(value) != 0.0 for value in self.command):
            raise ValueError("a disconnected segment must declare a zero command")


DEFAULT_QUALIFICATION_SCHEDULE = (
    QualificationSegment("settle_zero", 1.0, (0.0, 0.0, 0.0)),
    QualificationSegment("forward", 2.0, (0.30, 0.0, 0.0)),
    QualificationSegment("lateral", 2.0, (0.0, 0.18, 0.0)),
    QualificationSegment("yaw", 2.0, (0.0, 0.0, 0.40)),
    QualificationSegment("stop_zero", 1.0, (0.0, 0.0, 0.0)),
    QualificationSegment("watchdog_disconnect", 0.75, (0.0, 0.0, 0.0), False),
)


@dataclass(frozen=True)
class DynamicObstacleSpec:
    """Frozen straight-line wait/cross/hold/cross/park moving-body trajectory."""

    name: str
    start_xy: Tuple[float, float]
    end_xy: Tuple[float, float]
    wait_seconds: float
    speed_mps: float
    radius_m: float
    height_m: float
    terrain_clearance_m: float
    hold_fraction: float = 0.5
    hold_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("dynamic obstacle needs a name")
        if len(self.start_xy) != 2 or len(self.end_xy) != 2:
            raise ValueError("dynamic obstacle endpoints must be two-dimensional")
        values = tuple(float(value) for value in self.start_xy + self.end_xy) + (
            float(self.wait_seconds),
            float(self.speed_mps),
            float(self.radius_m),
            float(self.height_m),
            float(self.terrain_clearance_m),
            float(self.hold_fraction),
            float(self.hold_seconds),
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("dynamic obstacle values must be finite")
        if math.dist(self.start_xy, self.end_xy) <= 1.0e-9:
            raise ValueError("dynamic obstacle endpoints must be distinct")
        if (
            self.wait_seconds < 0.0
            or self.hold_seconds < 0.0
            or self.terrain_clearance_m < 0.0
        ):
            raise ValueError(
                "dynamic obstacle wait, hold, and clearance must be non-negative"
            )
        if not 0.0 < self.hold_fraction < 1.0:
            raise ValueError("dynamic obstacle hold fraction must be inside (0, 1)")
        if self.speed_mps <= 0.0 or self.radius_m <= 0.0 or self.height_m <= 0.0:
            raise ValueError("dynamic obstacle speed and dimensions must be positive")

    @property
    def crossing_duration_seconds(self) -> float:
        return math.dist(self.start_xy, self.end_xy) / self.speed_mps


def dynamic_obstacle_state(
    elapsed_seconds: float,
    spec: DynamicObstacleSpec,
    terrain_height: Callable[[float, float], float],
) -> Mapping[str, object]:
    """Evaluate a terrain-seated obstacle pose without simulator dependencies."""

    if not math.isfinite(elapsed_seconds) or elapsed_seconds < 0.0:
        raise ValueError("dynamic obstacle elapsed time must be finite and non-negative")
    crossing_elapsed = elapsed_seconds - spec.wait_seconds
    if crossing_elapsed <= 0.0:
        phase = "waiting"
        fraction = 0.0
    elif crossing_elapsed < spec.crossing_duration_seconds * spec.hold_fraction:
        phase = "crossing"
        fraction = crossing_elapsed / spec.crossing_duration_seconds
    elif crossing_elapsed < (
        spec.crossing_duration_seconds * spec.hold_fraction + spec.hold_seconds
    ):
        phase = "holding"
        fraction = spec.hold_fraction
    elif crossing_elapsed < spec.crossing_duration_seconds + spec.hold_seconds:
        phase = "crossing"
        fraction = (
            crossing_elapsed - spec.hold_seconds
        ) / spec.crossing_duration_seconds
    else:
        phase = "parked"
        fraction = 1.0
    dx = float(spec.end_xy[0]) - float(spec.start_xy[0])
    dy = float(spec.end_xy[1]) - float(spec.start_xy[1])
    x = float(spec.start_xy[0]) + fraction * dx
    y = float(spec.start_xy[1]) + fraction * dy
    segment_length = math.hypot(dx, dy)
    heading_yaw_radians = math.atan2(dy, dx)
    velocity_xy = (
        (spec.speed_mps * dx / segment_length, spec.speed_mps * dy / segment_length)
        if phase == "crossing"
        else (0.0, 0.0)
    )
    ground_z = float(terrain_height(x, y))
    if not math.isfinite(ground_z):
        raise ValueError("dynamic obstacle terrain height must be finite")
    center_z = ground_z + 0.5 * spec.height_m + spec.terrain_clearance_m
    return {
        "phase": phase,
        "elapsed_seconds": float(elapsed_seconds),
        "crossing_fraction": fraction,
        "center_xy_m": (x, y),
        "center_xyz_m": (x, y, center_z),
        "velocity_xy_mps": velocity_xy,
        "heading_yaw_radians": heading_yaw_radians,
        "terrain_height_m": ground_z,
        "bottom_terrain_clearance_m": center_z - 0.5 * spec.height_m - ground_z,
    }


def official_human_registered_state(
    dynamic_state: Mapping[str, object],
    spec: DynamicObstacleSpec,
    *,
    source_foot_z_m: float,
    source_visible_top_z_m: float,
    source_forward_yaw_radians: float,
) -> Mapping[str, object]:
    """Register an official foot-datum visual to a centre-datum capsule.

    The visual and the physical proxy deliberately keep separate world roots.
    Both are derived from one scheduled state so their time, XY, and heading
    cannot drift while their vertical datums remain physically meaningful.
    """

    scalar_values = (
        float(source_foot_z_m),
        float(source_visible_top_z_m),
        float(source_forward_yaw_radians),
    )
    if not all(math.isfinite(value) for value in scalar_values):
        raise ValueError("official human source geometry must be finite")
    if source_visible_top_z_m <= source_foot_z_m:
        raise ValueError("official human visible top must be above its foot datum")
    center_xyz = tuple(float(value) for value in dynamic_state["center_xyz_m"])
    if len(center_xyz) != 3 or not all(math.isfinite(value) for value in center_xyz):
        raise ValueError("official human scheduled centre must be finite XYZ")
    terrain_height_m = float(dynamic_state["terrain_height_m"])
    heading_yaw_radians = float(dynamic_state["heading_yaw_radians"])
    if not math.isfinite(terrain_height_m) or not math.isfinite(heading_yaw_radians):
        raise ValueError("official human terrain and heading must be finite")

    visual_foot_world_z_m = terrain_height_m + float(spec.terrain_clearance_m)
    visual_root_z_m = visual_foot_world_z_m - float(source_foot_z_m)
    visual_yaw_radians = heading_yaw_radians - float(source_forward_yaw_radians)
    half_yaw = 0.5 * visual_yaw_radians
    capsule_bottom_world_z_m = center_xyz[2] - 0.5 * float(spec.height_m)
    return {
        "visual_root_xyz_m": (center_xyz[0], center_xyz[1], visual_root_z_m),
        "visual_quaternion_wxyz": (
            math.cos(half_yaw),
            0.0,
            0.0,
            math.sin(half_yaw),
        ),
        "visual_yaw_radians": visual_yaw_radians,
        "visual_foot_world_z_m": visual_foot_world_z_m,
        "visual_top_world_z_m": (
            visual_root_z_m + float(source_visible_top_z_m)
        ),
        "capsule_center_xyz_m": center_xyz,
        "capsule_bottom_world_z_m": capsule_bottom_world_z_m,
        "foot_to_capsule_bottom_error_m": (
            visual_foot_world_z_m - capsule_bottom_world_z_m
        ),
    }


def retarget_joint_indices(
    skeleton_joints: Sequence[str], animation_joints: Sequence[str]
) -> Tuple[Optional[int], ...]:
    """Map an official animation joint table onto a character skeleton by name."""

    skeleton_names = tuple(str(value) for value in skeleton_joints)
    animation_names = tuple(str(value) for value in animation_joints)
    if not skeleton_names or not animation_names:
        raise ValueError("skeleton and animation joint tables must be non-empty")
    if len(set(skeleton_names)) != len(skeleton_names):
        raise ValueError("skeleton joint table contains duplicate names")
    if len(set(animation_names)) != len(animation_names):
        raise ValueError("animation joint table contains duplicate names")
    animation_index = {name: index for index, name in enumerate(animation_names)}
    absent = sorted(set(animation_names) - set(skeleton_names))
    if absent:
        raise ValueError(f"animation joints are absent from the skeleton: {absent}")
    return tuple(animation_index.get(name) for name in skeleton_names)


def procedural_human_gait_angles(
    elapsed_seconds: float,
    phase: str,
    cadence_hz: float = 1.6,
    maximum_swing_radians: float = math.radians(25.0),
) -> Mapping[str, float]:
    """Return deterministic opposing limb angles for a rigid-root human visual."""

    values = (
        float(elapsed_seconds),
        float(cadence_hz),
        float(maximum_swing_radians),
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("human gait inputs must be finite")
    if elapsed_seconds < 0.0 or cadence_hz <= 0.0:
        raise ValueError("human gait time and cadence are invalid")
    if not 0.0 < maximum_swing_radians <= math.pi / 2.0:
        raise ValueError("human gait swing must be inside (0, pi/2]")
    if phase not in ("waiting", "crossing", "holding", "parked"):
        raise ValueError(f"unsupported human gait phase: {phase}")

    swing = 0.0
    if phase == "crossing":
        swing = maximum_swing_radians * math.sin(
            2.0 * math.pi * cadence_hz * elapsed_seconds
        )
    return {
        "left_arm_radians": -swing,
        "right_arm_radians": swing,
        "left_leg_radians": swing,
        "right_leg_radians": -swing,
    }


def expand_isaac_env_regex_ns(prim_expr: str) -> str:
    """Expand Isaac Lab's environment namespace token to its runtime regex."""

    if not isinstance(prim_expr, str) or not prim_expr:
        raise ValueError("prim expression must be a non-empty string")
    return prim_expr.replace("{ENV_REGEX_NS}", "/World/envs/env_.*")


def circle_surface_clearance_2d(
    first_xy: Sequence[float],
    second_xy: Sequence[float],
    first_radius_m: float,
    second_radius_m: float,
) -> float:
    """Return signed planar clearance between two synchronized circle bounds."""

    if len(first_xy) != 2 or len(second_xy) != 2:
        raise ValueError("circle centres must be two-dimensional")
    values = tuple(float(value) for value in first_xy) + tuple(
        float(value) for value in second_xy
    ) + (float(first_radius_m), float(second_radius_m))
    if not all(math.isfinite(value) for value in values):
        raise ValueError("circle clearance inputs must be finite")
    if first_radius_m < 0.0 or second_radius_m < 0.0:
        raise ValueError("circle radii must be non-negative")
    return math.dist(first_xy, second_xy) - first_radius_m - second_radius_m


def schedule_state(
    elapsed_seconds: float,
    schedule: Sequence[QualificationSegment] = DEFAULT_QUALIFICATION_SCHEDULE,
) -> Tuple[QualificationSegment, float]:
    """Return the active schedule segment and elapsed time inside it."""

    if not math.isfinite(elapsed_seconds) or elapsed_seconds < 0.0:
        raise ValueError("elapsed_seconds must be finite and non-negative")
    if not schedule:
        raise ValueError("schedule must not be empty")
    cursor = 0.0
    for segment in schedule:
        boundary = cursor + segment.duration_seconds
        if elapsed_seconds < boundary:
            return segment, elapsed_seconds - cursor
        cursor = boundary
    return schedule[-1], schedule[-1].duration_seconds


def schedule_duration(
    schedule: Sequence[QualificationSegment] = DEFAULT_QUALIFICATION_SCHEDULE,
) -> float:
    if not schedule:
        raise ValueError("schedule must not be empty")
    return sum(segment.duration_seconds for segment in schedule)


def canonical_config_sha256(config: Mapping[str, object]) -> bytes:
    """Hash JSON-compatible configuration with deterministic serialization."""

    encoded = json.dumps(
        config, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).digest()


def quaternion_wxyz_to_xyzw(quaternion: Sequence[float]) -> Tuple[float, ...]:
    if len(quaternion) != 4:
        raise ValueError("quaternion must contain four values")
    values = tuple(float(value) for value in quaternion)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("quaternion must be finite")
    norm = math.sqrt(sum(value * value for value in values))
    if norm < 1.0e-12:
        raise ValueError("quaternion norm is zero")
    w, x, y, z = (value / norm for value in values)
    return x, y, z, w


def mounted_sensor_pose(prim_position, prim_quaternion, offset_position, offset_quaternion):
    """Compose RayCaster attachment pose and cfg.offset (base-aligned rays).

    Installed RayCaster stores the attachment pose in data.pos_w/quat_w and
    applies cfg.offset to ray starts/directions separately. World hits must be
    transformed into the mounted sensor frame exactly once at the bridge.
    """
    rotation = rotation_matrix_from_wxyz(prim_quaternion)
    position = tuple(float(prim_position[i]) + sum(rotation[i][j] * offset_position[j]
                                                   for j in range(3)) for i in range(3))
    x, y, z, w = quaternion_wxyz_to_xyzw(prim_quaternion)
    u, v, t, s = quaternion_wxyz_to_xyzw(offset_quaternion)
    quaternion = (w*s - x*u - y*v - z*t, w*u + x*s + y*t - z*v,
                  w*v - x*t + y*s + z*u, w*t + x*v - y*u + z*s)
    return position, quaternion


def rotation_matrix_from_wxyz(quaternion: Sequence[float]) -> Tuple[Tuple[float, ...], ...]:
    """Return the local-to-world rotation for a normalized Isaac quaternion."""

    x, y, z, w = quaternion_wxyz_to_xyzw(quaternion)
    return (
        (1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)),
        (2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)),
        (2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)),
    )


def world_hits_to_sensor_points(
    world_hits: Iterable[Sequence[float]],
    sensor_position_world: Sequence[float],
    sensor_quaternion_wxyz: Sequence[float],
    minimum_range: float,
    maximum_range: float,
    minimum_world_z: Optional[float] = None,
) -> Tuple[Tuple[float, float, float], ...]:
    """Transform finite, height- and range-gated world hits into the sensor frame."""

    if len(sensor_position_world) != 3:
        raise ValueError("sensor position must contain three values")
    origin = tuple(float(value) for value in sensor_position_world)
    if not all(math.isfinite(value) for value in origin):
        raise ValueError("sensor position must be finite")
    if (
        not math.isfinite(minimum_range)
        or not math.isfinite(maximum_range)
        or minimum_range < 0.0
        or maximum_range <= minimum_range
    ):
        raise ValueError("range limits are invalid")
    if minimum_world_z is not None and not math.isfinite(minimum_world_z):
        raise ValueError("minimum world z must be finite when provided")
    rotation = rotation_matrix_from_wxyz(sensor_quaternion_wxyz)
    result = []
    for hit in world_hits:
        if len(hit) != 3:
            raise ValueError("each world hit must contain three values")
        values = tuple(float(value) for value in hit)
        if not all(math.isfinite(value) for value in values):
            continue
        if minimum_world_z is not None and values[2] <= minimum_world_z:
            continue
        dx, dy, dz = (values[index] - origin[index] for index in range(3))
        # Row-vector delta multiplied by R gives R^T * delta in column form.
        local = (
            dx * rotation[0][0] + dy * rotation[1][0] + dz * rotation[2][0],
            dx * rotation[0][1] + dy * rotation[1][1] + dz * rotation[2][1],
            dx * rotation[0][2] + dy * rotation[1][2] + dz * rotation[2][2],
        )
        distance = math.sqrt(sum(value * value for value in local))
        if minimum_range <= distance <= maximum_range:
            result.append(local)
    return tuple(result)


def local_minimum_obstacle_hits(
    world_hits: Iterable[Sequence[float]],
    sensor_position_world: Sequence[float],
    minimum_range: float,
    maximum_range: float,
    cell_size: float,
    height_threshold: float,
    neighbor_cells: int = 1,
    minimum_neighbor_cells: int = 2,
) -> Tuple[Tuple[Tuple[float, float, float], ...], Mapping[str, int]]:
    """Keep obstacle-like hits above a local terrain envelope.

    The filter deliberately consumes only rendered XYZ geometry and sensor
    position. It has no terrain-height, scene-prim, or obstacle-label input.
    Sparse cells are retained conservatively rather than being called ground.
    """

    if len(sensor_position_world) != 3:
        raise ValueError("sensor position must contain three values")
    origin = tuple(float(value) for value in sensor_position_world)
    if not all(math.isfinite(value) for value in origin):
        raise ValueError("sensor position must be finite")
    if (
        not math.isfinite(minimum_range)
        or not math.isfinite(maximum_range)
        or minimum_range < 0.0
        or maximum_range <= minimum_range
    ):
        raise ValueError("range limits are invalid")
    if not math.isfinite(cell_size) or cell_size <= 0.0:
        raise ValueError("terrain-filter cell size must be positive and finite")
    if not math.isfinite(height_threshold) or height_threshold <= 0.0:
        raise ValueError("terrain-filter height threshold must be positive and finite")
    if neighbor_cells < 0:
        raise ValueError("terrain-filter neighbor cell count must be non-negative")
    if minimum_neighbor_cells <= 0:
        raise ValueError("terrain-filter minimum neighbor cells must be positive")

    candidates = []
    cell_minimum_z: Dict[Tuple[int, int], float] = {}
    input_count = 0
    for hit in world_hits:
        input_count += 1
        if len(hit) != 3:
            raise ValueError("each world hit must contain three values")
        point = tuple(float(value) for value in hit)
        if not all(math.isfinite(value) for value in point):
            continue
        distance = math.dist(point, origin)
        if distance < minimum_range or distance > maximum_range:
            continue
        cell = (
            math.floor(point[0] / cell_size),
            math.floor(point[1] / cell_size),
        )
        candidates.append((point, cell))
        cell_minimum_z[cell] = min(point[2], cell_minimum_z.get(cell, point[2]))

    obstacle_hits = []
    filtered_ground_count = 0
    sparse_retained_count = 0
    for point, cell in candidates:
        local_minima = []
        for dx in range(-neighbor_cells, neighbor_cells + 1):
            for dy in range(-neighbor_cells, neighbor_cells + 1):
                neighbor = (cell[0] + dx, cell[1] + dy)
                if neighbor in cell_minimum_z:
                    local_minima.append(cell_minimum_z[neighbor])
        if len(local_minima) < minimum_neighbor_cells:
            obstacle_hits.append(point)
            sparse_retained_count += 1
            continue
        terrain_envelope_z = min(local_minima)
        if point[2] - terrain_envelope_z > height_threshold:
            obstacle_hits.append(point)
        else:
            filtered_ground_count += 1

    stats = {
        "input_hit_count": input_count,
        "finite_in_range_hit_count": len(candidates),
        "cell_count": len(cell_minimum_z),
        "filtered_ground_hit_count": filtered_ground_count,
        "obstacle_hit_count": len(obstacle_hits),
        "sparse_retained_hit_count": sparse_retained_count,
    }
    return tuple(obstacle_hits), stats


def split_geometry_cloud_points(
    world_hits: Iterable[Sequence[float]],
    sensor_position_world: Sequence[float],
    sensor_quaternion_wxyz: Sequence[float],
    minimum_range: float,
    maximum_range: float,
    cell_size: float,
    height_threshold: float,
    neighbor_cells: int = 1,
    minimum_neighbor_cells: int = 2,
):
    """Create raw and terrain-filtered sensor-frame clouds from one scan."""

    materialized_hits = tuple(world_hits)
    raw_points = world_hits_to_sensor_points(
        materialized_hits,
        sensor_position_world,
        sensor_quaternion_wxyz,
        minimum_range,
        maximum_range,
        minimum_world_z=None,
    )
    planner_world_hits, stats = local_minimum_obstacle_hits(
        materialized_hits,
        sensor_position_world,
        minimum_range,
        maximum_range,
        cell_size,
        height_threshold,
        neighbor_cells,
        minimum_neighbor_cells,
    )
    planner_points = world_hits_to_sensor_points(
        planner_world_hits,
        sensor_position_world,
        sensor_quaternion_wxyz,
        minimum_range,
        maximum_range,
        minimum_world_z=None,
    )
    if len(raw_points) != stats["finite_in_range_hit_count"]:
        raise ValueError("raw cloud count does not match geometry-filter input")
    if len(raw_points) != len(planner_points) + stats["filtered_ground_hit_count"]:
        raise ValueError("raw/planning geometry partition is inconsistent")
    return raw_points, planner_points, stats


def terrain_seating_for_bounds(
    origin_xy: Sequence[float],
    local_bounds_min: Sequence[float],
    local_bounds_max: Sequence[float],
    terrain_height: Callable[[float, float], float],
    samples_per_axis: int = 5,
    clearance_m: float = 0.01,
) -> Mapping[str, object]:
    """Return a conservative AABB z placement for diagnostic use.

    The visual is axis-aligned in the current forest adapter. Sampling the
    complete XY bound avoids the V5 failure mode where a centre-height origin
    placed roughly half of a centre-origin rock below the surrounding terrain.
    It can visibly float an irregular mesh when a high box corner contains no
    source geometry; final source visuals should use real mesh support points.
    """

    if len(origin_xy) != 2 or len(local_bounds_min) != 3 or len(local_bounds_max) != 3:
        raise ValueError("origin and bounds dimensions are invalid")
    origin = tuple(float(value) for value in origin_xy)
    lower = tuple(float(value) for value in local_bounds_min)
    upper = tuple(float(value) for value in local_bounds_max)
    if not all(math.isfinite(value) for value in origin + lower + upper):
        raise ValueError("origin and bounds must be finite")
    if any(left >= right for left, right in zip(lower, upper)):
        raise ValueError("local bounds must have strictly increasing extents")
    if samples_per_axis < 2:
        raise ValueError("terrain seating needs at least two samples per axis")
    if not math.isfinite(clearance_m) or clearance_m < 0.0:
        raise ValueError("terrain seating clearance must be finite and non-negative")

    samples = []
    for x_index in range(samples_per_axis):
        x_fraction = x_index / (samples_per_axis - 1)
        x = origin[0] + lower[0] + (upper[0] - lower[0]) * x_fraction
        for y_index in range(samples_per_axis):
            y_fraction = y_index / (samples_per_axis - 1)
            y = origin[1] + lower[1] + (upper[1] - lower[1]) * y_fraction
            height = float(terrain_height(x, y))
            if not math.isfinite(height):
                raise ValueError("terrain height sample must be finite")
            samples.append((x, y, height))

    maximum_height = max(point[2] for point in samples)
    required_origin_z = maximum_height - lower[2] + clearance_m
    return {
        "sample_count": len(samples),
        "samples_world_xyz_m": tuple(samples),
        "maximum_terrain_height_m": maximum_height,
        "required_origin_z_m": required_origin_z,
        "seated_bounds_min_z_m": required_origin_z + lower[2],
        "clearance_m": clearance_m,
    }


def terrain_seating_for_mesh_support(
    origin_xy: Sequence[float],
    local_support_points: Iterable[Sequence[float]],
    terrain_height: Callable[[float, float], float],
    clearance_m: float = 0.01,
) -> Mapping[str, object]:
    """Seat a static mesh from real low-surface vertices instead of its box.

    A conservative full-AABB terrain sample can place an irregular mesh far
    above a steep surface: the AABB corner that touches the highest terrain may
    contain no geometry.  Each supplied support point is an actual mesh vertex
    from a narrow band above the mesh minimum.  The returned origin keeps every
    selected support point above terrain and makes at least one of them attain
    exactly ``clearance_m``.
    """

    if len(origin_xy) != 2:
        raise ValueError("origin must be two-dimensional")
    origin = tuple(float(value) for value in origin_xy)
    if not all(math.isfinite(value) for value in origin):
        raise ValueError("origin must be finite")
    if not math.isfinite(clearance_m) or clearance_m < 0.0:
        raise ValueError("terrain seating clearance must be finite and non-negative")

    samples = []
    for point in local_support_points:
        if len(point) != 3:
            raise ValueError("each mesh support point must be three-dimensional")
        local = tuple(float(value) for value in point)
        if not all(math.isfinite(value) for value in local):
            raise ValueError("mesh support points must be finite")
        world_x = origin[0] + local[0]
        world_y = origin[1] + local[1]
        height = float(terrain_height(world_x, world_y))
        if not math.isfinite(height):
            raise ValueError("terrain height sample must be finite")
        required_origin_z = height - local[2] + clearance_m
        samples.append(
            {
                "local_point_xyz_m": local,
                "world_xy_m": (world_x, world_y),
                "terrain_height_m": height,
                "required_origin_z_m": required_origin_z,
            }
        )
    if not samples:
        raise ValueError("mesh support points must not be empty")

    contact = max(samples, key=lambda row: float(row["required_origin_z_m"]))
    required_origin_z = float(contact["required_origin_z_m"])
    clearances = tuple(
        required_origin_z
        + float(row["local_point_xyz_m"][2])
        - float(row["terrain_height_m"])
        for row in samples
    )
    contact_local = tuple(float(value) for value in contact["local_point_xyz_m"])
    contact_world = (
        origin[0] + contact_local[0],
        origin[1] + contact_local[1],
        required_origin_z + contact_local[2],
    )
    return {
        "method": "lowest_mesh_vertex_band",
        "sample_count": len(samples),
        "support_samples": tuple(samples),
        "maximum_terrain_height_m": max(
            float(row["terrain_height_m"]) for row in samples
        ),
        "required_origin_z_m": required_origin_z,
        "minimum_support_clearance_m": min(clearances),
        "maximum_support_clearance_m": max(clearances),
        "contact_support_point_local_xyz_m": contact_local,
        "contact_support_point_world_xyz_m": contact_world,
        "contact_terrain_height_m": float(contact["terrain_height_m"]),
        "clearance_m": clearance_m,
    }


def point_to_segment_distance_2d(
    point: Sequence[float], start: Sequence[float], end: Sequence[float]
) -> float:
    """Return Euclidean distance from a 2-D point to a closed segment."""

    if len(point) != 2 or len(start) != 2 or len(end) != 2:
        raise ValueError("point and segment endpoints must be two-dimensional")
    px, py = (float(value) for value in point)
    sx, sy = (float(value) for value in start)
    ex, ey = (float(value) for value in end)
    if not all(math.isfinite(value) for value in (px, py, sx, sy, ex, ey)):
        raise ValueError("point and segment endpoints must be finite")
    dx = ex - sx
    dy = ey - sy
    length_squared = dx * dx + dy * dy
    if length_squared <= 1.0e-18:
        return math.hypot(px - sx, py - sy)
    projection = ((px - sx) * dx + (py - sy) * dy) / length_squared
    projection = max(0.0, min(1.0, projection))
    closest_x = sx + projection * dx
    closest_y = sy + projection * dy
    return math.hypot(px - closest_x, py - closest_y)


def segment_to_aabb_clearance_2d(
    start: Sequence[float],
    end: Sequence[float],
    bounds_min: Sequence[float],
    bounds_max: Sequence[float],
    swept_radius_m: float = 0.0,
) -> float:
    """Return centre-segment clearance from a 2-D AABB minus swept radius."""

    if any(len(value) != 2 for value in (start, end, bounds_min, bounds_max)):
        raise ValueError("segment and AABB inputs must be two-dimensional")
    sx, sy = (float(value) for value in start)
    ex, ey = (float(value) for value in end)
    min_x, min_y = (float(value) for value in bounds_min)
    max_x, max_y = (float(value) for value in bounds_max)
    radius = float(swept_radius_m)
    values = (sx, sy, ex, ey, min_x, min_y, max_x, max_y, radius)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("segment/AABB clearance inputs must be finite")
    if min_x > max_x or min_y > max_y:
        raise ValueError("AABB minimum must not exceed maximum")
    if radius < 0.0:
        raise ValueError("swept radius must be non-negative")

    def point_aabb_distance(point_x: float, point_y: float) -> float:
        dx = max(min_x - point_x, 0.0, point_x - max_x)
        dy = max(min_y - point_y, 0.0, point_y - max_y)
        return math.hypot(dx, dy)

    def orientation(ax, ay, bx, by, cx, cy) -> float:
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)

    def on_segment(ax, ay, bx, by, px, py) -> bool:
        return (
            min(ax, bx) - 1.0e-12 <= px <= max(ax, bx) + 1.0e-12
            and min(ay, by) - 1.0e-12 <= py <= max(ay, by) + 1.0e-12
        )

    def segments_intersect(a, b, c, d) -> bool:
        values = (
            orientation(*a, *b, *c),
            orientation(*a, *b, *d),
            orientation(*c, *d, *a),
            orientation(*c, *d, *b),
        )
        if values[0] * values[1] < 0.0 and values[2] * values[3] < 0.0:
            return True
        return any(
            abs(value) <= 1.0e-12 and on_segment(*segment[0], *segment[1], *point)
            for value, segment, point in (
                (values[0], (a, b), c),
                (values[1], (a, b), d),
                (values[2], (c, d), a),
                (values[3], (c, d), b),
            )
        )

    segment = ((sx, sy), (ex, ey))
    corners = (
        (min_x, min_y),
        (min_x, max_y),
        (max_x, max_y),
        (max_x, min_y),
    )
    edges = tuple(zip(corners, corners[1:] + corners[:1]))
    centre_distance = min(point_aabb_distance(sx, sy), point_aabb_distance(ex, ey))
    if centre_distance > 0.0 and not any(
        segments_intersect(segment[0], segment[1], edge[0], edge[1])
        for edge in edges
    ):
        centre_distance = min(
            centre_distance,
            *(point_to_segment_distance_2d(corner, start, end) for corner in corners),
        )
    else:
        centre_distance = 0.0
    return centre_distance - radius


def assert_command_visible_in_critic(
    critic_observation: Sequence[float],
    command: Sequence[float],
    command_offset: int = 9,
    tolerance: float = 1.0e-6,
) -> Tuple[float, float, float]:
    """Check the V17 teacher critic's live command slice."""

    if len(command) != 3 or command_offset < 0:
        raise ValueError("command or command_offset is invalid")
    if len(critic_observation) < command_offset + 3:
        raise ValueError("critic observation is too short for the command slice")
    observed = tuple(float(value) for value in critic_observation[command_offset : command_offset + 3])
    expected = tuple(float(value) for value in command)
    if not all(math.isfinite(value) for value in observed + expected):
        raise ValueError("command comparison contains a non-finite value")
    if any(abs(left - right) > tolerance for left, right in zip(observed, expected)):
        raise ValueError(
            "live command is not visible in the critic observation: "
            f"observed={observed}, expected={expected}"
        )
    return observed

"""Pure deterministic schedule contract for the Office eight-person trial."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence


@dataclass(frozen=True)
class OfficePedestrianRoute:
    name: str
    start_xy_m: tuple[float, float]
    end_xy_m: tuple[float, float]
    speed_mps: float
    start_delay_s: float
    radius_m: float = 0.30
    motion_mode: str = "single_pass"
    turnaround_hold_s: float = 0.0

    @property
    def distance_m(self) -> float:
        return math.dist(self.start_xy_m, self.end_xy_m)

    @property
    def travel_time_s(self) -> float:
        return self.distance_m / self.speed_mps


def office_pedestrian_state(elapsed_s: float, route: OfficePedestrianRoute) -> dict:
    if not math.isfinite(elapsed_s) or elapsed_s < 0.0:
        raise ValueError("elapsed time must be finite and non-negative")
    if route.motion_mode not in ("single_pass", "ping_pong"):
        raise ValueError(f"unsupported Office pedestrian motion mode: {route.motion_mode}")
    if route.motion_mode == "ping_pong" and (
        not math.isfinite(route.turnaround_hold_s) or route.turnaround_hold_s <= 0.0
    ):
        raise ValueError("ping-pong Office pedestrians require a positive turnaround hold")

    forward_yaw = math.atan2(
        route.end_xy_m[1] - route.start_xy_m[1],
        route.end_xy_m[0] - route.start_xy_m[0],
    )
    forward_velocity = (
        route.speed_mps
        * (route.end_xy_m[0] - route.start_xy_m[0])
        / route.distance_m,
        route.speed_mps
        * (route.end_xy_m[1] - route.start_xy_m[1])
        / route.distance_m,
    )

    if route.motion_mode == "single_pass":
        progress = min(
            max((elapsed_s - route.start_delay_s) / route.travel_time_s, 0.0),
            1.0,
        )
        phase = (
            "waiting"
            if progress <= 0.0
            else "arrived"
            if progress >= 1.0
            else "walking"
        )
        velocity_xy_mps = forward_velocity if phase == "walking" else (0.0, 0.0)
        yaw = forward_yaw
        direction = "forward"
        cycle_index = 0
    elif elapsed_s < route.start_delay_s:
        progress = 0.0
        phase = "waiting"
        velocity_xy_mps = (0.0, 0.0)
        yaw = forward_yaw
        direction = "forward"
        cycle_index = 0
    else:
        moving_elapsed_s = elapsed_s - route.start_delay_s
        cycle_duration_s = 2.0 * (
            route.travel_time_s + route.turnaround_hold_s
        )
        cycle_index = int(moving_elapsed_s // cycle_duration_s)
        cycle_elapsed_s = moving_elapsed_s % cycle_duration_s
        forward_end_s = route.travel_time_s
        end_turn_end_s = forward_end_s + route.turnaround_hold_s
        reverse_end_s = end_turn_end_s + route.travel_time_s

        if cycle_elapsed_s < forward_end_s:
            progress = cycle_elapsed_s / route.travel_time_s
            phase = "walking"
            velocity_xy_mps = forward_velocity
            yaw = forward_yaw
            direction = "forward"
        elif cycle_elapsed_s < end_turn_end_s:
            turn_progress = (
                cycle_elapsed_s - forward_end_s
            ) / route.turnaround_hold_s
            progress = 1.0
            phase = "turning"
            velocity_xy_mps = (0.0, 0.0)
            yaw = forward_yaw + math.pi * turn_progress
            direction = "turning_to_reverse"
        elif cycle_elapsed_s < reverse_end_s:
            reverse_progress = (
                cycle_elapsed_s - end_turn_end_s
            ) / route.travel_time_s
            progress = 1.0 - reverse_progress
            phase = "walking"
            velocity_xy_mps = tuple(-value for value in forward_velocity)
            yaw = forward_yaw + math.pi
            direction = "reverse"
        else:
            turn_progress = (
                cycle_elapsed_s - reverse_end_s
            ) / route.turnaround_hold_s
            progress = 0.0
            phase = "turning"
            velocity_xy_mps = (0.0, 0.0)
            yaw = forward_yaw + math.pi * (1.0 + turn_progress)
            direction = "turning_to_forward"

    x = route.start_xy_m[0] + progress * (route.end_xy_m[0] - route.start_xy_m[0])
    y = route.start_xy_m[1] + progress * (route.end_xy_m[1] - route.start_xy_m[1])
    return {
        "xy_m": (x, y),
        "yaw_rad": yaw,
        "progress": progress,
        "phase": phase,
        "velocity_xy_mps": velocity_xy_mps,
        "direction": direction,
        "cycle_index": cycle_index,
    }


def routes_from_preflight(
    payload: Mapping[str, object],
    motion_mode: str = "single_pass",
    turnaround_hold_s: float = 0.0,
) -> tuple[OfficePedestrianRoute, ...]:
    if motion_mode not in ("single_pass", "background_ping_pong", "ping_pong"):
        raise ValueError(f"unsupported Office pedestrian motion mode: {motion_mode}")
    if motion_mode != "single_pass" and (
        not math.isfinite(turnaround_hold_s) or turnaround_hold_s <= 0.0
    ):
        raise ValueError("ping-pong Office pedestrians require a positive turnaround hold")
    crossings = list(payload["crossing_pedestrians"])
    background = list(payload["background_pedestrians"])
    if len(crossings) < 2 or len(crossings) + len(background) != 8:
        raise ValueError(
            "Office crowd contract requires eight routes with at least two crossings"
        )
    path_length = float(payload["path_length_m"])
    robot_speed = 0.60
    routes = []
    for row in crossings:
        arrival_s = float(row["nominal_path_fraction"]) * path_length / robot_speed
        distance = math.dist(row["start_xy_m"], row["end_xy_m"])
        travel_time = distance / float(row["speed_mps"])
        derived_start_delay_s = max(
            0.0, arrival_s - (travel_time / 2.0) - 3.0
        )
        route_motion_mode = (
            "single_pass" if motion_mode == "background_ping_pong" else motion_mode
        )
        routes.append(
            OfficePedestrianRoute(
                name=str(row["name"]),
                start_xy_m=tuple(row["start_xy_m"]),
                end_xy_m=tuple(row["end_xy_m"]),
                speed_mps=float(row["speed_mps"]),
                # A measured dry-run delay may override the nominal 0.60 m/s
                # estimate. It remains immutable scenario input and never enters
                # SCAN; sensor observations are still the only planner trigger.
                start_delay_s=float(
                    row.get("start_delay_s", derived_start_delay_s)
                ),
                motion_mode=route_motion_mode,
                turnaround_hold_s=(
                    0.0 if route_motion_mode == "single_pass" else turnaround_hold_s
                ),
            )
        )
    background_delays = tuple(6.0 * index for index in range(len(background)))
    for row, delay in zip(background, background_delays, strict=True):
        route_motion_mode = (
            "ping_pong" if motion_mode == "background_ping_pong" else motion_mode
        )
        routes.append(
            OfficePedestrianRoute(
                name=str(row["name"]),
                start_xy_m=tuple(row["start_xy_m"]),
                end_xy_m=tuple(row["end_xy_m"]),
                speed_mps=float(row["speed_mps"]),
                start_delay_s=delay,
                motion_mode=route_motion_mode,
                turnaround_hold_s=(
                    0.0 if route_motion_mode == "single_pass" else turnaround_hold_s
                ),
            )
        )
    return tuple(routes)


def pairwise_clearance_precheck(
    routes: Sequence[OfficePedestrianRoute], duration_s: float, dt_s: float = 0.05
) -> dict:
    if duration_s <= 0.0 or dt_s <= 0.0:
        raise ValueError("precheck duration and dt must be positive")
    minimum = math.inf
    minimum_pair = None
    minimum_time = None
    steps = int(math.ceil(duration_s / dt_s)) + 1
    for step in range(steps):
        elapsed = min(duration_s, step * dt_s)
        states = [office_pedestrian_state(elapsed, route) for route in routes]
        for first in range(len(routes)):
            for second in range(first + 1, len(routes)):
                clearance = (
                    math.dist(states[first]["xy_m"], states[second]["xy_m"])
                    - routes[first].radius_m
                    - routes[second].radius_m
                )
                if clearance < minimum:
                    minimum = clearance
                    minimum_pair = (routes[first].name, routes[second].name)
                    minimum_time = elapsed
    return {
        "passed": minimum >= 0.05,
        "minimum_surface_clearance_m": minimum,
        "minimum_pair": minimum_pair,
        "minimum_time_s": minimum_time,
        "duration_s": duration_s,
        "dt_s": dt_s,
    }

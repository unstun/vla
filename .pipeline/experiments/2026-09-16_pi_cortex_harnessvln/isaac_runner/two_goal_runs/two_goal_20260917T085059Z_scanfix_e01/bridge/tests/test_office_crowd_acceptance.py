"""Tests for Office video quality and sensor-to-SCAN causal replanning."""

from __future__ import annotations

from pathlib import Path

import pytest

from lite3_sim_bridge.office_crowd_acceptance import (
    _mapped_event_time,
    _pedestrian_motion_fidelity,
    _runtime_gate_metrics,
    audit_active_path_causal_replans,
    verify_video_quality,
)
from lite3_sim_bridge.office_crowd_contract import OfficePedestrianRoute


@pytest.fixture
def dryrun11_dir() -> Path:
    path = Path(__file__).resolve().parents[3] / (
        ".pipeline/experiments/2026-08-17_office_l0_scan_crowd/"
        "results/office_crowd_dryrun11"
    )
    if not path.is_dir() or not (path / "closed_loop.mp4").is_file():
        pytest.skip(f"complete dryrun11 video fixture not found at {path}")
    return path


@pytest.fixture
def crossing_route() -> OfficePedestrianRoute:
    return OfficePedestrianRoute(
        name="crossing_1",
        start_xy_m=(-10.375, 9.375),
        end_xy_m=(-6.375, 9.375),
        speed_mps=0.8,
        start_delay_s=10.0,
        radius_m=0.30,
    )


@pytest.fixture
def sample_waypoints() -> list[list[float]]:
    return [
        [-11.625, 10.125, 0.85],
        [-8.375, 6.375, 0.85],
        [-8.375, -0.625, 0.85],
    ]


def _metrics(robot_xy=(-11.6, 10.1)) -> list[dict]:
    return [
        {
            "sim_time_seconds": index * 0.1,
            "root_pos_w": [robot_xy[0], robot_xy[1], 0.3],
        }
        for index in range(300)
    ]


def test_runtime_gate_metrics_preserve_terminal_and_step_evidence() -> None:
    rows = [
        {
            "sim_time_seconds": float(index),
            "root_pos_w": [0.01 * index, 0.0, 0.3],
            "root_lin_vel_w": [0.01, 0.0, 0.0],
            "applied_command": [0.0, 0.0, 0.0],
            "done": False,
        }
        for index in range(4)
    ]
    result = _runtime_gate_metrics(
        rows, [{"point_count": 10}, {"point_count": 0}], 2.0
    )

    assert result["maximum_step_displacement_m"] == pytest.approx(0.01)
    assert result["terminal_command_max_abs"] == 0.0
    assert result["terminal_planar_speed_max_mps"] == pytest.approx(0.01)
    assert result["cloud_nonempty_fraction"] == 0.5
    assert result["timestamps_advance"] is True
    assert result["termination_count"] == 0


def test_pedestrian_motion_fidelity_detects_in_place_walk() -> None:
    rows = [
        {
            "office_pedestrians": [
                {
                    "name": "person",
                    "velocity_xy_mps": [0.0, 0.0],
                    "animation": {"clip": "walk"},
                }
            ]
        }
    ]

    result = _pedestrian_motion_fidelity(rows)

    assert result["in_place_walk_fraction"] == 1.0
    assert result["root_moving_fraction"] == 0.0


def test_bspline_uses_recent_monitor_captured_simulator_stamp() -> None:
    event = {
        "kind": "bspline",
        "simulator_stamp_ns": 12_300_000_000,
        "simulator_stamp_receipt_age_s": 0.04,
        "receipt_monotonic_ns": 99_000_000_000,
    }

    mapped, error = _mapped_event_time(event, [], [], 0.20)

    assert mapped == pytest.approx(12.3)
    assert error == pytest.approx(0.04)


def test_bspline_rejects_stale_monitor_captured_simulator_stamp() -> None:
    event = {
        "kind": "bspline",
        "simulator_stamp_ns": 12_300_000_000,
        "simulator_stamp_receipt_age_s": 0.21,
        "receipt_monotonic_ns": 99_000_000_000,
    }

    mapped, error = _mapped_event_time(event, [], [], 0.20)

    assert mapped is None
    assert error == pytest.approx(0.21)


def test_bspline_interpolates_on_simulator_time_not_slow_wall_clock() -> None:
    event = {
        "kind": "bspline",
        "simulator_stamp_ns": 1_000_000_000,
        "simulator_stamp_receipt_age_s": 0.25,
        "receipt_monotonic_ns": 250_000_000,
    }
    pose_events = [(0, 1.0), (500_000_000, 1.1)]

    mapped, error = _mapped_event_time(
        event, pose_events, [0, 500_000_000], 0.20
    )

    assert mapped == pytest.approx(1.05)
    assert error == pytest.approx(0.10)


def _body_pose_events() -> list[dict]:
    return [
        {
            "kind": "body_pose",
            "receipt_monotonic_ns": index * 100_000_000,
            "stamp_ns": index * 100_000_000,
            "position": [-11.6, 10.1, 0.3],
        }
        for index in range(300)
    ]


def _bspline_event(
    trajectory_id: int, time_s: float, points: list[list[float]]
) -> dict:
    degree = min(2, len(points) - 1)
    knots = [0.0] * (degree + 1) + [1.0] * (degree + 1)
    return {
        "kind": "bspline",
        "trajectory_id": trajectory_id,
        "receipt_monotonic_ns": int(time_s * 1.0e9),
        "start_time_ns": int(time_s * 1.0e9),
        "order": degree,
        "knots": knots,
        "control_points": points,
    }


def _person_rows(
    detection_time_s: float | None, route_name: str = "crossing_1"
) -> tuple[list[dict], list[dict]]:
    sensor_rows = []
    depth_rows = []
    for index in range(300):
        time_s = index * 0.1
        detected = detection_time_s is not None and abs(
            time_s - detection_time_s
        ) < 0.051
        sensor_rows.append(
            {
                "sim_time_seconds": time_s,
                "office_pedestrian_surface_hit_count": 12 if detected else 0,
                "office_pedestrian_surface_hit_counts": {
                    route_name: 12 if detected else 0
                },
            }
        )
        depth_rows.append(
            {
                "sim_time_seconds": time_s,
                "office_pedestrian_surface_pixel_count": 20 if detected else 0,
                "office_pedestrian_surface_pixel_counts": {
                    route_name: 20 if detected else 0
                },
            }
        )
    return sensor_rows, depth_rows


def _occupancy_event(time_s: float, point_xy: tuple[float, float]) -> dict:
    return {
        "kind": "occupancy_inflate",
        "receipt_monotonic_ns": int(time_s * 1.0e9),
        "stamp_ns": int(time_s * 1.0e9),
        "point_count": 1,
        "sample_count": 1,
        "points_xyz": [[point_xy[0], point_xy[1], 0.8]],
    }


def _run_audit(
    *,
    route: OfficePedestrianRoute,
    waypoints: list[list[float]],
    plans: list[dict],
    detection_time_s: float | None,
    occupancy_event: dict | None,
    robot_xy=(-11.6, 10.1),
) -> dict:
    sensor_rows, depth_rows = _person_rows(detection_time_s, route.name)
    events = _body_pose_events() + plans
    if occupancy_event is not None:
        events.append(occupancy_event)
    return audit_active_path_causal_replans(
        metrics_rows=_metrics(robot_xy),
        sensor_rows=sensor_rows,
        depth_rows=depth_rows,
        ros_events=events,
        routes=[route],
        sparse_waypoints=waypoints,
    )


def _reactive_plans() -> list[dict]:
    return [
        _bspline_event(
            1,
            5.0,
            [[-11.6, 10.1, 0.3], [-9.0, 9.375, 0.3], [-8.375, 6.375, 0.3]],
        ),
        _bspline_event(
            2,
            12.5,
            [[-11.6, 10.1, 0.3], [-9.0, 10.25, 0.3], [-8.375, 6.375, 0.3]],
        ),
    ]


def test_dryrun11_blank_video_rejected(dryrun11_dir: Path) -> None:
    result = verify_video_quality(dryrun11_dir / "closed_loop.mp4")
    assert result["passed"] is False
    assert result["nonblank_fraction"] < 0.10


def test_waypoint_progression_does_not_count_as_replan(
    crossing_route, sample_waypoints
) -> None:
    plans = [
        _bspline_event(1, 5.0, [[-15.6, 13.1, 0.3], [-11.625, 10.125, 0.3]]),
        _bspline_event(2, 12.5, [[-11.625, 10.125, 0.3], [-8.375, 6.375, 0.3]]),
    ]
    result = _run_audit(
        route=crossing_route,
        waypoints=sample_waypoints,
        plans=plans,
        detection_time_s=12.4,
        occupancy_event=_occupancy_event(12.4, (-8.45, 9.375)),
    )
    assert result["passed"] is False
    assert result["reactive_replan_count"] == 0


def test_identical_republication_does_not_count(
    crossing_route, sample_waypoints
) -> None:
    path = [[-11.6, 10.1, 0.3], [-9.0, 9.375, 0.3], [-8.375, 6.375, 0.3]]
    plans = [_bspline_event(1, 5.0, path), _bspline_event(2, 12.5, path)]
    result = _run_audit(
        route=crossing_route,
        waypoints=sample_waypoints,
        plans=plans,
        detection_time_s=12.4,
        occupancy_event=_occupancy_event(12.4, (-8.45, 9.375)),
    )
    assert result["passed"] is False


def test_genuine_sensor_map_plan_chain_passes(
    crossing_route, sample_waypoints
) -> None:
    result = _run_audit(
        route=crossing_route,
        waypoints=sample_waypoints,
        plans=_reactive_plans(),
        detection_time_s=12.4,
        occupancy_event=_occupancy_event(12.4, (-8.45, 9.375)),
    )
    assert result["passed"] is True
    evidence = result["reactive_replans"][0]
    assert evidence["trigger_pedestrian"] == "crossing_1"
    assert evidence["lidar_hit_count"] == 12
    assert evidence["scan_occupancy"]["sample_count"] == 1


@pytest.mark.parametrize("missing", ["sensor", "occupancy"])
def test_missing_sensor_or_scan_occupancy_fails(
    crossing_route, sample_waypoints, missing
) -> None:
    result = _run_audit(
        route=crossing_route,
        waypoints=sample_waypoints,
        plans=_reactive_plans(),
        detection_time_s=None if missing == "sensor" else 12.4,
        occupancy_event=(
            None
            if missing == "occupancy"
            else _occupancy_event(12.4, (-8.45, 9.375))
        ),
    )
    assert result["passed"] is False


def test_person_detected_but_not_on_remaining_path_fails(sample_waypoints) -> None:
    distant = OfficePedestrianRoute(
        name="crossing_1",
        start_xy_m=(0.0, 0.0),
        end_xy_m=(0.0, 5.0),
        speed_mps=1.0,
        start_delay_s=10.0,
        radius_m=0.30,
    )
    result = _run_audit(
        route=distant,
        waypoints=sample_waypoints,
        plans=_reactive_plans(),
        detection_time_s=12.4,
        occupancy_event=_occupancy_event(12.4, (0.0, 2.4)),
    )
    assert result["passed"] is False


def test_replan_after_person_arrived_fails(
    crossing_route, sample_waypoints
) -> None:
    plans = [
        _reactive_plans()[0],
        _bspline_event(
            2,
            28.0,
            [[-11.6, 10.1, 0.3], [-9.0, 10.25, 0.3], [-8.375, 6.375, 0.3]],
        ),
    ]
    result = _run_audit(
        route=crossing_route,
        waypoints=sample_waypoints,
        plans=plans,
        detection_time_s=27.9,
        occupancy_event=_occupancy_event(27.9, crossing_route.end_xy_m),
    )
    assert result["passed"] is False


def test_unsynchronized_receipt_clock_fails(
    crossing_route, sample_waypoints
) -> None:
    plans = _reactive_plans()
    plans[1]["receipt_monotonic_ns"] = int(12.55 * 1.0e9)
    events = [
        event
        for event in _body_pose_events()
        if not 11.0 <= event["stamp_ns"] * 1.0e-9 <= 14.0
    ] + plans + [_occupancy_event(12.4, (-8.45, 9.375))]
    sensor_rows, depth_rows = _person_rows(12.4)
    result = audit_active_path_causal_replans(
        metrics_rows=_metrics(),
        sensor_rows=sensor_rows,
        depth_rows=depth_rows,
        ros_events=events,
        routes=[crossing_route],
        sparse_waypoints=sample_waypoints,
    )
    assert result["passed"] is False
    assert "align" in result["reason"]

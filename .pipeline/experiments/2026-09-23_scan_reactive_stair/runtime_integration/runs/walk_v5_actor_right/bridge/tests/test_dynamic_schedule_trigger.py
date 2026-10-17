from argparse import Namespace

import pytest

from lite3_sim_bridge.run_isaac_lite3 import AdapterFailure
from lite3_sim_bridge.run_isaac_v12_fallback import (
    _dynamic_obstacle_spec,
    _dynamic_route_static_geometry_checks,
    _dynamic_schedule_trigger_identity,
)
from lite3_sim_bridge.isaac_adapter_core import DynamicObstacleSpec


def test_dynamic_schedule_default_trigger_identity_is_preserved():
    assert (
        _dynamic_schedule_trigger_identity("first_nonzero_body_command")
        == "first nonzero accepted body command"
    )


def test_dynamic_schedule_run_start_trigger_is_explicit():
    assert _dynamic_schedule_trigger_identity("run_start") == "closed-loop run start"


def test_dynamic_schedule_trigger_rejects_unknown_mode():
    with pytest.raises(AdapterFailure, match="unsupported dynamic schedule trigger"):
        _dynamic_schedule_trigger_identity("unknown")


def test_dynamic_route_endpoint_x_is_optional_and_backward_compatible():
    args = Namespace(
        course="forest_gen_nav_v8_official_human",
        dynamic_obstacle_x=-3.6,
        dynamic_obstacle_end_x=-1.17,
        dynamic_obstacle_start_y=1.6,
        dynamic_obstacle_end_y=15.39,
        dynamic_obstacle_wait_seconds=0.0,
        dynamic_obstacle_speed=0.8,
        dynamic_obstacle_radius=0.3,
        dynamic_obstacle_height=1.7,
        dynamic_obstacle_terrain_clearance=0.02,
        dynamic_obstacle_hold_fraction=0.5,
        dynamic_obstacle_hold_seconds=0.0,
    )

    assert _dynamic_obstacle_spec(args).end_xy == (-1.17, 15.39)
    args.dynamic_obstacle_end_x = None
    assert _dynamic_obstacle_spec(args).end_xy == (-3.6, 15.39)


def _route_spec(x):
    return DynamicObstacleSpec(
        name="official_human",
        start_xy=(x, 1.6),
        end_xy=(x, 16.0),
        wait_seconds=0.0,
        speed_mps=0.8,
        radius_m=0.30,
        height_m=1.70,
        terrain_clearance_m=0.02,
    )


def test_dynamic_route_precheck_rejects_the_observed_rock_penetration():
    layout = {
        "proxies": [
            {
                "name": "forest_proxy_008",
                "kind": "Rock",
                "prim_path": "/World/forest_collision/proxy_008",
                "bounds_min_m": [-2.936428833, 0.652020359, 0.0],
                "bounds_max_m": [-1.401905656, 1.915158415, 2.0],
            }
        ]
    }

    report = _dynamic_route_static_geometry_checks(layout, _route_spec(-2.7))

    assert report["passed"] is False
    assert report["nearest_static_object"]["name"] == "forest_proxy_008"
    assert report["minimum_static_clearance_m"] == pytest.approx(-0.30)


def test_dynamic_route_precheck_accepts_a_clear_parallel_route():
    layout = {
        "proxies": [
            {
                "name": "forest_proxy_008",
                "kind": "Rock",
                "prim_path": "/World/forest_collision/proxy_008",
                "bounds_min_m": [-2.936428833, 0.652020359, 0.0],
                "bounds_max_m": [-1.401905656, 1.915158415, 2.0],
            }
        ]
    }

    report = _dynamic_route_static_geometry_checks(layout, _route_spec(-4.0))

    assert report["passed"] is True
    assert report["minimum_static_clearance_m"] == pytest.approx(0.763571167)

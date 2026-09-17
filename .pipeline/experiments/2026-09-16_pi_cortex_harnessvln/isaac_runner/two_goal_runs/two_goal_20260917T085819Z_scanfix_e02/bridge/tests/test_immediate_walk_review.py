from lite3_sim_bridge.immediate_walk_review import (
    causal_plan_replacement,
    directional_plan_deviation_2d,
    point_to_polyline_distance_2d,
)


def _plan(trajectory_id, time_seconds, y):
    return {
        "trajectory_id": trajectory_id,
        "effective_sim_time_seconds": time_seconds,
        "sampled_points": [(0.0, y, 0.0), (4.0, y, 0.0)],
    }


def test_polyline_distance_and_directional_deviation_ignore_path_truncation():
    assert point_to_polyline_distance_2d((2.0, 1.0), [(0.0, 0.0), (4.0, 0.0)]) == 1.0
    assert directional_plan_deviation_2d(
        [(2.0, 0.0), (4.0, 0.0)], [(0.0, 0.0), (4.0, 0.0)]
    ) == 0.0
    assert directional_plan_deviation_2d(
        [(0.0, 1.0), (4.0, 1.0)], [(0.0, 0.0), (4.0, 0.0)]
    ) == 1.0


def test_causal_plan_replacement_requires_intrusion_then_changed_plan():
    plans = [_plan(1, 0.0, 0.0), _plan(2, 1.2, 1.0)]
    metrics = [
        {
            "sim_time_seconds": 0.5,
            "dynamic_obstacle_actual_pos_w": [2.0, 1.2, 0.0],
        },
        {
            "sim_time_seconds": 0.8,
            "dynamic_obstacle_actual_pos_w": [2.0, 0.7, 0.0],
        },
    ]

    report = causal_plan_replacement(
        plans,
        metrics,
        maximum_active_path_distance_m=0.85,
        minimum_plan_deviation_m=0.15,
        maximum_response_seconds=1.0,
    )

    assert report["passed"] is True
    assert report["active_trajectory_id"] == 1
    assert report["replacement_trajectory_id"] == 2
    assert report["first_active_path_intrusion_sim_time_seconds"] == 0.8


def test_causal_plan_replacement_rejects_existing_plans_before_intrusion():
    plans = [_plan(1, 0.0, 0.0), _plan(2, 0.4, 1.0)]
    metrics = [
        {
            "sim_time_seconds": 0.8,
            "dynamic_obstacle_actual_pos_w": [2.0, 0.7, 0.0],
        }
    ]

    report = causal_plan_replacement(
        plans,
        metrics,
        maximum_active_path_distance_m=0.85,
        minimum_plan_deviation_m=0.15,
        maximum_response_seconds=1.0,
    )

    assert report["passed"] is False

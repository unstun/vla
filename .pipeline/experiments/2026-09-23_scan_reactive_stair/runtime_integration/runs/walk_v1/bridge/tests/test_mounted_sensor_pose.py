import math

import numpy as np
import pytest

from lite3_sim_bridge.isaac_adapter_core import mounted_sensor_pose, rotation_matrix_from_wxyz, split_geometry_cloud_points


def test_mounted_pose_matches_independent_ray_construction():
    # An asymmetric mount, 90-degree body yaw, and 15-degree sensor pitch.
    prim = [2.0, -1.0, 0.7]
    body_q = [math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)]
    offset = [0.18, -0.03, 0.11]
    pitch = math.radians(15)
    mount_q = [math.cos(pitch / 2), 0.0, math.sin(pitch / 2), 0.0]
    position, quaternion = mounted_sensor_pose(prim, body_q, offset, mount_q)
    assert position == pytest.approx([2.03, -0.82, 0.81])
    body_r = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
    mount_r = np.array([[math.cos(pitch), 0, math.sin(pitch)], [0, 1, 0],
                        [-math.sin(pitch), 0, math.cos(pitch)]])
    direction_sensor = np.array([0.8, 0.3, -0.1])
    # Same composition as installed RayCaster._initialize_rays_impl and
    # _update_ray_infos, with independent explicit rotation matrices.
    ray_origin = np.array(prim) + body_r @ offset
    world_hit = ray_origin + 2.0 * body_r @ mount_r @ direction_sensor
    recovered = np.array(rotation_matrix_from_wxyz(quaternion)).T @ (world_hit - position)
    assert recovered == pytest.approx(2.0 * direction_sensor)
    wrong = np.array(rotation_matrix_from_wxyz(body_q)).T @ (world_hit - prim)
    assert np.linalg.norm(wrong - recovered) > 0.1

    raw, planner, stats = split_geometry_cloud_points(
        [world_hit, world_hit - np.array([0, 0, 0.5])],
        position, quaternion, 0.1, 12.0, 0.3, 0.12, 1, 1)
    assert np.asarray(raw)[0] == pytest.approx(2.0 * direction_sensor)
    assert np.asarray(planner)[0] == pytest.approx(2.0 * direction_sensor)

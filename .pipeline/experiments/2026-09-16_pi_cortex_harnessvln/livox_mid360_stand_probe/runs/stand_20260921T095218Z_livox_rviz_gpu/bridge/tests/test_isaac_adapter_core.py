import math
import unittest

from lite3_sim_bridge.isaac_adapter_core import (
    DEFAULT_QUALIFICATION_SCHEDULE,
    DynamicObstacleSpec,
    assert_command_visible_in_critic,
    canonical_config_sha256,
    circle_surface_clearance_2d,
    dynamic_obstacle_state,
    expand_isaac_env_regex_ns,
    official_human_registered_state,
    retarget_joint_indices,
    local_minimum_obstacle_hits,
    split_geometry_cloud_points,
    point_to_segment_distance_2d,
    procedural_human_gait_angles,
    quaternion_wxyz_to_xyzw,
    rotation_matrix_from_wxyz,
    schedule_duration,
    schedule_state,
    segment_to_aabb_clearance_2d,
    terrain_seating_for_bounds,
    terrain_seating_for_mesh_support,
    world_hits_to_sensor_points,
)


class IsaacAdapterCoreTest(unittest.TestCase):
    def test_dynamic_obstacle_wait_cross_and_park_schedule(self):
        spec = DynamicObstacleSpec(
            name="crossing_actor",
            start_xy=(-3.5, 1.2),
            end_xy=(-3.5, 4.8),
            wait_seconds=3.5,
            speed_mps=0.8,
            radius_m=0.30,
            height_m=1.50,
            terrain_clearance_m=0.02,
            hold_fraction=0.5,
            hold_seconds=2.0,
        )
        waiting = dynamic_obstacle_state(2.0, spec, lambda x, y: x * 0.01 + y * 0.02)
        self.assertEqual(waiting["phase"], "waiting")
        self.assertEqual(waiting["center_xy_m"], (-3.5, 1.2))
        self.assertEqual(waiting["velocity_xy_mps"], (0.0, 0.0))

        crossing = dynamic_obstacle_state(4.5, spec, lambda _x, _y: 0.25)
        self.assertEqual(crossing["phase"], "crossing")
        self.assertAlmostEqual(crossing["center_xy_m"][0], -3.5)
        self.assertAlmostEqual(crossing["center_xy_m"][1], 2.0)
        self.assertEqual(crossing["velocity_xy_mps"], (0.0, 0.8))
        self.assertAlmostEqual(crossing["center_xyz_m"][2], 1.02)
        self.assertAlmostEqual(crossing["bottom_terrain_clearance_m"], 0.02)

        holding = dynamic_obstacle_state(7.0, spec, lambda _x, _y: 0.25)
        self.assertEqual(holding["phase"], "holding")
        self.assertAlmostEqual(holding["center_xy_m"][1], 3.0)
        self.assertEqual(holding["velocity_xy_mps"], (0.0, 0.0))

        parked = dynamic_obstacle_state(20.0, spec, lambda _x, _y: 0.10)
        self.assertEqual(parked["phase"], "parked")
        self.assertEqual(parked["center_xy_m"], (-3.5, 4.8))
        self.assertEqual(parked["velocity_xy_mps"], (0.0, 0.0))
        self.assertAlmostEqual(spec.crossing_duration_seconds, 4.5)
        self.assertAlmostEqual(crossing["heading_yaw_radians"], math.pi / 2.0)

    def test_official_human_registration_separates_foot_and_capsule_datums(self):
        spec = DynamicObstacleSpec(
            name="official_human",
            start_xy=(-3.0, 1.2),
            end_xy=(-3.0, 4.8),
            wait_seconds=0.2,
            speed_mps=0.8,
            radius_m=0.30,
            height_m=1.70,
            terrain_clearance_m=0.02,
        )
        state = dynamic_obstacle_state(1.0, spec, lambda _x, _y: 0.35)
        registered = official_human_registered_state(
            state,
            spec,
            source_foot_z_m=-1.9355964298028994e-7,
            source_visible_top_z_m=1.7357525825500488,
            source_forward_yaw_radians=-math.pi / 2.0,
        )
        self.assertAlmostEqual(registered["visual_root_xyz_m"][2], 0.37000019356)
        self.assertAlmostEqual(registered["visual_foot_world_z_m"], 0.37)
        self.assertAlmostEqual(registered["capsule_bottom_world_z_m"], 0.37)
        self.assertAlmostEqual(registered["capsule_center_xyz_m"][2], 1.22)
        self.assertAlmostEqual(registered["visual_top_world_z_m"], 2.10575277611)
        self.assertAlmostEqual(registered["visual_yaw_radians"], math.pi)
        self.assertAlmostEqual(registered["visual_quaternion_wxyz"][0], 0.0)
        self.assertAlmostEqual(registered["visual_quaternion_wxyz"][3], 1.0)

    def test_official_animation_joint_retarget_is_name_based_and_complete(self):
        self.assertEqual(
            retarget_joint_indices(
                ("root", "hip", "face", "left_foot"),
                ("root", "hip", "left_foot"),
            ),
            (0, 1, None, 2),
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            retarget_joint_indices(("root", "root"), ("root",))
        with self.assertRaisesRegex(ValueError, "absent"):
            retarget_joint_indices(("root",), ("root", "unknown"))

    def test_procedural_human_gait_is_opposed_and_crossing_only(self):
        neutral = procedural_human_gait_angles(0.25, "holding")
        self.assertTrue(all(value == 0.0 for value in neutral.values()))

        gait = procedural_human_gait_angles(
            0.5,
            "crossing",
            cadence_hz=0.5,
            maximum_swing_radians=0.4,
        )
        self.assertAlmostEqual(gait["left_leg_radians"], 0.4)
        self.assertAlmostEqual(gait["right_arm_radians"], 0.4)
        self.assertAlmostEqual(gait["right_leg_radians"], -0.4)
        self.assertAlmostEqual(gait["left_arm_radians"], -0.4)

        with self.assertRaisesRegex(ValueError, "phase"):
            procedural_human_gait_angles(0.0, "running")
        with self.assertRaisesRegex(ValueError, "cadence"):
            procedural_human_gait_angles(0.0, "crossing", cadence_hz=0.0)
        with self.assertRaisesRegex(ValueError, "swing"):
            procedural_human_gait_angles(
                0.0, "crossing", maximum_swing_radians=math.pi
            )

    def test_expand_isaac_env_regex_ns_matches_runtime_target(self):
        self.assertEqual(
            expand_isaac_env_regex_ns(
                "{ENV_REGEX_NS}/DynamicObstacle/Visual/Head"
            ),
            "/World/envs/env_.*/DynamicObstacle/Visual/Head",
        )
        with self.assertRaisesRegex(ValueError, "non-empty"):
            expand_isaac_env_regex_ns("")

    def test_dynamic_obstacle_contract_rejects_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            DynamicObstacleSpec(
                "bad", (0.0, 0.0), (0.0, 0.0), 1.0, 1.0, 0.2, 1.0, 0.0
            )
        with self.assertRaisesRegex(ValueError, "positive"):
            DynamicObstacleSpec(
                "bad", (0.0, 0.0), (1.0, 0.0), 1.0, 0.0, 0.2, 1.0, 0.0
            )
        with self.assertRaisesRegex(ValueError, "hold fraction"):
            DynamicObstacleSpec(
                "bad",
                (0.0, 0.0),
                (1.0, 0.0),
                1.0,
                1.0,
                0.2,
                1.0,
                0.0,
                hold_fraction=1.0,
            )
        spec = DynamicObstacleSpec(
            "actor", (0.0, 0.0), (1.0, 0.0), 1.0, 1.0, 0.2, 1.0, 0.0
        )
        with self.assertRaisesRegex(ValueError, "elapsed"):
            dynamic_obstacle_state(-0.1, spec, lambda _x, _y: 0.0)
        with self.assertRaisesRegex(ValueError, "terrain height"):
            dynamic_obstacle_state(0.0, spec, lambda _x, _y: float("nan"))

    def test_circle_surface_clearance_is_time_synchronized_geometry(self):
        self.assertAlmostEqual(
            circle_surface_clearance_2d((0.0, 0.0), (1.0, 0.0), 0.4, 0.3),
            0.3,
        )
        self.assertAlmostEqual(
            circle_surface_clearance_2d((0.0, 0.0), (0.5, 0.0), 0.4, 0.3),
            -0.2,
        )
        with self.assertRaisesRegex(ValueError, "radii"):
            circle_surface_clearance_2d((0.0, 0.0), (1.0, 0.0), -0.1, 0.3)

    def test_segment_to_aabb_clearance_catches_swept_penetration(self):
        self.assertAlmostEqual(
            segment_to_aabb_clearance_2d(
                (-2.7, 0.0),
                (-2.7, 16.0),
                (-2.9364, 0.6520),
                (-1.4019, 1.9152),
                swept_radius_m=0.30,
            ),
            -0.30,
        )
        self.assertAlmostEqual(
            segment_to_aabb_clearance_2d(
                (-4.0, 1.6),
                (-4.0, 16.0),
                (-2.9364, 0.6520),
                (-1.4019, 1.9152),
                swept_radius_m=0.30,
            ),
            0.7636,
            places=4,
        )
        self.assertAlmostEqual(
            segment_to_aabb_clearance_2d(
                (0.0, 0.0), (1.0, 0.0), (2.0, -1.0), (3.0, 1.0), 0.25
            ),
            0.75,
        )
        with self.assertRaisesRegex(ValueError, "minimum"):
            segment_to_aabb_clearance_2d(
                (0.0, 0.0), (1.0, 0.0), (2.0, 1.0), (1.0, 2.0)
            )

    def test_schedule_boundaries_and_disconnect(self):
        first, elapsed = schedule_state(0.25)
        self.assertEqual(first.name, "settle_zero")
        self.assertAlmostEqual(elapsed, 0.25)
        forward, elapsed = schedule_state(1.0)
        self.assertEqual(forward.name, "forward")
        self.assertEqual(elapsed, 0.0)
        last, _ = schedule_state(schedule_duration() + 1.0)
        self.assertEqual(last.name, "watchdog_disconnect")
        self.assertFalse(last.connected)
        self.assertGreater(schedule_duration(DEFAULT_QUALIFICATION_SCHEDULE), 8.0)

    def test_config_hash_is_canonical(self):
        left = canonical_config_sha256({"b": [2, 3], "a": 1})
        right = canonical_config_sha256({"a": 1, "b": [2, 3]})
        self.assertEqual(left, right)
        self.assertEqual(len(left), 32)

    def test_quaternion_conversion_and_rotation(self):
        xyzw = quaternion_wxyz_to_xyzw((2.0, 0.0, 0.0, 0.0))
        self.assertEqual(xyzw, (0.0, 0.0, 0.0, 1.0))
        rotation = rotation_matrix_from_wxyz(
            (math.cos(math.pi / 4), 0.0, 0.0, math.sin(math.pi / 4))
        )
        self.assertAlmostEqual(rotation[0][0], 0.0, places=6)
        self.assertAlmostEqual(rotation[1][0], 1.0, places=6)

    def test_world_hits_transform_filter_and_range(self):
        # Sensor yaw is +90 degrees. World +Y is sensor +X.
        points = world_hits_to_sensor_points(
            ((1.0, 3.0, 3.0), (float("inf"), 0.0, 0.0), (1.0, 1.99, 3.0)),
            (1.0, 2.0, 3.0),
            (math.cos(math.pi / 4), 0.0, 0.0, math.sin(math.pi / 4)),
            0.1,
            2.0,
        )
        self.assertEqual(len(points), 1)
        self.assertAlmostEqual(points[0][0], 1.0, places=6)
        self.assertAlmostEqual(points[0][1], 0.0, places=6)

    def test_world_hits_remove_declared_traversable_floor(self):
        points = world_hits_to_sensor_points(
            (
                (1.0, 0.0, 0.0),
                (1.0, 0.0, 0.05),
                (1.0, 0.0, 0.051),
            ),
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 0.0, 0.0),
            0.1,
            2.0,
            minimum_world_z=0.05,
        )
        self.assertEqual(len(points), 1)
        self.assertAlmostEqual(points[0][0], 1.0, places=6)
        self.assertAlmostEqual(points[0][2], -0.949, places=6)

    def test_world_hits_reject_nonfinite_floor_threshold(self):
        with self.assertRaisesRegex(ValueError, "minimum world z"):
            world_hits_to_sensor_points(
                ((1.0, 0.0, 1.0),),
                (0.0, 0.0, 1.0),
                (1.0, 0.0, 0.0, 0.0),
                0.1,
                2.0,
                minimum_world_z=float("nan"),
            )

    def test_local_minimum_filter_removes_slope_and_keeps_tree_and_rock(self):
        slope = []
        for x_index in range(6):
            for y_index in range(3):
                x = 0.30 * x_index
                y = 0.30 * y_index
                slope.append((x, y, 0.08 * x_index + 0.02 * y_index))
        # The obstacle cell has nearby rendered ground plus taller returns.
        slope.extend(
            (
                (0.90, 0.30, 0.26),
                (0.90, 0.30, 0.55),
                (0.90, 0.30, 1.20),
            )
        )
        obstacles, stats = local_minimum_obstacle_hits(
            slope,
            (-1.0, 0.0, 1.0),
            0.1,
            5.0,
            cell_size=0.30,
            height_threshold=0.22,
        )
        self.assertIn((0.90, 0.30, 0.55), obstacles)
        self.assertIn((0.90, 0.30, 1.20), obstacles)
        self.assertNotIn((0.90, 0.30, 0.26), obstacles)
        self.assertGreater(stats["filtered_ground_hit_count"], 10)
        self.assertEqual(stats["obstacle_hit_count"], 2)

    def test_local_minimum_filter_removes_continuous_flat_ground(self):
        flat = tuple(
            (0.05 + 0.30 * x, 0.05 + 0.30 * y, 0.0)
            for x in range(4)
            for y in range(4)
        )
        planner, stats = local_minimum_obstacle_hits(
            flat, (-1.0, 0.0, 1.0), 0.1, 5.0, 0.30, 0.22
        )
        self.assertEqual(planner, ())
        self.assertEqual(stats["filtered_ground_hit_count"], len(flat))
        self.assertEqual(
            stats["finite_in_range_hit_count"],
            stats["filtered_ground_hit_count"] + stats["obstacle_hit_count"],
        )

    def test_local_minimum_filter_keeps_step_riser_as_geometry(self):
        ground = [
            (0.05 + 0.30 * x, 0.05 + 0.30 * y, 0.0)
            for x in range(4)
            for y in range(3)
        ]
        step_riser = (0.65, 0.35, 0.30)
        planner, stats = local_minimum_obstacle_hits(
            tuple(ground) + (step_riser,),
            (-1.0, 0.0, 1.0),
            0.1,
            5.0,
            0.30,
            0.22,
        )
        self.assertIn(step_riser, planner)
        self.assertGreater(stats["filtered_ground_hit_count"], 0)

    def test_dual_cloud_split_keeps_flat_ground_raw_and_obstacle_planning(self):
        flat = tuple(
            (0.05 + 0.30 * x, 0.05 + 0.30 * y, 0.0)
            for x in range(4)
            for y in range(4)
        )
        obstacle = (0.65, 0.35, 0.50)
        raw, planner, stats = split_geometry_cloud_points(
            flat + (obstacle,),
            (-1.0, 0.0, 1.0),
            (1.0, 0.0, 0.0, 0.0),
            0.1,
            5.0,
            0.30,
            0.22,
        )
        self.assertEqual(len(raw), len(flat) + 1)
        self.assertEqual(len(planner), 1)
        self.assertEqual(stats["filtered_ground_hit_count"], len(flat))
        self.assertEqual(stats["obstacle_hit_count"], 1)

    def test_local_minimum_filter_retains_sparse_hit_conservatively(self):
        obstacles, stats = local_minimum_obstacle_hits(
            ((1.0, 1.0, 0.7), (float("nan"), 0.0, 0.0), (20.0, 0.0, 0.0)),
            (0.0, 0.0, 1.0),
            0.1,
            5.0,
            cell_size=0.30,
            height_threshold=0.22,
        )
        self.assertEqual(obstacles, ((1.0, 1.0, 0.7),))
        self.assertEqual(stats["sparse_retained_hit_count"], 1)
        self.assertEqual(stats["finite_in_range_hit_count"], 1)

    def test_local_minimum_filter_rejects_invalid_parameters(self):
        with self.assertRaisesRegex(ValueError, "cell size"):
            local_minimum_obstacle_hits(
                (), (0.0, 0.0, 1.0), 0.1, 5.0, 0.0, 0.22
            )
        with self.assertRaisesRegex(ValueError, "height threshold"):
            local_minimum_obstacle_hits(
                (), (0.0, 0.0, 1.0), 0.1, 5.0, 0.30, float("nan")
            )

    def test_point_to_segment_distance_clamps_projection(self):
        self.assertAlmostEqual(
            point_to_segment_distance_2d((0.0, 1.0), (-1.0, 0.0), (1.0, 0.0)),
            1.0,
        )
        self.assertAlmostEqual(
            point_to_segment_distance_2d((3.0, 0.0), (-1.0, 0.0), (1.0, 0.0)),
            2.0,
        )
        self.assertAlmostEqual(
            point_to_segment_distance_2d((1.0, 1.0), (0.0, 0.0), (0.0, 0.0)),
            math.sqrt(2.0),
        )

    def test_terrain_seating_uses_highest_sample_and_local_minimum(self):
        result = terrain_seating_for_bounds(
            origin_xy=(2.0, 3.0),
            local_bounds_min=(-1.0, -0.5, -0.40),
            local_bounds_max=(1.0, 0.5, 0.60),
            terrain_height=lambda x, y: 0.20 + 0.10 * x + 0.05 * y,
            samples_per_axis=3,
            clearance_m=0.02,
        )
        self.assertEqual(result["sample_count"], 9)
        self.assertAlmostEqual(result["maximum_terrain_height_m"], 0.675)
        self.assertAlmostEqual(result["required_origin_z_m"], 1.095)
        self.assertAlmostEqual(result["seated_bounds_min_z_m"], 0.695)

    def test_terrain_seating_rejects_invalid_bounds_or_height(self):
        with self.assertRaisesRegex(ValueError, "bounds"):
            terrain_seating_for_bounds(
                (0.0, 0.0),
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 1.0),
                lambda _x, _y: 0.0,
            )
        with self.assertRaisesRegex(ValueError, "terrain height"):
            terrain_seating_for_bounds(
                (0.0, 0.0),
                (-1.0, -1.0, -1.0),
                (1.0, 1.0, 1.0),
                lambda _x, _y: float("nan"),
            )

    def test_mesh_support_seating_uses_real_low_surface_points(self):
        result = terrain_seating_for_mesh_support(
            origin_xy=(2.0, 3.0),
            local_support_points=(
                (-0.2, -0.1, -0.40),
                (0.3, 0.2, -0.39),
            ),
            terrain_height=lambda x, y: 0.10 * x + 0.05 * y,
            clearance_m=0.02,
        )
        self.assertEqual(result["method"], "lowest_mesh_vertex_band")
        self.assertEqual(result["sample_count"], 2)
        self.assertAlmostEqual(result["required_origin_z_m"], 0.80)
        self.assertAlmostEqual(result["minimum_support_clearance_m"], 0.02)
        self.assertAlmostEqual(
            result["contact_support_point_world_xyz_m"][2],
            result["contact_terrain_height_m"] + 0.02,
        )

    def test_mesh_support_seating_rejects_missing_or_nonfinite_points(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            terrain_seating_for_mesh_support(
                (0.0, 0.0), (), lambda _x, _y: 0.0
            )
        with self.assertRaisesRegex(ValueError, "finite"):
            terrain_seating_for_mesh_support(
                (0.0, 0.0), ((0.0, 0.0, float("nan")),), lambda _x, _y: 0.0
            )

    def test_command_visibility(self):
        observation = [0.0] * 20
        observation[9:12] = [0.3, -0.1, 0.2]
        self.assertEqual(
            assert_command_visible_in_critic(observation, (0.3, -0.1, 0.2)),
            (0.3, -0.1, 0.2),
        )
        with self.assertRaisesRegex(ValueError, "not visible"):
            assert_command_visible_in_critic(observation, (0.2, -0.1, 0.2))


if __name__ == "__main__":
    unittest.main()

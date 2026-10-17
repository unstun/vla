import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from lite3_sim_bridge.acceptance import _percentile, evaluate_acceptance


class AcceptanceTest(unittest.TestCase):
    def _thresholds(self):
        return {
            "claim": "test gate",
            "goal_world_m": [4.0, 0.0, 0.35],
            "obstacle": {"detour_x_window_m": [1.4, 2.6]},
            "thresholds": {
                "minimum_record_count": 600,
                "minimum_sim_duration_seconds": 12.0,
                "goal_xy_tolerance_m": 0.12,
                "goal_z_tolerance_m": 0.08,
                "stop_window_seconds": 2.0,
                "stop_command_max_abs": 0.05,
                "stop_planar_speed_max_mps": 0.12,
                "minimum_nonzero_command_records": 250,
                "command_component_max_abs": [0.75, 0.35, 1.0],
                "command_bound_epsilon": 0.005,
                "root_height_range_m": [0.25, 0.42],
                "maximum_step_displacement_m": 0.05,
                "minimum_supported_contact_fraction": 0.97,
                "maximum_nonfoot_contact_n": 75.0,
                "minimum_detour_abs_y_m": 0.80,
                "policy_rate_hz_range": [45.0, 55.0],
                "sensor_rate_hz_range": [8.0, 12.0],
                "minimum_cloud_nonempty_fraction": 0.99,
                "minimum_cloud_points": 10,
                "minimum_obstacle_surface_hits": 20,
                "maximum_unexpected_above_floor_hits": 0,
                "minimum_sensor_pose_displacement_m": 3.5,
                "maximum_sequence_gaps": 0,
                "maximum_watchdog_events": 0,
                "maximum_command_age_p95_ms": 100.0,
                "minimum_unique_trajectories": 2,
                "minimum_synchronized_sensor_fraction": 0.95,
                "maximum_transport_protocol_errors": 0,
                "maximum_coalesced_command_frames": 100,
                "maximum_telemetry_reconnects": 1,
                "minimum_video_frames": 250,
                "minimum_video_duration_seconds": 10.0,
                "minimum_video_bytes": 100000,
                "minimum_rosbag_bytes": 10000,
                "minimum_planner_successes": 2,
                "maximum_planner_failures": 0,
                "maximum_origin_occupancy_errors": 0,
            },
        }

    def _metrics(self):
        rows = []
        count = 620
        for index in range(count):
            fraction = index / (count - 1)
            x = 4.0 * fraction
            y = -0.95 * math.sin(math.pi * fraction)
            stopped = index >= count - 110
            rows.append(
                {
                    "sim_time_seconds": 0.02 * index,
                    "root_pos_w": [x, y, 0.31],
                    "root_lin_vel_w": [0.0 if stopped else 0.3, 0.0, 0.0],
                    "terrain_height_under_root_m": 0.05 * fraction,
                    "base_clearance_m": 0.31 - 0.05 * fraction,
                    "applied_command": [0.0, 0.0, 0.0]
                    if stopped
                    else [0.3, 0.0, 0.2],
                    "contact_count": 2,
                    "nonfoot_contact_max_n": 0.0,
                    "finite": True,
                    "done": False,
                    "sequence_gaps": 0,
                    "watchdog_events": 0,
                    "command_age_ms": 10.0,
                }
            )
        return rows

    def _sensor_metrics(self):
        return [
            {
                "sim_time_seconds": 0.1 * index,
                "sensor_position_w": [4.0 * index / 124, 0.0, 0.42],
                "point_count": 30,
                "obstacle_surface_hit_count": 30,
                "unexpected_above_floor_hit_count": 0,
                "planner_geometry_filter_enabled": True,
                "planner_geometry_filter_ground_hit_count": 100,
                "planner_geometry_filter_obstacle_hit_count": 30,
                "planner_geometry_filter_sparse_retained_hit_count": 3,
            }
            for index in range(125)
        ]

    def _ros_summary(self):
        topic = {
            "count": 125,
            "duration_seconds": 12.4,
            "rate_hz": 10.0,
            "nonincreasing_stamp_count": 0,
        }
        return {
            "topics": {
                "body_pose": dict(topic),
                "sensor_pose": dict(topic),
                "cloud": dict(topic),
                "cmd_vel": {"count": 620, "rate_hz": 50.0},
                "bspline": {"count": 3, "rate_hz": 0.3},
            },
            "unique_trajectory_count": 3,
            "synchronized_sensor_triplet_fraction": 1.0,
            "cloud_points": {"minimum": 30, "maximum": 30, "mean": 30.0},
        }

    def _v3_thresholds(self):
        thresholds = self._thresholds()
        thresholds["v3_sensor_rig"] = {
            "canonical_urdf_sha256": "canonical",
            "isaac_urdf_sha256": "isaac",
            "lidar_frame": "mid360_scan_frame",
            "depth_frame": "d435i_depth_optical_frame",
            "expected_body_count": 24,
            "expected_joint_count": 23,
            "expected_fixed_joint_count": 11,
            "expected_movable_joint_count": 12,
            "expected_collision_count": 29,
            "runtime_mass_range_kg": [13.2817, 13.2819],
            "minimum_depth_frames": 120,
            "depth_rate_hz_range": [8.0, 12.0],
            "minimum_depth_nonempty_fraction": 0.99,
            "minimum_depth_obstacle_pixels": 20,
            "minimum_depth_pose_displacement_m": 3.5,
            "depth_dimensions": [87, 58],
            "minimum_self_occluded_lidar_hits": 1,
            "minimum_depth_artifact_count": 3,
        }
        return thresholds

    def _depth_metrics(self):
        return [
            {
                "sim_time_seconds": 0.1 * index,
                "sensor_position_w": [4.0 * index / 124, 0.0, 0.4],
                "valid_depth_pixel_count": 100,
                "nonfinite_depth_count": 0,
                "obstacle_surface_pixel_count": 30,
                "width": 87,
                "height": 58,
            }
            for index in range(125)
        ]

    def test_percentile_interpolates(self):
        self.assertAlmostEqual(_percentile([0.0, 10.0, 20.0], 0.75), 15.0)
        with self.assertRaises(ValueError):
            _percentile([], 0.5)

    def test_accepts_complete_run_and_rejects_collision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "run.mp4"
            video.write_bytes(b"v" * 120000)
            video_sha = hashlib.sha256(video.read_bytes()).hexdigest()
            bag = root / "rosbag"
            bag.mkdir()
            (bag / "metadata.yaml").write_text("rosbag2_bagfile_information: {}\n")
            (bag / "run_0.db3").write_bytes(b"b" * 12000)
            metrics = self._metrics()
            report = evaluate_acceptance(
                self._thresholds(),
                metrics,
                self._sensor_metrics(),
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                {"acceptance_config_sha256": "frozen"},
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
            )
            self.assertEqual(
                report["status"],
                "PASS",
                msg={
                    name: check
                    for name, check in report["checks"].items()
                    if not check["passed"]
                },
            )

            metrics[300]["nonfoot_contact_max_n"] = 100.0
            failed = evaluate_acceptance(
                self._thresholds(),
                metrics,
                self._sensor_metrics(),
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                {"acceptance_config_sha256": "frozen"},
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
            )
            self.assertEqual(failed["status"], "FAIL")
            self.assertFalse(failed["checks"]["no_collision"]["passed"])

    def test_v3_requires_asset_depth_and_runtime_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "run.mp4"
            video.write_bytes(b"v" * 120000)
            video_sha = hashlib.sha256(video.read_bytes()).hexdigest()
            bag = root / "rosbag"
            bag.mkdir()
            (bag / "metadata.yaml").write_text("rosbag2_bagfile_information: {}\n")
            (bag / "run_0.db3").write_bytes(b"b" * 12000)
            artifacts = {}
            for name in ("depth.npy", "depth_mm.png", "depth_preview.png"):
                path = root / name
                path.write_bytes(name.encode("ascii"))
                artifacts[name] = {
                    "path": name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            sensor_metrics = self._sensor_metrics()
            for row in sensor_metrics:
                row["self_occluded_hit_count"] = 12
            identity = {
                "acceptance_config_sha256": "frozen",
                "robot_asset": {
                    "canonical_asset_sha256": "canonical",
                    "asset_sha256": "isaac",
                },
                "sensor": {"parent_frame": "mid360_scan_frame"},
                "depth_camera": {"parent_frame": "d435i_depth_optical_frame"},
            }
            composition = {
                "runtime_body_names": [str(index) for index in range(24)],
                "imported_joint_prim_paths": [str(index) for index in range(23)],
                "imported_fixed_joint_prim_paths": [str(index) for index in range(11)],
                "imported_movable_joint_prim_paths": [str(index) for index in range(12)],
                "imported_collision_prim_paths": [str(index) for index in range(29)],
                "runtime_total_mass_kg": 13.281788,
                "silent_default_mass_check": {"status": "pass"},
            }
            report = evaluate_acceptance(
                self._v3_thresholds(),
                self._metrics(),
                sensor_metrics,
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                    "depth_artifact": {"artifacts": artifacts},
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
                self._depth_metrics(),
                composition,
                root,
            )
            self.assertEqual(report["status"], "PASS")
            identity["robot_asset"]["asset_sha256"] = "wrong"
            failed = evaluate_acceptance(
                self._v3_thresholds(),
                self._metrics(),
                sensor_metrics,
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                    "depth_artifact": {"artifacts": artifacts},
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
                self._depth_metrics(),
                composition,
                root,
            )
            self.assertEqual(failed["status"], "FAIL")
            self.assertFalse(failed["checks"]["v3_isaac_urdf_hash"]["passed"])

    def test_forest_navigation_requires_speed_geometry_filter_and_real_detour(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "run.mp4"
            video.write_bytes(b"v" * 120000)
            video_sha = hashlib.sha256(video.read_bytes()).hexdigest()
            bag = root / "rosbag"
            bag.mkdir()
            (bag / "metadata.yaml").write_text(
                "rosbag2_bagfile_information: {}\n"
            )
            (bag / "run_0.db3").write_bytes(b"b" * 12000)
            thresholds = self._thresholds()
            thresholds["forest_navigation"] = {
                "goal_world_m": [4.0, 0.0, 0.35],
                "obstacle_x_window_m": [1.0, 3.0],
                "minimum_filter_enabled_fraction": 1.0,
                "minimum_filtered_ground_hits_per_frame": 50,
                "minimum_filtered_obstacle_hits_per_frame": 20,
                "maximum_sparse_retained_fraction": 0.20,
                "minimum_forward_command_mps": 0.25,
                "minimum_measured_speed_p75_mps": 0.25,
                "minimum_primary_center_clearance_m": 0.60,
                "minimum_line_deviation_m": 0.80,
                "minimum_path_length_excess_m": 0.20,
                "minimum_base_clearance_m": 0.20,
                "minimum_terrain_height_range_m": 0.04,
            }
            identity = {
                "acceptance_config_sha256": "frozen",
                "forest_scene": {
                    "navigation": {
                        "start_world_m": [0.0, 0.0, 0.31],
                        "goal_world_m": [4.0, 0.0, 0.35],
                        "primary_blocker": {"center_m": [2.0, 0.0, 0.4]},
                        "required_center_clearance_m": 0.64,
                        "direct_path_intersects_inflated_blocker": True,
                    }
                },
                "sensor": {
                    "forest_geometry_filter": {
                        "enabled": True,
                        "forbidden_inputs": [
                            "terrain_height_function",
                            "scene_prim_id",
                            "proxy_bounds",
                            "obstacle_label",
                        ],
                    }
                },
            }
            report = evaluate_acceptance(
                thresholds,
                self._metrics(),
                self._sensor_metrics(),
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
            )
            self.assertEqual(report["status"], "PASS")
            self.assertTrue(report["checks"]["forest_planner_detour"]["passed"])

            straight_metrics = self._metrics()
            for row in straight_metrics:
                row["root_pos_w"][1] = 0.0
            failed = evaluate_acceptance(
                thresholds,
                straight_metrics,
                self._sensor_metrics(),
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
            )
            self.assertEqual(failed["status"], "FAIL")
            self.assertFalse(
                failed["checks"]["forest_primary_blocker_clearance"]["passed"]
            )
            self.assertFalse(failed["checks"]["forest_planner_detour"]["passed"])

    def test_v6_requires_four_layer_speed_geometry_and_trace_overlay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "run.mp4"
            overlay = root / "overlay.mp4"
            video.write_bytes(b"v" * 120000)
            overlay.write_bytes(b"o" * 130000)
            video_sha = hashlib.sha256(video.read_bytes()).hexdigest()
            overlay_sha = hashlib.sha256(overlay.read_bytes()).hexdigest()
            bag = root / "rosbag"
            bag.mkdir()
            (bag / "metadata.yaml").write_text(
                "rosbag2_bagfile_information: {}\n"
            )
            (bag / "run_0.db3").write_bytes(b"b" * 12000)

            thresholds = self._thresholds()
            thresholds["thresholds"]["command_component_max_abs"] = [
                1.0,
                0.35,
                1.0,
            ]
            thresholds["v6_review"] = {
                "expected_course": "forest_gen_nav_v6",
                "expected_forward_limit_mps": 1.0,
                "planner_acceleration_limit_mps2": 0.5,
                "high_command_minimum_vx_mps": 0.90,
                "high_command_maximum_abs_yaw_rps": 0.15,
                "minimum_high_command_sample_count": 20,
                "minimum_high_command_measured_speed_p75_mps": 0.70,
                "minimum_rock_terrain_clearance_m": 0.01,
                "maximum_proxy_bounds_error_m": 0.005,
                "expected_proxy_render_visible": False,
                "minimum_complete_bspline_records": 2,
                "minimum_overlay_video_bytes": 100000,
                "minimum_overlay_video_frames": 250,
                "maximum_plan_pose_alignment_error_ms": 150.0,
            }
            metrics = self._metrics()
            for row in metrics[:-110]:
                row["applied_command"] = [0.95, 0.0, 0.05]
                row["root_lin_vel_w"] = [0.80, 0.0, 0.0]
            identity = {
                "acceptance_config_sha256": "frozen",
                "course": {"name": "forest_gen_nav_v6"},
                "command_limits": [1.0, 0.35, 1.0],
            }
            geometry = {
                "passed": True,
                "proxy_records": [
                    {
                        "name": "rock_proxy",
                        "kind": "Rock",
                        "source_visual_terrain_clearance_m": 0.015,
                        "proxy_bounds_max_error_m": 0.0,
                        "expected_render_visible": False,
                        "visible_geometry_prim_paths": [],
                        "render_visibility_matches": True,
                    }
                ],
            }
            trajectory_events = [
                {
                    "kind": "bspline",
                    "trajectory_id": identifier,
                    "start_time_ns": identifier,
                    "order": 1,
                    "knots": [0.0, 0.0, 1.0, 1.0],
                    "control_points": [[0.0, 0.0, 0.3], [1.0, 0.2, 0.3]],
                }
                for identifier in (1, 2)
            ]
            input_hashes = {
                "raw_video": "raw",
                "ros_events": "events",
                "metrics": "metrics",
                "run_identity": "identity",
            }
            review_metadata = {
                "input_sha256": dict(input_hashes),
                "output": {
                    "sha256": overlay_sha,
                    "bytes": overlay.stat().st_size,
                    "frame_count": 310,
                },
                "mapping": {"maximum_plan_pose_alignment_error_ms": 20.0},
            }
            report = evaluate_acceptance(
                thresholds,
                metrics,
                self._sensor_metrics(),
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
                runtime_composition={
                    "forest_scene": {"static_geometry_checks": geometry}
                },
                overlay_video_path=overlay,
                trajectory_events=trajectory_events,
                trajectory_review_metadata=review_metadata,
                trajectory_review_input_sha256=input_hashes,
                effective_input_text="max_vx=1.0\n",
                planner_config_text=(
                    "    manager.max_vel: 1.00\n"
                    "    manager.max_acc: 0.5\n"
                    "    optimization.max_vel: 1.00\n"
                ),
                controller_config_text="    max_vx: 1.00\n",
            )
            self.assertEqual(report["status"], "PASS")
            self.assertTrue(
                report["checks"]["v6_synchronized_forward_limits"]["passed"]
            )
            self.assertTrue(report["checks"]["v6_overlay_input_hashes"]["passed"])

            geometry["proxy_records"][0]["visible_geometry_prim_paths"] = [
                "/World/visible_proxy"
            ]
            failed = evaluate_acceptance(
                thresholds,
                metrics,
                self._sensor_metrics(),
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
                runtime_composition={
                    "forest_scene": {"static_geometry_checks": geometry}
                },
                overlay_video_path=overlay,
                trajectory_events=trajectory_events,
                trajectory_review_metadata=review_metadata,
                trajectory_review_input_sha256=input_hashes,
                effective_input_text="max_vx=1.0\n",
                planner_config_text=(
                    "    manager.max_vel: 1.00\n"
                    "    manager.max_acc: 0.5\n"
                    "    optimization.max_vel: 1.00\n"
                ),
                controller_config_text="    max_vx: 1.00\n",
            )
            self.assertEqual(failed["status"], "FAIL")
            self.assertFalse(
                failed["checks"]["v6_proxy_review_visibility"]["passed"]
            )

    def test_v7_requires_moving_dual_sensor_obstacle_and_post_detection_plan(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "run.mp4"
            video.write_bytes(b"v" * 120000)
            video_sha = hashlib.sha256(video.read_bytes()).hexdigest()
            bag = root / "rosbag"
            bag.mkdir()
            (bag / "metadata.yaml").write_text(
                "rosbag2_bagfile_information: {}\n"
            )
            (bag / "run_0.db3").write_bytes(b"b" * 12000)

            thresholds = self._thresholds()
            thresholds["v7_dynamic_obstacle"] = {
                "expected_course": "forest_gen_nav_v7_dynamic",
                "expected_shape": "cylinder",
                "expected_radius_m": 0.30,
                "expected_height_m": 1.50,
                "expected_speed_mps": 1.0,
                "expected_wait_seconds": 2.0,
                "expected_hold_fraction": 0.5,
                "expected_hold_seconds": 0.0,
                "expected_schedule_trigger": "first nonzero accepted body command",
                "expected_occupied_decay_updates": 8,
                "expected_controller_strict_tracking_error_m": 0.10,
                "expected_controller_catchup_max_error_m": 0.40,
                "expected_controller_catchup_minimum_speed_mps": 0.20,
                "expected_controller_finish_distance_m": 0.10,
                "maximum_post_stop_drift_m": 0.35,
                "minimum_actual_travel_m": 1.9,
                "maximum_pose_error_m": 0.02,
                "minimum_terrain_clearance_m": 0.01,
                "minimum_lidar_hits_per_detection": 3,
                "minimum_depth_pixels_per_detection": 3,
                "minimum_lidar_detection_frames": 5,
                "minimum_depth_detection_frames": 5,
                "minimum_observed_position_span_m": 0.5,
                "maximum_nominal_route_distance_m": 0.10,
                "minimum_post_detection_bspline_records": 1,
                "maximum_replan_response_seconds": 0.5,
                "minimum_synchronized_surface_clearance_m": 0.10,
                "minimum_overlay_dynamic_records": 300,
            }
            metrics = self._metrics()
            settle_start = len(metrics) - 122
            ramp_start = metrics[settle_start - 1]["root_pos_w"][:2]
            for offset, row in enumerate(metrics[settle_start : settle_start + 20]):
                fraction = (offset + 1) / 20.0
                row["root_pos_w"] = [
                    ramp_start[0] + (4.0 - ramp_start[0]) * fraction,
                    ramp_start[1] * (1.0 - fraction),
                    0.31,
                ]
            for row in metrics[settle_start + 20 :]:
                row["root_pos_w"] = [4.0, 0.0, 0.31]
                row["root_lin_vel_w"] = [0.0, 0.0, 0.0]
                row["applied_command"] = [0.0, 0.0, 0.0]
            for row in metrics:
                elapsed = float(row["sim_time_seconds"])
                triggered = elapsed >= 0.2
                if not triggered:
                    row["applied_command"] = [0.0, 0.0, 0.0]
                if elapsed <= 2.0:
                    phase = "waiting"
                    y = -1.0
                elif elapsed < 4.0:
                    phase = "crossing"
                    y = -1.0 + (elapsed - 2.0)
                else:
                    phase = "parked"
                    y = 1.0
                actual = [2.0, y, 1.0]
                row.update(
                    {
                        "dynamic_obstacle_phase": phase,
                        "dynamic_obstacle_elapsed_seconds": (
                            elapsed - 0.2 if triggered else 0.0
                        ),
                        "dynamic_obstacle_schedule_triggered": triggered,
                        "dynamic_obstacle_trigger_sim_time_seconds": (
                            0.2 if triggered else None
                        ),
                        "dynamic_obstacle_actual_pos_w": actual,
                        "dynamic_obstacle_pose_error_m": 0.005,
                        "dynamic_obstacle_bottom_clearance_m": 0.02,
                        "root_to_dynamic_surface_clearance_m": 0.20,
                    }
                )
            sensor_metrics = self._sensor_metrics()
            depth_metrics = self._depth_metrics()
            for rows, hit_key in (
                (sensor_metrics, "dynamic_obstacle_surface_hit_count"),
                (depth_metrics, "dynamic_obstacle_surface_pixel_count"),
            ):
                for index, row in enumerate(rows):
                    elapsed = float(row["sim_time_seconds"])
                    y = max(-1.0, min(1.0, elapsed - 3.0))
                    row["dynamic_obstacle_actual_pos_w"] = [2.0, y, 1.0]
                    row[hit_key] = 8 if 20 <= index <= 40 else 0
            identity = {
                "acceptance_config_sha256": "frozen",
                "course": {"name": "forest_gen_nav_v7_dynamic"},
                "dynamic_obstacle": {
                    "shape": "cylinder",
                    "radius_m": 0.30,
                    "height_m": 1.50,
                    "speed_mps": 1.0,
                    "wait_seconds": 2.0,
                    "hold_fraction": 0.5,
                    "hold_seconds": 0.0,
                    "schedule_trigger": "first nonzero accepted body command",
                    "start_xy_m": [2.0, -1.0],
                    "end_xy_m": [2.0, 1.0],
                    "planner_input": "rendered sensor hits only",
                    "ground_truth_use": "forbidden from planner and robot steering",
                },
                "forest_scene": {
                    "navigation": {
                        "start_world_m": [0.0, 0.0, 0.35],
                        "goal_world_m": [4.0, 0.0, 0.35],
                    }
                },
            }
            geometry_checks = {
                name: True
                for name in (
                    "runtime_root_exists",
                    "rigid_object_initialized",
                    "kinematic_enabled",
                    "collision_enabled",
                    "visible_geometry",
                    "lidar_transform_tracking",
                    "depth_transform_tracking",
                )
            }
            review_metadata = {
                "plans": [
                    {"trajectory_id": 2, "effective_sim_time_seconds": 2.2},
                    {"trajectory_id": 3, "effective_sim_time_seconds": 3.0},
                ],
                "dynamic_obstacle": {"rendered": True, "record_count": 310},
            }
            report = evaluate_acceptance(
                thresholds,
                metrics,
                sensor_metrics,
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
                depth_metrics=depth_metrics,
                runtime_composition={
                    "dynamic_obstacle": {
                        "geometry_checks": {
                            "passed": True,
                            "checks": geometry_checks,
                        }
                    }
                },
                trajectory_review_metadata=review_metadata,
                planner_config_text="    grid_map.occupied_decay_updates: 8\n",
                controller_config_text=(
                    "    max_tracking_error: 0.10\n"
                    "    replan_catchup_max_error: 0.40\n"
                    "    replan_catchup_min_speed: 0.20\n"
                    "    finish_dist: 0.10\n"
                ),
            )
            self.assertEqual(
                report["status"],
                "PASS",
                msg={
                    name: check
                    for name, check in report["checks"].items()
                    if not check["passed"]
                },
            )
            self.assertTrue(
                report["checks"]["v7_post_detection_scan_response"]["passed"]
            )
            self.assertTrue(
                report["checks"]["v7_physical_dynamic_clearance"]["passed"]
            )

            review_metadata["plans"] = [
                {"trajectory_id": 1, "effective_sim_time_seconds": 1.0}
            ]
            failed = evaluate_acceptance(
                thresholds,
                metrics,
                sensor_metrics,
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
                depth_metrics=depth_metrics,
                runtime_composition={
                    "dynamic_obstacle": {
                        "geometry_checks": {
                            "passed": True,
                            "checks": geometry_checks,
                        }
                    }
                },
                trajectory_review_metadata=review_metadata,
                planner_config_text="    grid_map.occupied_decay_updates: 8\n",
                controller_config_text=(
                    "    max_tracking_error: 0.10\n"
                    "    replan_catchup_max_error: 0.40\n"
                    "    replan_catchup_min_speed: 0.20\n"
                    "    finish_dist: 0.10\n"
                ),
            )
            self.assertEqual(failed["status"], "FAIL")
            self.assertFalse(
                failed["checks"]["v7_post_detection_scan_response"]["passed"]
            )

            human_asset = root / "procedural_human.usda"
            human_asset.write_text("#usda 1.0\n", encoding="utf-8")
            human_sha = hashlib.sha256(human_asset.read_bytes()).hexdigest()
            part_names = sorted(
                [
                    "Head",
                    "Torso",
                    "Pelvis",
                    "LeftArm",
                    "RightArm",
                    "LeftLeg",
                    "RightLeg",
                ]
            )
            thresholds["v7_dynamic_obstacle"]["expected_course"] = (
                "forest_gen_nav_v8_human"
            )
            thresholds["v7_dynamic_obstacle"]["expected_shape"] = (
                "procedural_humanoid"
            )
            thresholds["v8_human_obstacle"] = {
                "expected_asset_filename": "procedural_human.usda",
                "expected_asset_sha256": human_sha,
                "expected_part_names": part_names,
                "expected_colour_rgb": [1.0, 0.82, 0.02],
                "expected_overlay_colour_bgr": [0, 215, 255],
                "minimum_crossing_gait_records": 5,
                "minimum_observed_swing_radians": 0.25,
                "expected_maximum_swing_radians": 0.4,
                "maximum_opposition_error_radians": 1.0e-9,
                "maximum_neutral_swing_radians": 1.0e-9,
                "minimum_sensor_visible_swing_radians": 0.25,
                "minimum_lidar_animated_detections": 1,
                "minimum_depth_animated_detections": 1,
            }
            identity["course"]["name"] = "forest_gen_nav_v8_human"
            identity["dynamic_obstacle"].update(
                {
                    "shape": "procedural_humanoid",
                    "collision_shape": "hidden_capsule",
                    "colour_rgb": [1.0, 0.82, 0.02],
                    "visible_part_names": part_names,
                    "sensor_target_exprs": [f"target/{name}" for name in part_names],
                    "human_asset": {
                        "source": (
                            "locally generated procedural USDA; no external character asset"
                        ),
                        "sha256": human_sha,
                    },
                }
            )
            for row in metrics:
                swing = 0.3 if row["dynamic_obstacle_phase"] == "crossing" else 0.0
                row["dynamic_human_gait_angles"] = {
                    "left_arm_radians": -swing,
                    "right_arm_radians": swing,
                    "left_leg_radians": swing,
                    "right_leg_radians": -swing,
                }
            for rows in (sensor_metrics, depth_metrics):
                for row in rows:
                    row["dynamic_human_gait_angles"] = {
                        "left_arm_radians": -0.3,
                        "right_arm_radians": 0.3,
                        "left_leg_radians": 0.3,
                        "right_leg_radians": -0.3,
                    }
            geometry_checks.update(
                {
                    "human_parts_complete": True,
                    "human_collision_hidden": True,
                }
            )
            human_geometry = {
                "passed": True,
                "checks": geometry_checks,
                "visible_human_part_names": part_names,
                "collision_prim_paths": ["/Human/CollisionCapsule"],
                "visible_collision_prim_paths": [],
            }
            review_metadata["plans"] = [
                {"trajectory_id": 2, "effective_sim_time_seconds": 2.2},
                {"trajectory_id": 3, "effective_sim_time_seconds": 3.0},
            ]
            review_metadata["colours_bgr"] = {
                "dynamic_obstacle_actual": [0, 215, 255]
            }
            human_report = evaluate_acceptance(
                thresholds,
                metrics,
                sensor_metrics,
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
                depth_metrics=depth_metrics,
                runtime_composition={
                    "dynamic_obstacle": {"geometry_checks": human_geometry}
                },
                depth_artifact_root=root,
                trajectory_review_metadata=review_metadata,
                planner_config_text="    grid_map.occupied_decay_updates: 8\n",
                controller_config_text=(
                    "    max_tracking_error: 0.10\n"
                    "    replan_catchup_max_error: 0.40\n"
                    "    replan_catchup_min_speed: 0.20\n"
                    "    finish_dist: 0.10\n"
                ),
            )
            self.assertEqual(
                human_report["status"],
                "PASS",
                msg={
                    name: check
                    for name, check in human_report["checks"].items()
                    if not check["passed"]
                },
            )
            self.assertTrue(human_report["checks"]["v8_human_gait"]["passed"])
            self.assertTrue(
                human_report["checks"]["v8_sensor_visible_gait_and_overlay"][
                    "passed"
                ]
            )

            human_geometry["checks"]["lidar_transform_tracking"] = False
            missing_tracking_report = evaluate_acceptance(
                thresholds,
                metrics,
                sensor_metrics,
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {"protocol_errors": 0, "reconnects": 1},
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
                depth_metrics=depth_metrics,
                runtime_composition={
                    "dynamic_obstacle": {"geometry_checks": human_geometry}
                },
                depth_artifact_root=root,
                trajectory_review_metadata=review_metadata,
                planner_config_text="    grid_map.occupied_decay_updates: 8\n",
                controller_config_text=(
                    "    max_tracking_error: 0.10\n"
                    "    replan_catchup_max_error: 0.40\n"
                    "    replan_catchup_min_speed: 0.20\n"
                    "    finish_dist: 0.10\n"
                ),
            )
            self.assertFalse(
                missing_tracking_report["checks"]["v8_human_stage_geometry"][
                    "passed"
                ]
            )

            geometry_checks["lidar_transform_tracking"] = True
            geometry_checks["physical_geometry_visibility"] = True
            geometry_checks.update(
                {
                    "official_visual_root_exists": True,
                    "official_visual_geometry_visible": True,
                    "official_visual_has_no_collision": True,
                    "official_visual_has_no_rigid_body": True,
                    "official_sensor_proxy_is_capsule": True,
                }
            )
            visual_asset = root / "official_human_visual.usda"
            proxy_asset = root / "official_human_proxy.usda"
            visual_asset.write_text("#usda 1.0\n# official visual\n", encoding="utf-8")
            proxy_asset.write_text("#usda 1.0\n# hidden proxy\n", encoding="utf-8")
            visual_sha = hashlib.sha256(visual_asset.read_bytes()).hexdigest()
            proxy_sha = hashlib.sha256(proxy_asset.read_bytes()).hexdigest()
            character_url = (
                "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
                "Assets/Isaac/5.1/Isaac/People/Characters/"
                "male_adult_police_04/male_adult_police_04.usd"
            )
            biped_url = (
                "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
                "Assets/Isaac/5.1/Isaac/People/Characters/Biped_Setup.usd"
            )
            cache_sha = "7" * 64
            del thresholds["v8_human_obstacle"]
            thresholds["v7_dynamic_obstacle"]["expected_course"] = (
                "forest_gen_nav_v8_official_human"
            )
            thresholds["v7_dynamic_obstacle"]["expected_shape"] = (
                "official_skinned_human_plus_capsule"
            )
            thresholds["v8_official_human_obstacle"] = {
                "expected_character_url": character_url,
                "expected_biped_url": biped_url,
                "expected_visual_asset_filename": "official_human_visual.usda",
                "expected_proxy_asset_filename": "official_human_proxy.usda",
                "expected_visual_asset_sha256": visual_sha,
                "expected_proxy_asset_sha256": proxy_sha,
                "expected_cache_content_sha256": cache_sha,
                "expected_joint_count": 101,
                "expected_animation_fps": 30,
                "expected_idle_frame_count": 60,
                "expected_walk_frame_count": 90,
                "expected_visual_runtime_prim": "/World/DynamicHumanVisual",
                "expected_overlay_colour_bgr": [40, 40, 235],
                "minimum_crossing_animation_records": 5,
                "minimum_distinct_walk_frames": 5,
                "minimum_idle_animation_records": 5,
                "minimum_lidar_walk_detections": 1,
                "minimum_depth_walk_detections": 1,
                "maximum_visual_root_pose_error_m": 1.0e-6,
                "maximum_foot_datum_error_m": 1.0e-6,
            }
            identity["course"]["name"] = "forest_gen_nav_v8_official_human"
            identity["dynamic_obstacle"].update(
                {
                    "shape": "official_skinned_human_plus_capsule",
                    "collision_shape": "hidden_capsule",
                    "visible_part_names": ["/World/DynamicHumanVisual"],
                    "sensor_target_exprs": [
                        "{ENV_REGEX_NS}/DynamicObstacle/CollisionCapsule"
                    ],
                    "human_asset": {
                        "official_visual": {
                            "official_character_url": character_url,
                            "sha256": visual_sha,
                        },
                        "physical_and_sensor_proxy": {"sha256": proxy_sha},
                    },
                    "gait": {
                        "biped_url": biped_url,
                        "status": "official_biped_retarget_cache_replay",
                        "local_procedural_gait": False,
                        "direct_gpu_animation_graph_used": False,
                        "retarget_cache": {
                            "content_sha256": cache_sha,
                            "joint_count": 101,
                            "fps": 30,
                            "idle_frame_count": 60,
                            "walk_frame_count": 90,
                        },
                    },
                }
            )

            def official_gait(clip, frame_index):
                return {
                    "source": (
                        "NVIDIA Isaac Sim 5.1 Biped AnimationGraph retarget cache"
                    ),
                    "clip": clip,
                    "frame_index": frame_index,
                    "frame_count": 90 if clip == "walk" else 60,
                    "fps": 30,
                    "target_joint_count": 101,
                    "cache_content_sha256": cache_sha,
                    "local_procedural_gait": False,
                    "direct_gpu_animation_graph_used": False,
                }

            walk_index = 0
            for row in metrics:
                if row["dynamic_obstacle_phase"] == "crossing":
                    row["dynamic_human_gait_angles"] = official_gait(
                        "walk", walk_index % 90
                    )
                    walk_index += 1
                else:
                    row["dynamic_human_gait_angles"] = official_gait("idle", 0)
                row["official_human_visual_pose"] = {
                    "root_pose_error_m": 0.0,
                    "foot_to_capsule_bottom_error_m": 0.0,
                }
            for rows in (sensor_metrics, depth_metrics):
                for index, row in enumerate(rows):
                    row["dynamic_human_gait_angles"] = official_gait(
                        "walk", index % 90
                    )
            official_geometry = {
                "passed": True,
                "checks": geometry_checks,
                "collision_prim_paths": [
                    "/World/envs/env_0/DynamicObstacle/CollisionCapsule"
                ],
                "visible_collision_prim_paths": [],
                "visible_geometry_prim_paths": [],
                "official_visual_geometry_prim_paths": [
                    "/World/DynamicHumanVisual/OfficialCharacter/Body"
                ],
                "official_visual_collision_prim_paths": [],
                "official_visual_runtime_prim": "/World/DynamicHumanVisual",
            }
            review_metadata["dynamic_obstacle"]["label"] = (
                "Official human actual"
            )
            review_metadata["colours_bgr"] = {
                "dynamic_obstacle_actual": [40, 40, 235]
            }
            official_report = evaluate_acceptance(
                thresholds,
                metrics,
                sensor_metrics,
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {
                        "protocol_errors": 0,
                        "reconnects": 1,
                    },
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
                depth_metrics=depth_metrics,
                runtime_composition={
                    "dynamic_obstacle": {"geometry_checks": official_geometry}
                },
                depth_artifact_root=root,
                trajectory_review_metadata=review_metadata,
                planner_config_text="    grid_map.occupied_decay_updates: 8\n",
                controller_config_text=(
                    "    max_tracking_error: 0.10\n"
                    "    replan_catchup_max_error: 0.40\n"
                    "    replan_catchup_min_speed: 0.20\n"
                    "    finish_dist: 0.10\n"
                ),
            )
            self.assertEqual(
                official_report["status"],
                "PASS",
                msg={
                    name: check
                    for name, check in official_report["checks"].items()
                    if not check["passed"]
                },
            )
            self.assertTrue(
                official_report["checks"]["v8_official_animation"]["passed"]
            )

            identity["dynamic_obstacle"]["gait"]["retarget_cache"][
                "content_sha256"
            ] = "8" * 64
            cache_mismatch = evaluate_acceptance(
                thresholds,
                metrics,
                sensor_metrics,
                {
                    "status": "PASS",
                    "runtime_error": None,
                    "command_transport": {"protocol_errors": 0},
                    "telemetry_transport": {
                        "protocol_errors": 0,
                        "reconnects": 1,
                    },
                    "video": {
                        "frame_count": 310,
                        "encoded_duration_seconds": 12.4,
                        "sha256": video_sha,
                    },
                },
                identity,
                self._ros_summary(),
                video,
                bag,
                "final_plan_success=1\nfinal_plan_success=1\n"
                "[FSM]: from EXEC_TRAJ to WAIT_TARGET\n",
                "frozen",
                depth_metrics=depth_metrics,
                runtime_composition={
                    "dynamic_obstacle": {"geometry_checks": official_geometry}
                },
                depth_artifact_root=root,
                trajectory_review_metadata=review_metadata,
                planner_config_text="    grid_map.occupied_decay_updates: 8\n",
                controller_config_text=(
                    "    max_tracking_error: 0.10\n"
                    "    replan_catchup_max_error: 0.40\n"
                    "    replan_catchup_min_speed: 0.20\n"
                    "    finish_dist: 0.10\n"
                ),
            )
            self.assertFalse(
                cache_mismatch["checks"]["v8_official_identity"]["passed"]
            )


if __name__ == "__main__":
    unittest.main()

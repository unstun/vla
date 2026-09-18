from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from lite3_sim_bridge.run_isaac_v12_fallback import (
    FOREST_PREVIEW_SCHEDULE,
    OFFICE_STATIC_SCHEDULE,
    _candidate_name,
    _depth_gate,
    _forest_preview_report,
    _office_enabled,
    _rgb_scene_content,
    _sensor_gate,
    _urdf_contract,
)


class OfficeCourseContractTest(unittest.TestCase):
    def test_office_course_is_static_and_has_distinct_candidate_identity(self):
        args = SimpleNamespace(course="office_l0_static")
        self.assertTrue(_office_enabled(args))
        self.assertEqual(len(OFFICE_STATIC_SCHEDULE), 1)
        self.assertEqual(OFFICE_STATIC_SCHEDULE[0].command, (0.0, 0.0, 0.0))
        self.assertIn("Office L0 static support", _candidate_name(args))

    def test_camera_content_gate_rejects_wall_occlusion(self):
        import numpy as np

        wall = np.full((16, 16, 3), 18, dtype=np.uint8)
        scene = wall.copy()
        scene[:, 8:, :] = 180

        self.assertFalse(_rgb_scene_content(wall)["passed"])
        self.assertTrue(_rgb_scene_content(scene)["passed"])


class V12SensorGateTest(unittest.TestCase):
    def _records(self):
        return [
            {
                "sim_time_seconds": 0.1,
                "sensor_position_w": [0.0, 0.0, 0.4],
                "point_count": 20,
                "finite_point_count": 20,
                "ground_hit_count": 10,
                "obstacle_surface_hit_count": 3,
                "centroid_sensor": [1.0, 0.0, -0.2],
            },
            {
                "sim_time_seconds": 0.2,
                "sensor_position_w": [0.2, 0.0, 0.4],
                "point_count": 18,
                "finite_point_count": 18,
                "ground_hit_count": 8,
                "obstacle_surface_hit_count": 2,
                "centroid_sensor": [0.9, 0.1, -0.2],
            },
        ]

    def test_accepts_advancing_pose_dependent_obstacle_cloud(self):
        checks, passed = _sensor_gate(self._records())
        self.assertTrue(passed)
        self.assertTrue(checks["pose_dependent_geometry"])

    def test_rejects_static_or_nonfinite_cloud(self):
        records = self._records()
        records[1]["sensor_position_w"] = records[0]["sensor_position_w"]
        records[1]["centroid_sensor"] = records[0]["centroid_sensor"]
        records[1]["finite_point_count"] = 17
        checks, passed = _sensor_gate(records)
        self.assertFalse(passed)
        self.assertFalse(checks["finite"])
        self.assertFalse(checks["pose_dependent_geometry"])

    def test_rejects_ground_only_returns(self):
        records = self._records()
        for row in records:
            row["obstacle_surface_hit_count"] = 0
        checks, passed = _sensor_gate(records)
        self.assertFalse(passed)
        self.assertFalse(checks["obstacle_returns"])


class V3DepthGateTest(unittest.TestCase):
    def _records(self):
        intrinsic = [
            [50.0, 0.0, 43.0],
            [0.0, 50.0, 29.0],
            [0.0, 0.0, 1.0],
        ]
        return [
            {
                "sim_time_seconds": 0.1,
                "sensor_position_w": [0.2, 0.0, 0.45],
                "nonfinite_depth_count": 0,
                "valid_depth_pixel_count": 120,
                "obstacle_surface_pixel_count": 12,
                "intrinsic_matrix": intrinsic,
            },
            {
                "sim_time_seconds": 0.2,
                "sensor_position_w": [0.35, 0.0, 0.45],
                "nonfinite_depth_count": 0,
                "valid_depth_pixel_count": 118,
                "obstacle_surface_pixel_count": 9,
                "intrinsic_matrix": intrinsic,
            },
        ]

    def test_accepts_advancing_finite_depth_with_obstacle(self):
        checks, passed = _depth_gate(self._records())
        self.assertTrue(passed)
        self.assertTrue(checks["pose_dependent_frame"])

    def test_rejects_missing_obstacle_or_nonfinite_depth(self):
        records = self._records()
        records[0]["nonfinite_depth_count"] = 1
        records[0]["obstacle_surface_pixel_count"] = 0
        records[1]["obstacle_surface_pixel_count"] = 0
        checks, passed = _depth_gate(records)
        self.assertFalse(passed)
        self.assertFalse(checks["finite_depth"])
        self.assertFalse(checks["obstacle_returns"])

    def test_rejects_static_depth_frame(self):
        records = self._records()
        records[1]["sensor_position_w"] = records[0]["sensor_position_w"]
        checks, passed = _depth_gate(records)
        self.assertFalse(passed)
        self.assertFalse(checks["pose_dependent_frame"])


class SensorRigUrdfContractTest(unittest.TestCase):
    def test_extracts_topology_mass_collision_and_mesh_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mesh = root / "shape.stl"
            mesh.write_bytes(b"solid shape\nendsolid shape\n")
            urdf = root / "robot.urdf"
            urdf.write_text(
                """<robot name="fixture">
  <link name="base">
    <inertial><mass value="2.0"/><inertia ixx="1" ixy="0" ixz="0" iyy="1" iyz="0" izz="1"/></inertial>
    <visual><geometry><mesh filename="shape.stl"/></geometry></visual>
    <collision><geometry><box size="1 1 1"/></geometry></collision>
  </link>
  <link name="frame"/>
  <joint name="frame_joint" type="fixed"><parent link="base"/><child link="frame"/></joint>
</robot>\n""",
                encoding="utf-8",
            )
            contract = _urdf_contract(urdf)
        self.assertEqual(contract["link_count"], 2)
        self.assertEqual(contract["joint_count"], 1)
        self.assertEqual(contract["movable_joint_count"], 0)
        self.assertEqual(contract["fixed_joint_count"], 1)
        self.assertEqual(contract["collision_count"], 1)
        self.assertEqual(contract["total_declared_mass_kg"], 2.0)
        self.assertEqual(contract["links_without_inertial"], ["frame"])
        self.assertEqual(len(contract["referenced_meshes"]["shape.stl"]["sha256"]), 64)


class _Stats:
    def __init__(self):
        self.frames_received = 4


class ForestPreviewReportTest(unittest.TestCase):
    def _row(self, segment, root_x, forward=0.0, yaw=0.0):
        return {
            "done": False,
            "finite": True,
            "command_observation_max_error": 0.0,
            "contact_count": 4,
            "base_clearance_m": 0.30,
            "schedule_segment": segment,
            "schedule_segment_elapsed_seconds": 1.0,
            "root_lin_vel_b": [forward, 0.0, 0.0],
            "root_ang_vel_b": [0.0, 0.0, yaw],
            "applied_command": (
                [0.0, 0.0, 0.0]
                if segment in ("settle_zero", "stop_zero")
                else ([0.25, 0.0, 0.0] if segment == "forward" else [0.0, 0.0, 0.35])
            ),
            "root_pos_w": [root_x, 0.0, 0.30],
            "terrain_height_under_root_m": 0.01 * root_x,
        }

    def test_accepts_bounded_forest_motion_with_geometry_agreement(self):
        records = [
            self._row("settle_zero", 0.0),
            self._row("forward", 0.25, forward=0.20),
            self._row("yaw", 0.38, yaw=0.24),
            self._row("stop_zero", 0.40),
        ]
        report = _forest_preview_report(
            records,
            {"sensor_frames": 4, "nonempty_sensor_frames": 4, "status_frames": 4},
            _Stats(),
            _Stats(),
            {"passed": True},
        )
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["checks"]["locomotion_displacement"])
        self.assertEqual(
            [segment.name for segment in FOREST_PREVIEW_SCHEDULE],
            ["settle_zero", "forward", "yaw", "stop_zero"],
        )

    def test_rejects_unproven_proxy_geometry(self):
        records = [
            self._row("settle_zero", 0.0),
            self._row("forward", 0.25, forward=0.20),
            self._row("yaw", 0.38, yaw=0.24),
            self._row("stop_zero", 0.40),
        ]
        report = _forest_preview_report(
            records,
            {"sensor_frames": 4, "nonempty_sensor_frames": 4, "status_frames": 4},
            _Stats(),
            _Stats(),
            {"passed": False},
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["checks"]["static_geometry_agreement"])


if __name__ == "__main__":
    unittest.main()

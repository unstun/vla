import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import re


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = (
    REPOSITORY_ROOT
    / ".pipeline"
    / "experiments"
    / "2026-08-17_office_l0_scan_crowd"
)
LEDGER_PATH = EXPERIMENT_ROOT / "revision_ledger.json"
VALIDATOR_PATH = EXPERIMENT_ROOT / "validate_revision_ledger.py"

SPEC = importlib.util.spec_from_file_location(
    "office_revision_ledger_validator",
    VALIDATOR_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load revision-ledger validator: {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class OfficeRevisionLedgerTest(unittest.TestCase):
    def _write_payload(self, payload: dict, directory: str) -> Path:
        path = Path(directory) / "revision_ledger.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_current_ledger_and_evidence_hashes_pass(self) -> None:
        VALIDATOR.validate(LEDGER_PATH, REPOSITORY_ROOT)

    def test_full_run_authorization_cannot_be_inferred(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["revision_history"][-1].pop("full_duration_run_authorization")
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "full_duration_run_authorization"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_full_run_authorization_is_exactly_sixty_seconds(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["revision_history"][-1]["full_duration_run_authorization"][
            "duration_seconds"
        ] = 30
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "duration_seconds"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_pending_full_run_id_cannot_already_exist(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        authorization = payload["revision_history"][-1][
            "full_duration_run_authorization"
        ]
        run_id = "office_v2_0_1_go2_geometry_dryrun03"
        authorization["run_id"] = run_id
        authorization["status"] = "approved_pending_execution"
        payload["next_action"]["full_run_authorized"] = True
        payload["runs"].append(
            {
                "run_id": run_id,
                "revision": payload["current_working_revision"],
                "stage": "dryrun",
                "status": "failed",
                "immutable": True,
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "cannot already exist"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_consumed_full_run_authorization_requires_run_record(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        run_id = payload["revision_history"][-1]["full_duration_run_authorization"][
            "run_id"
        ]
        payload["runs"] = [run for run in payload["runs"] if run["run_id"] != run_id]
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "requires its run record"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_evidence_hash_drift_fails(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["runs"][1]["evidence"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "historical run records drifted"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_revision_history_cannot_drop_parent_revision(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["revision_history"] = payload["revision_history"][1:]
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "parent"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_revision_parent_chain_must_be_append_only(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["revision_history"][1]["parent_revision"] = None
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "parent"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_current_revision_must_match_history_tail(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["current_working_revision"] = "office-r2.0.1-preflight"
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "final revision_history entry"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_planned_revision_requires_fail_closed_gate_inventory(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["revision_history"][-1]["automated_gates"] = []
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "automated_gates"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_go2_borrowed_parameter_drift_fails(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["revision_history"][-1]["borrowed_parameters"]["values"][
            "grid_map.double_cylinder_radius"
        ] = 0.4
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "borrowed parameter inventory"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_frozen_lite3_speed_drift_fails(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["revision_history"][-1]["frozen_parameters"][
            "manager_max_vel_mps"
        ] = 0.75
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "manager_max_vel_mps"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_historical_run_record_drift_fails(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["runs"][0]["status"] = "rejected"
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "historical run records drifted"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_nonflat_run_authorization_cannot_be_inferred(self) -> None:
        payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload["next_action"]["nonflat_preflight_authorized"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_payload(payload, directory)
            with self.assertRaisesRegex(ValueError, "nonflat_preflight_authorized"):
                VALIDATOR.validate(path, REPOSITORY_ROOT)

    def test_upstream_go2_profile_borrows_only_declared_geometry_values(self) -> None:
        config = (
            REPOSITORY_ROOT
            / "integration/scan_planner_foxy_ws/src/plan_manage/config"
            / "foxy_isaac_office_crowd_upstream_go2_reference.yaml"
        ).read_text(encoding="utf-8")

        def scalar(name: str) -> float:
            match = re.search(rf"^\s*{re.escape(name)}:\s*([0-9.]+)\s*$", config, re.MULTILINE)
            self.assertIsNotNone(match, name)
            return float(match.group(1))

        expected_go2 = {
            "grid_map.double_cylinder_radius": 0.25,
            "grid_map.double_cylinder_offset": 0.18,
            "grid_map.body_height": 0.40,
            "grid_map.obstacles_inflation_z_up": 0.10,
            "grid_map.obstacles_inflation_z_down": 0.10,
        }
        for name, value in expected_go2.items():
            self.assertEqual(scalar(name), value)
        self.assertEqual(scalar("manager.max_vel"), 0.50)
        self.assertEqual(scalar("optimization.max_vel"), 0.50)
        self.assertEqual(scalar("grid_map.sliding_map_size_x"), 16.0)
        self.assertEqual(scalar("grid_map.sliding_map_size_y"), 16.0)
        self.assertEqual(scalar("grid_map.sliding_map_size_z"), 5.0)
        self.assertEqual(scalar("manager.planning_horizon"), 8.0)

    def test_rviz_live_cloud_uses_raw_topic_with_zero_decay(self) -> None:
        rviz = (
            REPOSITORY_ROOT
            / "integration/lite3_sim_bridge/config/foxy_native_scan_review.rviz"
        ).read_text(encoding="utf-8")
        name_offset = rviz.index("Name: Live LiDAR Cloud")
        live = rviz[name_offset - 500 : name_offset + 500]
        self.assertIn("Value: /quad_0/cloud_raw", live)
        self.assertIn("Decay Time: 0", live)

    def test_new_bridge_profile_requires_distinct_dual_cloud_topics(self) -> None:
        config = (
            REPOSITORY_ROOT
            / "integration/lite3_sim_bridge/config/foxy_bridge_upstream_go2_reference.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("raw_cloud_topic: /quad_0/cloud_raw", config)
        self.assertIn("cloud_topic: /quad_0/cloud", config)
        self.assertIn("require_dual_cloud_sensor_frame: true", config)
        self.assertIn("telemetry_receive_timeout_seconds: 10.0", config)
        self.assertIn("max_vx: 0.50", config)

    def test_foxy_bridge_publishes_both_clouds_from_one_decoded_frame(self) -> None:
        source = (
            REPOSITORY_ROOT
            / "integration/lite3_sim_bridge/lite3_sim_bridge/foxy_bridge_node.py"
        ).read_text(encoding="utf-8")
        self.assertIn("decode_dual_cloud_sensor_payload(frame.payload)", source)
        self.assertIn("self._scan_id_tracker.observe(decoded.scan_id)", source)
        raw_build = "stamp, sensor.raw_point_count, sensor.raw_points_xyz_f32_be"
        planner_build = (
            "stamp,\n                    sensor.planner_point_count,\n"
            "                    sensor.planner_points_xyz_f32_be,"
        )
        self.assertIn(raw_build, source)
        self.assertIn(planner_build, source)
        self.assertLess(
            source.index("self._raw_cloud_publisher.publish(raw_cloud)"),
            source.index("self._cloud_publisher.publish(planner_cloud)"),
        )
        self.assertIn('raise ProtocolError("dual-cloud sensor frame is required")', source)

    def test_scan_keeps_upstream_z_gradient_suppression_and_horizontal_control(self) -> None:
        optimizer = (
            REPOSITORY_ROOT
            / "integration/scan_planner_foxy_ws/src/bspline_opt/src/bspline_optimizer.cpp"
        ).read_text(encoding="utf-8")
        controller = (
            REPOSITORY_ROOT
            / "integration/scan_planner_foxy_ws/src/plan_manage/src/closed_loop_controller.cpp"
        ).read_text(encoding="utf-8")
        self.assertGreaterEqual(optimizer.count("grad_3D.row(2).setZero()"), 2)
        self.assertIn("command.linear.x", controller)
        self.assertIn("command.linear.y", controller)
        self.assertIn("command.angular.z", controller)
        self.assertNotIn("command.linear.z =", controller)


if __name__ == "__main__":
    unittest.main()

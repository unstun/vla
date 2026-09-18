from pathlib import Path
import unittest

from lite3_sim_bridge.delivery_reliability import (
    LIVE_CLOUD_TOPIC,
    build_live_pointcloud_continuity_audit,
    build_transfer_candidate_validation,
    expected_display_visibility,
    load_live_cloud_display_contract,
    select_smallest_passing_candidate,
    summarize_visibility,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RVIZ_CONFIG = (
    REPOSITORY_ROOT
    / "integration"
    / "lite3_sim_bridge"
    / "config"
    / "foxy_native_scan_review.rviz"
)


class DeliveryReliabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generated = [
            {
                "scan_reference_timestamp_ns": index * 100_000_000,
                "point_count": 15_000 + index,
            }
            for index in range(10)
        ]
        self.observations = [
            {
                "stamp_ns": index * 100_000_000,
                "wall_time_ns": 1_000_000_000 + index * 2_000_000_000,
                "point_count": 15_000 + index,
            }
            for index in range(10)
        ]
        self.native = {
            "source_mode": "live",
            "source_topics": [LIVE_CLOUD_TOPIC],
            "require_live_lidar": True,
            "live_lidar_publish_count": 10,
            "live_lidar_observations": self.observations,
        }
        self.display = {
            "source_topic": LIVE_CLOUD_TOPIC,
            "decay_time_seconds": 0.0,
            "retains_latest_until_replaced": True,
        }

    def _audit(self, *, visible=None):
        return build_live_pointcloud_continuity_audit(
            self.generated,
            self.native,
            self.display,
            [True] * 250 if visible is None else visible,
        )

    def test_10hz_simulator_sequence_passes(self) -> None:
        audit = self._audit()
        self.assertEqual(audit["status"], "PASS")
        self.assertAlmostEqual(audit["generated_scan_frequency_hz"], 10.0)
        self.assertAlmostEqual(audit["generated_received_coverage"], 1.0)

    def test_slow_wall_time_does_not_fail_normal_simulator_stamps(self) -> None:
        audit = self._audit()
        self.assertEqual(audit["wall_time_arrival_gap"]["median_seconds"], 2.0)
        self.assertNotIn("wall", " ".join(audit["checks"]))
        self.assertEqual(audit["status"], "PASS")

    def test_coverage_gate_is_exactly_ninety_five_percent(self) -> None:
        self.generated = [
            {
                "scan_reference_timestamp_ns": index * 100_000_000,
                "point_count": 15_000 + index,
            }
            for index in range(100)
        ]
        self.native["live_lidar_observations"] = [
            {
                "stamp_ns": index * 100_000_000,
                "wall_time_ns": 1_000_000_000 + index * 2_000_000_000,
                "point_count": 15_000 + index,
            }
            for index in range(95)
        ]
        self.assertEqual(self._audit()["status"], "PASS")
        self.native["live_lidar_observations"].pop()
        self.assertEqual(self._audit()["status"], "FAIL")

    def test_empty_received_cloud_fails(self) -> None:
        self.native["live_lidar_observations"][4]["point_count"] = 0
        audit = self._audit()
        self.assertFalse(audit["checks"]["all_received_clouds_nonempty"])
        self.assertEqual(audit["status"], "FAIL")

    def test_stamp_regression_fails(self) -> None:
        self.native["live_lidar_observations"][4]["stamp_ns"] = 100_000_000
        audit = self._audit()
        self.assertEqual(audit["stamp_regression_count"], 1)
        self.assertEqual(audit["status"], "FAIL")

    def test_simulator_gap_over_point_two_seconds_fails(self) -> None:
        for index, row in enumerate(self.native["live_lidar_observations"][5:], 5):
            row["stamp_ns"] = index * 100_000_000 + 200_000_000
        audit = self._audit()
        self.assertGreater(audit["simulator_time_gap"]["max_seconds"], 0.2)
        self.assertEqual(audit["status"], "FAIL")

    def test_disabled_live_lidar_audit_fails(self) -> None:
        self.native["require_live_lidar"] = False
        audit = self._audit()
        self.assertFalse(audit["checks"]["live_lidar_audit_required"])
        self.assertEqual(audit["status"], "FAIL")

    def test_zero_live_lidar_publish_count_fails(self) -> None:
        self.native["live_lidar_publish_count"] = 0
        audit = self._audit()
        self.assertFalse(audit["checks"]["live_lidar_publish_count_nonzero"])
        self.assertEqual(audit["status"], "FAIL")

    def test_old_point_four_second_decay_reproduces_long_blank_runs(self) -> None:
        frame_times = [index / 25.0 for index in range(48)]
        old_flags = expected_display_visibility([0.0, 1.89], frame_times, 0.4)
        persistent_flags = expected_display_visibility([0.0, 1.89], frame_times, 0.0)
        old_summary = summarize_visibility(old_flags)
        persistent_summary = summarize_visibility(persistent_flags)
        self.assertGreater(old_summary["longest_consecutive_invisible_frames"], 2)
        self.assertEqual(persistent_summary["longest_consecutive_invisible_frames"], 0)

    def test_rviz_persistence_does_not_change_source_topic(self) -> None:
        contract = load_live_cloud_display_contract(RVIZ_CONFIG)
        self.assertEqual(contract["source_topic"], LIVE_CLOUD_TOPIC)
        self.assertEqual(contract["decay_time_seconds"], 0.0)
        self.assertTrue(contract["retains_latest_until_replaced"])

    def test_consecutive_blank_video_frames_fail(self) -> None:
        visible = [False] * 4 + [True] * 10 + [False] * 3 + [True] * 233
        audit = self._audit(visible=visible)
        self.assertEqual(
            audit["video_visibility"]["longest_consecutive_invisible_frames"], 3
        )
        self.assertEqual(audit["status"], "FAIL")

    def test_wrong_source_topic_fails_even_with_persistent_display(self) -> None:
        self.display["source_topic"] = "/review/live_lidar"
        audit = self._audit()
        self.assertFalse(audit["checks"]["source_topic_is_quad_0_cloud_raw"])
        self.assertEqual(audit["status"], "FAIL")

    def test_transfer_validation_and_selection_are_fail_closed(self) -> None:
        master = {
            "width": 3840,
            "height": 1080,
            "r_frame_rate": "25/1",
            "frame_count": 251,
            "duration_seconds": 10.04,
            "size_bytes": 50_000_000,
        }
        candidate_probe = {
            **master,
            "codec_name": "h264",
            "profile": "High",
            "pix_fmt": "yuv420p",
            "color_space": "bt709",
            "color_transfer": "bt709",
            "color_primaries": "bt709",
            "size_bytes": 10_000_000,
        }
        validation = build_transfer_candidate_validation(
            master, candidate_probe, decoded_frame_count=251, ssim=0.98
        )
        self.assertEqual(validation["status"], "PASS")
        candidates = [
            {"status": "PASS", "probe": {"size_bytes": 12}, "crf": 22},
            {"status": "PASS", "probe": {"size_bytes": 8}, "crf": 24},
            {"status": "FAIL", "probe": {"size_bytes": 4}, "crf": 26},
        ]
        self.assertEqual(select_smallest_passing_candidate(candidates)["crf"], 24)
        with self.assertRaisesRegex(ValueError, "no transfer candidate"):
            select_smallest_passing_candidate(
                [{"status": "FAIL", "probe": {"size_bytes": 1}}]
            )


if __name__ == "__main__":
    unittest.main()

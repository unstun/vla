import unittest

from lite3_sim_bridge.rviz_replay_core import ReplayAuditState


class ReplayAuditStateTests(unittest.TestCase):
    def test_passing_summary_preserves_replay_only_claim(self):
        state = ReplayAuditState(sample_count=160)
        self.assertTrue(state.accept_body_stamp(10))
        self.assertTrue(state.accept_body_stamp(20))
        state.accept_bspline(7, 160, 15)
        state.accept_current_pose(root_transform_published=False)
        state.accept_current_pose(root_transform_published=False)
        state.accept_bbox_snapshot("frame_000001.npz")
        state.accept_voxel_snapshot("frame_000001.npz", 100, 500, 200)
        state.record_preloaded_snapshot("frame_000001.npz")

        summary = state.summary()

        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["trajectory_ids"], [7])
        self.assertEqual(summary["trajectory_point_counts"], {"7": 160})
        self.assertIn("replay-only", summary["claim_boundary"])
        self.assertIn("no planning", summary["claim_boundary"])
        self.assertEqual(summary["bbox_publish_count"], 1)
        self.assertEqual(summary["bbox_snapshot_files"], ["frame_000001.npz"])
        self.assertEqual(summary["voxel_publish_count"], 1)
        self.assertEqual(summary["preloaded_snapshot_file"], "frame_000001.npz")
        self.assertEqual(
            summary["voxel_point_counts"]["frame_000001.npz"],
            {"raw": 100, "inflated": 500, "live_lidar": 200},
        )
        self.assertEqual(summary["live_lidar_publish_count"], 1)
        self.assertIn("/review/live_lidar", summary["published_topics"])
        self.assertIn("from 1 Foxy-decoded snapshots", summary["claim_boundary"])

    def test_live_summary_requires_truthful_paths_pose_and_root_transform(self):
        state = ReplayAuditState(
            sample_count=160,
            source_mode="live",
            require_live_lidar=True,
            require_voxel_snapshots=False,
            require_root_transform=True,
        )
        state.accept_live_lidar_message(
            stamp_ns=100_000_000, point_count=15_000, wall_time_ns=1_000_000_000
        )
        state.accept_live_lidar_message(
            stamp_ns=200_000_000, point_count=15_100, wall_time_ns=3_000_000_000
        )
        self.assertTrue(state.accept_body_stamp(10))
        state.accept_current_pose(root_transform_published=True)
        self.assertTrue(state.accept_body_stamp(20))
        state.accept_current_pose(root_transform_published=True)
        state.accept_bspline(3, 160, 15)

        summary = state.summary()

        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["source_mode"], "live")
        self.assertIn("same run", summary["claim_boundary"])
        self.assertIn("no planning", summary["claim_boundary"])
        self.assertEqual(summary["root_transform_publish_count"], 2)
        self.assertNotIn("voxel_snapshots_observed", summary["checks"])
        self.assertIn("/review/lite3_current_pose", summary["published_topics"])
        self.assertNotIn("/review/live_lidar", summary["published_topics"])
        self.assertEqual(summary["live_lidar_received_count"], 2)
        self.assertEqual(summary["live_lidar_publish_count"], 2)

    def test_live_summary_fails_when_audit_is_disabled(self):
        state = ReplayAuditState(
            sample_count=160,
            source_mode="live",
            require_voxel_snapshots=False,
        )
        state.accept_live_lidar_message(
            stamp_ns=100_000_000, point_count=15_000, wall_time_ns=1_000_000_000
        )

        summary = state.summary()

        self.assertFalse(summary["checks"]["live_lidar_audit_enabled"])
        self.assertEqual(summary["status"], "FAIL")

    def test_live_summary_audits_empty_cloud_and_stamp_regression(self):
        state = ReplayAuditState(
            sample_count=160,
            source_mode="live",
            require_live_lidar=True,
            require_voxel_snapshots=False,
        )
        state.accept_live_lidar_message(
            stamp_ns=100_000_000, point_count=15_000, wall_time_ns=1_000_000_000
        )
        state.accept_live_lidar_message(
            stamp_ns=90_000_000, point_count=0, wall_time_ns=2_000_000_000
        )

        summary = state.summary()

        self.assertEqual(summary["live_lidar_empty_count"], 1)
        self.assertEqual(summary["live_lidar_stamp_regression_count"], 1)
        self.assertFalse(summary["checks"]["all_received_live_lidar_nonempty"])
        self.assertFalse(summary["checks"]["live_lidar_stamps_strictly_increase"])
        self.assertEqual(summary["status"], "FAIL")

    def test_non_increasing_body_stamp_is_rejected_and_audited(self):
        state = ReplayAuditState(sample_count=10)
        self.assertTrue(state.accept_body_stamp(20))
        self.assertFalse(state.accept_body_stamp(20))

        summary = state.summary()

        self.assertEqual(summary["body_pose_count"], 1)
        self.assertEqual(summary["rejected_body_pose_count"], 1)
        self.assertFalse(summary["checks"]["body_stamps_strictly_increase"])
        self.assertEqual(summary["status"], "FAIL")

    def test_wrong_sample_count_is_rejected(self):
        state = ReplayAuditState(sample_count=160)

        with self.assertRaisesRegex(ValueError, "expected 160"):
            state.accept_bspline(3, 159, 100)

    def test_empty_voxel_snapshot_is_rejected(self):
        state = ReplayAuditState(sample_count=160)

        with self.assertRaisesRegex(ValueError, "must be non-empty"):
            state.accept_voxel_snapshot("frame.npz", 0, 5)

    def test_required_live_lidar_is_fail_closed(self):
        state = ReplayAuditState(sample_count=160, require_live_lidar=True)

        with self.assertRaisesRegex(ValueError, "live LiDAR cloud must be non-empty"):
            state.accept_voxel_snapshot("frame.npz", 10, 50, 0)


if __name__ == "__main__":
    unittest.main()

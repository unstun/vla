import json
from pathlib import Path
import tempfile
import unittest

from lite3_sim_bridge.trajectory_review import (
    associate_bspline_sim_times,
    dynamic_obstacle_color_bgr,
    dynamic_obstacle_label,
    frame_metric_rows,
    render_trajectory_review,
    sample_uniform_bspline,
)


class TrajectoryReviewTest(unittest.TestCase):
    def test_dynamic_obstacle_overlay_distinguishes_official_human(self):
        official = {
            "dynamic_obstacle": {"shape": "official_skinned_human_plus_capsule"}
        }
        self.assertEqual(dynamic_obstacle_color_bgr(official), (40, 40, 235))
        self.assertEqual(dynamic_obstacle_label(official), "Official human actual")
        self.assertEqual(
            dynamic_obstacle_color_bgr(
                {"dynamic_obstacle": {"shape": "procedural_humanoid"}}
            ),
            (0, 215, 255),
        )
        self.assertEqual(
            dynamic_obstacle_label(
                {"dynamic_obstacle": {"shape": "procedural_humanoid"}}
            ),
            "Procedural human actual",
        )
        self.assertEqual(
            dynamic_obstacle_color_bgr(
                {"dynamic_obstacle": {"shape": "cylinder"}}
            ),
            (0, 120, 255),
        )
        self.assertEqual(
            dynamic_obstacle_label({"dynamic_obstacle": {"shape": "cylinder"}}),
            "Dynamic obstacle actual",
        )

    def test_samples_clamped_cubic_bspline_not_control_polygon(self):
        points = sample_uniform_bspline(
            order=3,
            knots=(0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0),
            control_points=(
                (0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (1.0, 1.0, 0.0),
                (1.0, 0.0, 0.0),
            ),
            sample_count=3,
        )
        self.assertEqual(points[0], (0.0, 0.0, 0.0))
        self.assertEqual(points[-1], (1.0, 0.0, 0.0))
        self.assertAlmostEqual(points[1][0], 0.5)
        self.assertAlmostEqual(points[1][1], 0.75)

    def test_rejects_inconsistent_bspline_shape(self):
        with self.assertRaisesRegex(ValueError, "knot count"):
            sample_uniform_bspline(
                order=3,
                knots=(0.0, 0.0, 1.0, 1.0),
                control_points=((0.0, 0.0, 0.0),) * 4,
            )

    def test_interpolates_plan_between_simulator_pose_receipts(self):
        events = [
            {
                "kind": "body_pose",
                "receipt_monotonic_ns": 1_000,
                "stamp_ns": 100_000_000,
                "position": [0.0, 0.0, 0.0],
            },
            {
                "kind": "bspline",
                "receipt_monotonic_ns": 1_080,
                "trajectory_id": 7,
                "order": 1,
                "start_time_ns": 123,
                "knots": [0.0, 0.0, 1.0, 1.0],
                "control_points": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            },
            {
                "kind": "body_pose",
                "receipt_monotonic_ns": 1_100,
                "stamp_ns": 200_000_000,
                "position": [0.1, 0.0, 0.0],
            },
        ]
        plans = associate_bspline_sim_times(events, sample_count=5)
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["trajectory_id"], 7)
        self.assertAlmostEqual(plans[0]["effective_sim_time_seconds"], 0.18)
        self.assertEqual(
            plans[0]["mapping_method"],
            "bracketed_simulator_time_interpolation",
        )
        self.assertAlmostEqual(plans[0]["receipt_alignment_error_ms"], 100.0)
        self.assertEqual(len(plans[0]["sampled_points"]), 5)

    def test_selects_exact_metrics_rows_used_for_video_frames(self):
        rows = [
            {"step": step, "sim_time_seconds": step * 0.02}
            for step in range(10)
        ]
        selected = frame_metric_rows(rows, frame_stride=3, frame_count=4)
        self.assertEqual([row["step"] for row in selected], [0, 3, 6, 9])
        with self.assertRaisesRegex(ValueError, "video frames"):
            frame_metric_rows(rows, frame_stride=3, frame_count=5)

    def test_renders_hashed_overlay_from_raw_plan_and_root_trace(self):
        import cv2
        import numpy as np

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_video = root / "raw.mp4"
            writer = cv2.VideoWriter(
                str(raw_video), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (320, 240)
            )
            self.assertTrue(writer.isOpened())
            for value in (30, 45, 60, 75):
                writer.write(np.full((240, 320, 3), value, dtype=np.uint8))
            writer.release()

            events = [
                {
                    "kind": "body_pose",
                    "receipt_monotonic_ns": 1_000,
                    "stamp_ns": 0,
                    "position": [0.0, 0.0, 0.4],
                },
                {
                    "kind": "bspline",
                    "receipt_monotonic_ns": 1_010,
                    "trajectory_id": 1,
                    "order": 1,
                    "start_time_ns": 1,
                    "knots": [0.0, 0.0, 1.0, 1.0],
                    "control_points": [[0.0, 0.0, 0.4], [1.0, 0.2, 0.4]],
                },
                {
                    "kind": "body_pose",
                    "receipt_monotonic_ns": 1_020,
                    "stamp_ns": 20_000_000,
                    "position": [0.1, 0.0, 0.4],
                },
            ]
            metrics = []
            for frame_index, step in enumerate((0, 3, 6, 9)):
                metrics.append(
                    {
                        "step": step,
                        "sim_time_seconds": frame_index * 0.06,
                        "root_pos_w": [frame_index * 0.25, 0.05 * frame_index, 0.4],
                        "root_lin_vel_w": [0.5, 0.0, 0.0],
                        "applied_command": [1.0, 0.0, 0.0],
                        "dynamic_obstacle_phase": (
                            "waiting" if frame_index == 0 else "crossing"
                        ),
                        "dynamic_obstacle_actual_pos_w": [
                            0.4,
                            -0.2 + 0.15 * frame_index,
                            0.75,
                        ],
                        "root_to_dynamic_surface_clearance_m": 0.4,
                    }
                )
            identity = {
                "video": {"frame_stride": 3},
                "dynamic_obstacle": {
                    "radius_m": 0.30,
                    "start_xy_m": [0.4, -0.2],
                    "end_xy_m": [0.4, 0.4],
                },
                "forest_scene": {
                    "navigation": {
                        "start_world_m": [0.0, 0.0, 0.4],
                        "goal_world_m": [1.0, 0.2, 0.4],
                        "primary_blocker": {"name": "tree"},
                    },
                    "proxies": [
                        {
                            "name": "tree",
                            "shape": "cylinder",
                            "center_m": [0.5, 0.0, 1.0],
                            "size_m": [0.2, 0.2, 2.0],
                        }
                    ],
                },
            }
            events_path = root / "events.jsonl"
            metrics_path = root / "metrics.jsonl"
            identity_path = root / "identity.json"
            events_path.write_text(
                "".join(json.dumps(row) + "\n" for row in events), encoding="utf-8"
            )
            metrics_path.write_text(
                "".join(json.dumps(row) + "\n" for row in metrics), encoding="utf-8"
            )
            identity_path.write_text(json.dumps(identity), encoding="utf-8")
            output = root / "overlay.mp4"
            metadata_path = root / "overlay.json"
            metadata = render_trajectory_review(
                raw_video,
                events_path,
                metrics_path,
                identity_path,
                output,
                metadata_path,
            )
            self.assertTrue(output.is_file())
            self.assertTrue(metadata_path.is_file())
            self.assertEqual(metadata["output"]["frame_count"], 4)
            self.assertEqual(metadata["trajectory_ids"], [1])
            self.assertTrue(metadata["dynamic_obstacle"]["rendered"])
            self.assertEqual(metadata["dynamic_obstacle"]["record_count"], 4)
            decoded = cv2.VideoCapture(str(output))
            self.assertTrue(decoded.isOpened())
            self.assertEqual(int(decoded.get(cv2.CAP_PROP_FRAME_COUNT)), 4)
            decoded.release()


if __name__ == "__main__":
    unittest.main()

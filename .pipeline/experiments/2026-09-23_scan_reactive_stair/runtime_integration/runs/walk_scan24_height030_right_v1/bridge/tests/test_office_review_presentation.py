"""Fail-closed tests for Office L0 review presentation evidence."""

import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

import numpy as np

from lite3_sim_bridge.office_review_presentation import (
    PRESERVED_FIRST_VIEW_CAMERA_MODEL,
    REVIEW_MATERIAL_LIMB_RGB,
    REVIEW_MATERIAL_TORSO_RGB,
    apply_office_review_material_usd,
    camera_trace_row,
    frozen_quality_profile,
    isometric_project,
    normalize_side,
    office_actor_root_paths,
    office_floor_root_paths,
    office_l0_cutaway_root_paths,
    overview_desired_pose,
    preserved_first_view_pose,
    render_temporally_settled_frame,
    render_office_review_dashboard,
    review_film_iso,
    side_follow_desired_pose,
    smooth_pose_bounded,
    validate_office_review_presentation,
    validate_overview_camera_config,
    validate_side_camera_config,
)
from lite3_sim_bridge.rviz_time_sync import (
    observe_camera_trace,
    synchronize_rviz_video,
)


class MockPrim:
    def __init__(self, path):
        self.path = path

    def IsValid(self):
        return True


class MockStage:
    def __init__(self, root="/World/envs/env_0/Robot"):
        self.mock_body_paths = [f"{root}/base", f"{root}/FL_thigh"]
        self.mock_joint_paths = [f"{root}/joint1"]
        self.mock_collision_paths = [f"{root}/base/collision"]
        self.mock_visual_mesh_paths = [f"{root}/torso/visual", f"{root}/FL_thigh/visual"]
        self.mock_material_bindings = {p: "/World/Looks/Original" for p in self.mock_visual_mesh_paths}
        self.mock_mass_properties = {f"{root}/base": 12.5}
        self.mock_inertia_properties = {f"{root}/base": [1.0, 1.1, 1.2]}
        self.mock_sensor_target_paths = [f"{root}/mid360_scan_frame", f"{root}/d435i_depth_optical_frame"]

    def GetPrimAtPath(self, path):
        return MockPrim(path)


class GeometryTest(unittest.TestCase):
    def test_fixed_exposure_and_temporal_settling(self):
        profile = frozen_quality_profile()
        self.assertFalse(profile["renderer_auto_exposure"])
        self.assertEqual(profile["renderer_settle_render_count"], 3)
        self.assertAlmostEqual(review_film_iso(0.0), 100.0)
        self.assertAlmostEqual(review_film_iso(-1.0), 50.0)
        self.assertAlmostEqual(review_film_iso(1.0), 200.0)
        with self.assertRaises(ValueError):
            review_film_iso(5.0)

        rendered = []

        def render_once():
            rendered.append(len(rendered) + 1)
            return rendered[-1]

        self.assertEqual(render_temporally_settled_frame(render_once, 3), 3)
        self.assertEqual(rendered, [1, 2, 3])
        with self.assertRaises(ValueError):
            render_temporally_settled_frame(render_once, 0)

    def test_camera_geometry_and_bounds(self):
        side = validate_side_camera_config({})
        overview = validate_overview_camera_config({"azimuth_offset_deg": 0.0})
        self.assertEqual(normalize_side("left"), -1.0)
        eye, target = side_follow_desired_pose(0, 0, 0.3, 0, side)
        self.assertAlmostEqual(eye[0], -1.5)
        self.assertAlmostEqual(eye[1], 3.0)
        self.assertAlmostEqual(target[0], 1.0)
        eye, target = overview_desired_pose(0, 0, 0.3, 0, overview)
        self.assertAlmostEqual(eye[0], -6.5)
        self.assertAlmostEqual(eye[2], 4.8)
        self.assertAlmostEqual(target[0], 2.0)
        values = smooth_pose_bounded(
            (0, 0, 0), (0, 0, 0), (100, 0, 0), (0, 100, 0),
            dt=0.1, smoothing_rate=100, max_eye_speed=5, max_target_speed=5,
        )
        self.assertEqual(values[0], (0.5, 0.0, 0.0))
        self.assertAlmostEqual(values[2], values[4])
        with self.assertRaises(ValueError):
            validate_side_camera_config({"smoothing_rate": 0})
        with self.assertRaises(ValueError):
            validate_side_camera_config({"focal_length_mm": 3.0})
        with self.assertRaises(ValueError):
            normalize_side("front")
        trace = camera_trace_row(
            0, 0, 0.0, "run", [0, 0, 0.3], [1, 0, 0, 0],
            [-2, 0, 2], [0, 0, 0.3], eye, target, eye, target, {},
            eye, target, eye, target, overview, 0.04,
        )
        self.assertEqual(
            trace["side_follow"]["camera_model"],
            "high_oblique_l0_global_cutaway_v3_height8m",
        )
        self.assertEqual(
            trace["first_view"]["camera_model"],
            PRESERVED_FIRST_VIEW_CAMERA_MODEL,
        )

    def test_preserved_first_view_keeps_original_chase_equations(self):
        eye, target = preserved_first_view_pose(1.0, 2.0, 0.35, 0.0)
        self.assertAlmostEqual(eye[0], -1.2)
        self.assertEqual(eye[1:], (2.0, 2.15))
        self.assertEqual(target, (1.6, 2.0, 0.51))
        eye, target = preserved_first_view_pose(1.0, 2.0, 1.0, math.pi / 2.0)
        self.assertAlmostEqual(eye[0], 1.0)
        self.assertAlmostEqual(eye[1], -0.2)
        self.assertEqual(eye[2], 2.4)
        self.assertAlmostEqual(target[0], 1.0)
        self.assertAlmostEqual(target[1], 2.6)
        with self.assertRaises(ValueError):
            preserved_first_view_pose(0, 0, float("nan"), 0)

    def test_office_cutaway_selects_only_ceiling_actor_roots(self):
        paths = [
            "/World/Environment/SM_Ceiling_6m24",
            "/World/Environment/SM_Ceiling_6m24/SM_Ceiling_6m",
            "/World/Environment/BP_CeilingLight17/Light",
            "/World/ground/Root/Environment/SM_Ceiling_3m07/SM_Ceiling_3m",
            "/World/ground/OfficeL0Physics/Root/BP_CeilingLight18/Light",
            "/World/Environment/SM_Floor_6m24/SM_Floor_6m",
            "/World/Environment/SM_Wall_3m01/SM_Wall_3m",
            "/World/envs/env_0/Robot/base",
        ]
        self.assertEqual(
            office_l0_cutaway_root_paths(paths),
            [
                "/World/Environment/BP_CeilingLight17",
                "/World/Environment/SM_Ceiling_6m24",
                "/World/ground/OfficeL0Physics/Root/BP_CeilingLight18",
                "/World/ground/Root/Environment/SM_Ceiling_3m07",
            ],
        )
        floor_roots = office_floor_root_paths(paths)
        self.assertEqual(
            floor_roots,
            ["/World/Environment/SM_Floor_6m24"],
        )
        actors = office_actor_root_paths(
            paths,
            [
                "/World/Environment/SM_Ceiling_6m24",
                "/World/Environment/SM_Floor_6m24",
            ],
        )
        self.assertIn("/World/Environment/SM_Floor_6m24", actors)
        self.assertIn("/World/Environment/SM_Wall_3m01", actors)

    def test_material_audit_and_true_3d_projection(self):
        self.assertEqual(REVIEW_MATERIAL_TORSO_RGB, (1.0, 1.0, 1.0))
        self.assertEqual(REVIEW_MATERIAL_LIMB_RGB, (1.0, 1.0, 1.0))
        audit = apply_office_review_material_usd(
            MockStage(), robot_asset_sha256="robot-sha",
            referenced_mesh_sha256={"body.stl": "mesh-sha"},
        )
        self.assertTrue(audit["physics_inventory_unchanged"])
        self.assertEqual(audit["pre_inventory"]["query_phase"], "before_binding")
        self.assertEqual(audit["post_inventory"]["query_phase"], "after_binding")
        self.assertNotEqual(audit["pre_inventory"]["material_bindings"], audit["post_inventory"]["material_bindings"])
        low = isometric_project(1, 1, 0, 0, 0, 100, 480, 360)
        high = isometric_project(1, 1, 1, 0, 0, 100, 480, 360)
        self.assertEqual(low[0], high[0])
        self.assertAlmostEqual(low[1] - high[1], 100)


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        names = {
            "first": "closed_loop.mp4", "side": "closed_loop_third_person_side.mp4",
            "overview": "closed_loop_overview.mp4", "trace": "camera_trace.jsonl",
            "audit": "material_audit.json", "dashboard": "dashboard.mp4",
            "metadata": "dashboard.json", "events": "events.jsonl", "metrics": "metrics.jsonl",
            "identity": "run_identity.json", "effective": "effective_input.txt",
            "acceptance": "acceptance.json",
        }
        for attr, name in names.items():
            setattr(self, attr, self.root / name)
        self._video(self.first, (40, 100, 180))
        self._video(self.side, (80, 190, 70))
        self._video(self.overview, (190, 70, 80))
        self.effective.write_text(
            "duration_seconds=0.4\ncourse=office_l0_crowd\nvideo_fps=25\n",
            encoding="utf-8",
        )
        self.acceptance.write_text('{"goal_tolerance_m":0.6}', encoding="utf-8")
        self.capture_profile = frozen_quality_profile()
        self.capture_profile["exposure"] = -0.25
        self.capture_profile["renderer_film_iso"] = review_film_iso(
            self.capture_profile["exposure"],
            self.capture_profile["renderer_base_film_iso"],
        )
        self.capture_profile["fps"] = 25.0
        self.identity.write_text(json.dumps({
            "config_sha256": "run-sha", "course": "office_l0_crowd",
            "acceptance_config_sha256": self._sha(self.acceptance),
            "office_review_presentation": {
                "first_view_model": PRESERVED_FIRST_VIEW_CAMERA_MODEL,
                "first_view": {
                    "focal_length_mm": 24.0,
                    "horizontal_aperture_mm": 45.55,
                    "horizontal_fov_degrees": math.degrees(
                        2.0 * math.atan(45.55 / 48.0)
                    ),
                },
                "quality_profile": self.capture_profile,
            },
        }), encoding="utf-8")
        self._trace()
        apply_office_review_material_usd(
            MockStage(), audit_output_path=self.audit, robot_asset_sha256="robot-sha",
            referenced_mesh_sha256={"body.stl": "mesh-sha"},
        )
        events = [
            {"kind": "body_pose", "stamp_ns": 0, "receipt_monotonic_ns": 0, "sim_time_seconds": 0.0},
            {"kind": "body_pose", "stamp_ns": 400000000, "receipt_monotonic_ns": 400000000, "sim_time_seconds": 0.4},
            {"kind": "bspline", "stamp_ns": 0, "receipt_monotonic_ns": 0, "start_time_ns": 0,
             "trajectory_id": 7, "order": 3, "start_time_s": 0.0, "duration_s": 5.0,
             "control_points": [[-15.6, 13.1, .28], [-15, 12.5, .30], [-14, 11.5, .35],
                                [-13, 10.5, .31], [-12, 9.5, .38]],
             "knots": [0, 0, 0, 0, 2.5, 5, 5, 5, 5]},
            {"kind": "occupancy_inflate", "stamp_ns": 10000000, "point_count": 3,
             "points_xyz": [[-14.5, 12.5, .30], [-14.2, 12.2, .32], [-13.8, 11.8, .35]]},
        ]
        self.events.write_text("".join(json.dumps(x) + "\n" for x in events), encoding="utf-8")
        metrics = [
            {"step": k * 2, "sim_time": k * .04,
             "root_pos_w": [-15.625 + k * .05, 13.125 - k * .025, .28 + k * .005],
             "root_lin_vel_w": [.4, 0, 0], "applied_command": [.5, 0, 0],
             "supported_contact_ratio": 1.0, "nonfoot_contact_max_force_n": 0.0}
            for k in range(10)
        ]
        self.metrics.write_text("".join(json.dumps(x) + "\n" for x in metrics), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _video(self, path, color, fps=25):
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self.skipTest("ffmpeg unavailable")
        profile = frozen_quality_profile()
        width = int(profile["resolution_width"])
        height = int(profile["resolution_height"])
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-f", "rawvideo",
            "-pixel_format", "rgb24", "-video_size", f"{width}x{height}", "-framerate", str(fps),
            "-i", "-", "-an", "-c:v", "libx264", "-profile:v", "high", "-preset", "medium",
            "-crf", str(profile["crf"]), "-pix_fmt", "yuv420p", "-color_range", "tv",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1",
            str(path),
        ]
        proc = subprocess.Popen(command, stdin=subprocess.PIPE)
        for k in range(10):
            frame = np.full((height, width, 3), color, dtype=np.uint8)
            frame[:, k * 10:(k + 1) * 10] = 255
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        self.assertEqual(proc.wait(), 0)

    def _trace(self):
        profile = dict(self.capture_profile)
        delta = math.hypot(.05, .025)
        rows = []
        for k in range(10):
            root = [-15.625 + k * .05, 13.125 - k * .025, .28 + k * .005]
            side_eye = [-15 + k * .05, 10 - k * .025, 2]
            target = [-15 + k * .05, 13 - k * .025, .3]
            overview_eye = [-10 + k * .05, 8 - k * .025, 4.5]
            row = camera_trace_row(
                k, k * 2, k * .04, "run-sha", root, [1, 0, 0, 0],
                [-17 + k * .05, 13 - k * .025, 2], target,
                side_eye, target, side_eye, target, {"side": "left"},
                overview_eye, target, overview_eye, target, {}, .04,
                0 if k == 0 else delta, 0 if k == 0 else delta, .32, .32,
                0 if k == 0 else delta, 0 if k == 0 else delta, .24, .24,
                renderer_settings=profile,
            )
            row["first_view"].update({
                "focal_length_mm": 24.0,
                "horizontal_aperture_mm": 45.55,
                "horizontal_fov_degrees": math.degrees(
                    2.0 * math.atan(45.55 / 48.0)
                ),
            })
            rows.append(row)
        self.trace.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")

    def _render(self):
        return render_office_review_dashboard(
            self.first, self.side, self.overview, self.trace, self.audit,
            self.events, self.metrics, self.identity, self.effective, self.acceptance,
            self.dashboard, self.metadata,
        )

    def _validate(self, **changes):
        paths = dict(
            first_video_path=self.first, side_video_path=self.side, overview_video_path=self.overview,
            camera_trace_path=self.trace, material_audit_path=self.audit,
            dashboard_video_path=self.dashboard, dashboard_metadata_path=self.metadata,
            ros_events_path=self.events, metrics_path=self.metrics, run_identity_path=self.identity,
            effective_input_path=self.effective, acceptance_config_path=self.acceptance,
        )
        paths.update(changes)
        return validate_office_review_presentation(**paths)

    def _refresh(self, key, path):
        metadata = json.loads(self.metadata.read_text(encoding="utf-8"))
        metadata["input_sha256"][key] = self._sha(path)
        self.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    def test_full_dashboard_decode_and_overwrite_gate(self):
        self.assertEqual(self._render()["frame_count"], 10)
        report = self._validate()
        self.assertTrue(report["passed"], report["issues"])
        self.assertEqual(set(report["checks"]["decoded_frames"].values()), {10})
        with self.assertRaises(FileExistsError):
            self._render()

    def test_duplicate_content_and_low_fps_are_rejected(self):
        self._render()
        duplicate = self._validate(side_video_path=self.first)
        self.assertFalse(duplicate["passed"])
        low = self.root / "low.mp4"
        self._video(low, (80, 190, 70), fps=12)
        report = self._validate(side_video_path=low)
        self.assertFalse(report["passed"])
        self.assertTrue(any("below 25" in x or "rates differ" in x for x in report["issues"]))

    def test_truncated_requested_duration_is_rejected(self):
        self._render()
        self.effective.write_text(
            "duration_seconds=1.0\ncourse=office_l0_crowd\nvideo_fps=25\n",
            encoding="utf-8",
        )
        self._refresh("effective_input", self.effective)
        report = self._validate()
        self.assertFalse(report["passed"])
        self.assertTrue(any("requested" in issue for issue in report["issues"]))

    def test_trace_forgery_is_rejected(self):
        self._render()
        rows = [json.loads(x) for x in self.trace.read_text(encoding="utf-8").splitlines()]
        rows[3]["run_identity"] = "wrong"
        rows[3]["step"] = rows[2]["step"]
        rows[3]["side_follow"]["realized_eye"] = [100, 100, 100]
        self.trace.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
        self._refresh("camera_trace", self.trace)
        issues = "\n".join(self._validate()["issues"])
        self.assertIn("run identity", issues)
        self.assertIn("strictly increasing", issues)
        self.assertIn("displacement", issues)

    def test_material_and_provenance_forgery_are_rejected(self):
        self._render()
        audit = json.loads(self.audit.read_text(encoding="utf-8"))
        audit["affected_prims"][0]["opacity"] = .5
        audit["post_inventory"]["mass_properties"]["/World/envs/env_0/Robot/base"] = 99
        self.audit.write_text(json.dumps(audit), encoding="utf-8")
        self._refresh("material_audit", self.audit)
        report = self._validate()
        self.assertFalse(report["passed"])
        self.assertTrue(any("inventory changed" in x or "translucent" in x for x in report["issues"]))
        report = self._validate(ros_events_path=self.root / "missing.jsonl")
        self.assertFalse(report["passed"])

    def test_candidate_and_flat_z_are_rejected(self):
        self._render()
        report = self._validate(first_video_path=Path("/tmp/candidate38/closed_loop.mp4"))
        self.assertTrue(any("candidate" in x for x in report["issues"]))
        metrics = [json.loads(x) for x in self.metrics.read_text(encoding="utf-8").splitlines()]
        for row in metrics:
            row["root_pos_w"][2] = 0
        self.metrics.write_text("".join(json.dumps(x) + "\n" for x in metrics), encoding="utf-8")
        self._refresh("metrics", self.metrics)
        self.assertTrue(any("zero Z variation" in x for x in self._validate()["issues"]))

    def test_native_rviz_is_selected_at_matching_simulator_times(self):
        timeline = self.root / "rviz_timeline.jsonl"
        output = self.root / "rviz_sim_time.mp4"
        metadata_path = self.root / "rviz_sim_time.json"
        rows = [
            {
                "kind": "capture_clock",
                "schema_version": 1,
                "capture_start_epoch_ns": 1,
                "poll_seconds": 0.005,
                "clock": "CLOCK_REALTIME_epoch_ns",
            }
        ]
        rows.extend(
            {
                "kind": "trace_observation",
                "schema_version": 1,
                "frame_index": k,
                "step": k * 2,
                "sim_time_seconds": k * 0.04,
                "observed_epoch_ns": 1 + k * 40_000_000,
                "capture_elapsed_seconds": k * 0.04,
            }
            for k in range(10)
        )
        timeline.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        metadata = synchronize_rviz_video(
            self.side,
            timeline,
            self.trace,
            self.first,
            output,
            metadata_path,
        )
        self.assertEqual(metadata["frame_count"], 10)
        self.assertEqual(
            [row["source_rviz_frame_index"] for row in metadata["frame_mapping"]],
            list(range(10)),
        )
        self.assertTrue(output.is_file())

    def test_rviz_observer_waits_for_complete_jsonl_row(self):
        source = self.root / "live_camera_trace.jsonl"
        timeline = self.root / "live_rviz_timeline.jsonl"
        producer = subprocess.Popen(
            ["python3", "-c", "import time; time.sleep(0.25)"]
        )
        result = {}
        errors = []

        def _observe():
            try:
                result["count"] = observe_camera_trace(
                    source,
                    timeline,
                    capture_start_epoch_ns=time.time_ns(),
                    producer_pid=producer.pid,
                    poll_seconds=0.001,
                )
            except BaseException as exc:  # test thread must surface failures
                errors.append(exc)

        thread = threading.Thread(target=_observe)
        thread.start()
        time.sleep(0.02)
        with source.open("w", encoding="utf-8") as handle:
            handle.write('{"frame_index":0,"step":0,')
            handle.flush()
            time.sleep(0.03)
            handle.write('"sim_time_seconds":0.03}\n')
            handle.flush()
        producer.wait()
        thread.join(timeout=2.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(result["count"], 1)
        rows = [json.loads(line) for line in timeline.read_text().splitlines()]
        self.assertEqual(rows[0]["clock"], "CLOCK_MONOTONIC_ns")
        self.assertEqual(rows[1]["frame_index"], 0)


class EntrypointWiringTest(unittest.TestCase):
    def test_office_entrypoint_wires_review_mode(self):
        repo = Path(__file__).resolve().parents[3]
        runner = (repo / "integration/lite3_sim_bridge/lite3_sim_bridge/run_isaac_v12_fallback.py").read_text()
        presentation = (repo / "integration/lite3_sim_bridge/lite3_sim_bridge/office_review_presentation.py").read_text()
        shared = (repo / ".pipeline/experiments/2026-08-13_scan_foxy_isaac_closed_loop/run_remote_closed_loop.sh").read_text()
        office = (repo / ".pipeline/experiments/2026-08-17_office_l0_scan_crowd/run_remote_office_crowd.sh").read_text()
        native_rviz = (repo / ".pipeline/experiments/2026-08-17_office_l0_scan_crowd/run_remote_office_crowd_native_rviz.sh").read_text()
        foxy_bridge = (
            repo / "integration/lite3_sim_bridge/lite3_sim_bridge/foxy_bridge_node.py"
        ).read_text()
        package_xml = (repo / "integration/lite3_sim_bridge/package.xml").read_text()
        native_rviz_launch = (
            repo
            / "integration/lite3_sim_bridge/launch/native_rviz_review.launch.py"
        ).read_text()
        for token in (
            "DirectH264Writer", "office_review_validation_report_path",
            "office_review_effective_input_path", "office_review_ros_events_snapshot.jsonl",
            "office_review_camera_focal_length_mm", "GetFocalLengthAttr",
            "side_render_rejected_frame.png",
            "render_temporally_settled_frame",
            "/rtx/post/histogram/enabled",
            "/rtx/post/tonemap/filmIso",
            "review_wall_seconds",
            "max_step_wall_seconds",
        ):
            self.assertIn(token, runner)
        self.assertIn('"${OFFICE_REVIEW_ARGS[@]}"', shared)
        self.assertIn("office-review-camera-focal-length-mm", shared)
        self.assertIn("office_review_output_sha256.txt", shared)
        self.assertIn("SCAN_NATIVE_RVIZ_ENABLED", shared)
        self.assertIn("SCAN_NATIVE_RVIZ_PRESTART_GATE", shared)
        self.assertIn("SCAN_VISUAL_REVIEW_ONLY", shared)
        self.assertIn("SCAN_RECORD_ROSBAG", shared)
        self.assertIn("rosbag.disabled.txt", shared)
        self.assertIn(
            "SCAN_RECORD_ROSBAG=0 is allowed only with SCAN_VISUAL_REVIEW_ONLY=1",
            shared,
        )
        self.assertIn('rviz2 -d "$NATIVE_RVIZ_CONFIG_CONTAINER"', shared)
        self.assertIn("native_rviz_review.launch.py", shared)
        self.assertIn("/quad_0/joint_states", shared)
        self.assertIn("NATIVE_RVIZ_ROBOT_ASSET_CONTAINER", shared)
        self.assertIn("SCAN_OFFICE_REVIEW_ENABLED=1", office)
        self.assertIn("SCAN_VIDEO_FPS=25", office)
        self.assertIn("SCAN_VIDEO_FRAME_STRIDE=2", office)
        self.assertIn("SCAN_ENABLE_VOXEL_CAPTURE=1", office)
        self.assertIn("SCAN_VISUAL_REVIEW_ONLY=${SCAN_VISUAL_REVIEW_ONLY:-0}", office)
        self.assertIn("SCAN_RECORD_ROSBAG=${SCAN_RECORD_ROSBAG:-1}", office)
        self.assertIn("SCAN_OFFICE_REVIEW_CAMERA_SIDE=right", office)
        self.assertIn("SCAN_OFFICE_REVIEW_CAMERA_LATERAL_DISTANCE=3.5", office)
        self.assertIn("SCAN_OFFICE_REVIEW_CAMERA_TRAILING_BIAS=3.5", office)
        self.assertIn("SCAN_OFFICE_REVIEW_CAMERA_HEIGHT=8.0", office)
        self.assertIn("SCAN_OFFICE_REVIEW_CAMERA_FOCAL_LENGTH_MM=18.0", office)
        self.assertIn("SIDE_VIEW_CAMERA_MODEL", runner)
        self.assertIn("PRESERVED_FIRST_VIEW_CAMERA_MODEL", runner)
        self.assertIn("preserved_first_view_pose", runner)
        self.assertNotIn("review_optical_camera_pose", runner)
        self.assertIn("GetHorizontalApertureAttr", runner)
        self.assertIn("high_oblique_l0_global_cutaway_v3_height8m", presentation)
        self.assertIn("office_l0_cutaway_root_paths", runner)
        self.assertIn("native_scan_voxel_review.mp4", office)
        self.assertIn("office_review_native_scan_dashboard.mp4", office)
        self.assertIn("SCAN_NATIVE_RVIZ_ENABLED=1", native_rviz)
        self.assertIn("SCAN_RVIZ_STARTUP_TIMEOUT_SECONDS", native_rviz)
        self.assertIn("native_scan_rviz3d_5070ti.mp4", native_rviz)
        self.assertIn("native_scan_rviz3d_5070ti_sim_time.mp4", native_rviz)
        self.assertIn("office_review_terminal_validation.json", native_rviz)
        self.assertIn("office_review_third_person_rviz_4k.mp4", native_rviz)
        self.assertIn("office_review_third_person_rviz_4k_transfer.mp4", native_rviz)
        self.assertIn("live_pointcloud_continuity_audit.json", native_rviz)
        self.assertIn("lite3_sim_bridge.delivery_reliability audit", native_rviz)
        self.assertIn("lite3_sim_bridge.delivery_reliability compress", native_rviz)
        self.assertIn("office_pedestrian_motion_audit.json", native_rviz)
        self.assertIn(
            "SCAN_OFFICE_PEDESTRIAN_MOTION_MODE=background_ping_pong",
            native_rviz,
        )
        self.assertIn("SCAN_OFFICIAL_HUMAN_ANIMATION_MODE=phase_conditioned", native_rviz)
        self.assertIn("_runtime_gate_metrics", native_rviz)
        self.assertIn("goal_world_xy_m", native_rviz)
        self.assertIn("continuous_terminal_stop", native_rviz)
        self.assertIn("scale=1920:1080:flags=lanczos", native_rviz)
        self.assertIn("[side][rviz]hstack=inputs=2[review]", native_rviz)
        self.assertNotIn("vstack=inputs=2", native_rviz)
        self.assertIn('"resolution": [3840, 1080]', native_rviz)
        self.assertIn("lite3_sim_bridge.rviz_time_sync", native_rviz)
        self.assertIn("foxy_native_scan_review.rviz", native_rviz)
        self.assertEqual(
            native_rviz.count(
                "export PYTHONPATH=$BRIDGE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
            ),
            2,
        )
        self.assertNotIn(
            'export PYTHONPATH="$RUN_ROOT/integration/lite3_sim_bridge',
            native_rviz,
        )
        rviz_review = (
            repo / "integration/lite3_sim_bridge/config/foxy_native_scan_review.rviz"
        ).read_text()
        for topic in (
            "/map_generator/global_cloud",
            "/quad_0/cloud_raw",
            "/grid_map/occupancy",
            "/grid_map/occupancy_inflate",
            "/review/lite3_actual_path",
            "/review/lite3_current_pose",
            "/review/scan_planned_path",
            "/robot_description",
        ):
            self.assertIn(topic, rviz_review)
        self.assertIn("Current Lite3 Position (live pose)", rviz_review)
        self.assertNotIn("/quad_0/path", rviz_review)
        self.assertNotIn("/optimal_list", rviz_review)
        self.assertIn("Lite3 URDF (measured joints)", rviz_review)
        self.assertIn("Current Lite3 Pose (TORSO)", rviz_review)
        self.assertIn("Sparse Waypoints / Final Goal", rviz_review)
        self.assertIn("Target Frame: TORSO", rviz_review)
        self.assertIn("Alpha: 0.14000000000000001", rviz_review)
        self.assertIn("TransformBroadcaster", foxy_bridge)
        self.assertIn("self._transform_broadcaster.sendTransform", foxy_bridge)
        self.assertIn("decode_joint_state_payload", foxy_bridge)
        self.assertIn("<exec_depend>tf2_ros</exec_depend>", package_xml)
        self.assertIn("<exec_depend>robot_state_publisher</exec_depend>", package_xml)
        self.assertIn("file://{}/meshes/", native_rviz_launch)
        self.assertIn('"source_mode": "live"', native_rviz_launch)
        self.assertIn('"robot_root_frame": "TORSO"', native_rviz_launch)
        self.assertIn('"require_live_lidar": True', native_rviz_launch)
        self.assertIn("SCAN_NATIVE_RVIZ_PRESTART_GATE=1", native_rviz)
        self.assertLess(
            native_rviz_launch.index('executable="rviz_replay_node"'),
            native_rviz_launch.index('executable="robot_state_publisher"'),
        )


if __name__ == "__main__":
    unittest.main()

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "make_walk_review.py"
RUN_ID = "synthetic_run"
T0_NS = 1_000_000_000_000
STEP_NS = 20_000_000


def load_module():
    spec = importlib.util.spec_from_file_location("make_walk_review", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def mono(step):
    return T0_NS + step * STEP_NS


def snapshot(step, x):
    return {"run_id": RUN_ID, "sim_time_s": 0.02 * (step + 1), "measured": {"base_xyz": [x, 0.0, 0.35]}}


def state(terminals):
    return {"terminal_results": terminals, "pct": {"plan_history": [
        {"request_id": RUN_ID + "-goal-a-attempt-1", "ok": True, "started_monotonic_s": mono(2) / 1e9,
         "waypoints_m": [[0.0, 0.0, 0.35], [1.0, 0.0, 0.35]]}]}}


def journal(complete=True):
    """Driver/backend events at known steps; the incomplete variant fails attempt 2."""
    events = [
        {"event": "initial_cancel_reference_snapshot", "snapshot": snapshot(0, 0.0), "wall_monotonic_ns": mono(0) + 5},
        {"event": "post_goal", "payload": {"request_id": RUN_ID + "-goal-a-attempt-1", "goal_id": "goal-a",
                                           "target_ground_xyz": [2.0, 0.0, 0.0]},
         "response": {"ok": True}, "wall_monotonic_ns": mono(2) + 5},
        {"event": "post_cancel", "trigger_snapshot": snapshot(4, 0.4), "response": {"ok": True},
         "cancel_displacement_m": 0.4, "wall_monotonic_ns": mono(5) + 5},
        {"event": "post_stop_proof", "dwell_start_sim_s": 0.02 * 8, "snapshot": snapshot(8, 0.45),
         "wall_monotonic_ns": mono(9) + 5},
        {"event": "post_goal", "payload": {"request_id": RUN_ID + "-goal-a-attempt-2", "goal_id": "goal-a",
                                           "target_ground_xyz": [2.0, 0.0, 0.0]},
         "response": {"ok": True}, "wall_monotonic_ns": mono(9) + 9},
    ]
    terminals = [{"request_id": RUN_ID + "-goal-a-attempt-1", "status": "cancelled", "monotonic_s": (mono(6) + 5) / 1e9}]
    if complete:
        terminals.append({"request_id": RUN_ID + "-goal-a-attempt-2", "status": "arrived", "monotonic_s": (mono(11) + 5) / 1e9})
        events.append({"event": "post_goal", "payload": {"request_id": RUN_ID + "-goal-b", "goal_id": "goal-b",
                                                         "target_ground_xyz": [3.0, 0.0, 0.0]},
                       "response": {"ok": True}, "wall_monotonic_ns": mono(12) + 5})
        terminals.append({"request_id": RUN_ID + "-goal-b", "status": "arrived", "monotonic_s": (mono(14) + 5) / 1e9})
    else:
        terminals.append({"request_id": RUN_ID + "-goal-a-attempt-2", "status": "failed",
                          "cause": "initial_heartbeat_missing", "monotonic_s": (mono(10) + 5) / 1e9})
        events.append({"event": "driver_error", "error": "timed out", "wall_monotonic_ns": mono(16) + 60 * 10**9})
    events.append({"event": "state_poll", "state": state(terminals), "wall_monotonic_ns": mono(16)})
    return {"passed": complete, "events": events}


def metric_rows(steps=17):
    return [{"step": s, "sim_time_s": 0.02 * (s + 1), "state_sample_monotonic_ns": mono(s),
             "base_xyz": [0.1 * s, 0.0, 0.35], "base_rpy_rad": [0.0, 0.0, 0.0], "horizontal_speed_mps": 0.5,
             "command_horizontal_norm_mps": 0.5, "admitted_command": [0.5, 0.0, 0.0], "raw_command": [0.5, 0.0, 0.0],
             "nonfoot_force_max_n": 0.0} for s in range(steps)]


def write_run(root, complete=True, video_frames=5, camera_rows=5):
    run = Path(root) / RUN_ID
    out = run / "returned_artifacts/runner_output"
    out.mkdir(parents=True)
    (run / "inputs").mkdir()
    (run / "inputs/pilot.json").write_text(json.dumps({"goal_xy_tolerance_m": 0.25, "goals": [
        {"goal_id": "goal-a", "ground_xyz_m": [2.0, 0.0, 0.0]}, {"goal_id": "goal-b", "ground_xyz_m": [3.0, 0.0, 0.0]}]}))
    (run / "returned_artifacts/pilot_journal.json").write_text(json.dumps(journal(complete)))
    (out / "metrics.jsonl").write_text("".join(json.dumps(r) + "\n" for r in metric_rows()))
    (out / "camera_frames.jsonl").write_text("".join(
        json.dumps({"frame_index": i, "step": 4 * i, "sim_time_s": 0.02 * (4 * i + 1)}) + "\n" for i in range(camera_rows)))
    (out / "run_clock.json").write_text(json.dumps({"complete_body_state_period_s": 0.02}))
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc=size=320x180:rate=12.5", "-frames:v", str(video_frames), "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", str(out / "third_person_master.mp4")], check=True)
    return run


class EventAndAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.m = load_module()

    def test_events_phases_and_positions_follow_the_journal(self):
        parsed = self.m.extract_journal(journal(True), RUN_ID, self.m.StateIndex(metric_rows()))
        keys = [e["key"] for e in parsed["events"]]
        self.assertEqual(keys, ["goal_a_sent", "cancel_sent", "cancel_confirmed", "still_dwell_start", "still_confirmed",
                                "goal_a_resent", "arrived_a", "goal_b_sent", "arrived_b"])
        self.assertEqual(parsed["missing"], [])
        by_key = {e["key"]: e for e in parsed["events"]}
        # Wall/backend times map to the last state row not after them.
        self.assertAlmostEqual(by_key["cancel_sent"]["sim_time_s"], 0.02 * 6)
        self.assertAlmostEqual(by_key["cancel_confirmed"]["sim_time_s"], 0.02 * 7)
        self.assertAlmostEqual(by_key["still_dwell_start"]["sim_time_s"], 0.16)
        self.assertEqual(parsed["points"]["stop"]["xyz"][0], 0.45)
        self.assertEqual(parsed["points"]["cancel"]["xyz"][0], 0.4)
        self.assertEqual(self.m.phase_at(parsed["events"], 0.0)[0], "standing, no goal sent")
        self.assertEqual(self.m.phase_at(parsed["events"], 0.12)[0], "cancel sent, stopping")
        self.assertEqual(by_key["cancel_confirmed"]["phase"], "cancel confirmed, stopping")
        self.assertEqual(self.m.phase_at(parsed["events"], 0.17)[0], "stopped, confirming stillness (dwell)")
        # A dwell that began before the backend's cancel record changes the confirmation text.
        early = [{"key": "still_dwell_start", "sim_time_s": 0.12}, {"key": "cancel_confirmed", "sim_time_s": 0.14}]
        self.assertEqual(self.m.phase_text(early[1], early), "cancel confirmed, confirming stillness")
        self.assertEqual(self.m.phase_at(parsed["events"], 0.2)[0], "resubmitted A, walking to A")
        self.assertEqual(self.m.phase_at(parsed["events"], 10.0)[0], "arrived B")
        self.assertEqual(len(parsed["plans"]), 1)

    def test_failed_run_marks_failure_missing_events_and_late_driver_error(self):
        parsed = self.m.extract_journal(journal(False), RUN_ID, self.m.StateIndex(metric_rows()))
        self.assertEqual(parsed["missing"], ["arrived_a", "goal_b_sent", "arrived_b"])
        failed = [e for e in parsed["events"] if e.get("unexpected_status")]
        self.assertEqual(failed[0]["phase"], "A attempt 2 failed: initial_heartbeat_missing")
        late = [e for e in parsed["events"] if e["key"] == "driver_error"][0]
        self.assertEqual(late["placement"], "after_recorded_state")
        self.assertNotIn(late, self.m.timeline_events(parsed["events"]))
        self.assertEqual(self.m.phase_at(parsed["events"], 10.0)[0], "A attempt 2 failed: initial_heartbeat_missing")

    def test_frame_alignment_rules(self):
        self.assertEqual(self.m.align_frames(207, 207)[0], 207)
        count, rule = self.m.align_frames(208, 207)
        self.assertEqual((count, rule.split(":")[0]), (207, "video_plus_one"))
        count, rule = self.m.align_frames(206, 207)
        self.assertEqual((count, rule.split(":")[0]), (206, "camera_plus_one"))
        for video in (205, 209):
            with self.assertRaisesRegex(self.m.InputError, "video has %d frames and camera_frames.jsonl has 207" % video):
                self.m.align_frames(video, 207)

    def test_equal_limits_give_equal_metres_per_pixel(self):
        (x0, x1), (y0, y1) = self.m.equal_limits(-2.0, 3.0, -4.6, -4.4, 365, 418)
        self.assertAlmostEqual((x1 - x0) / 365, (y1 - y0) / 418)
        self.assertAlmostEqual((y0 + y1) / 2, -4.5)
        (x0, x1), (y0, y1) = self.m.equal_limits(0.0, 0.1, 0.0, 5.0, 365, 418)
        self.assertAlmostEqual((x1 - x0) / 365, (y1 - y0) / 418)

    def test_goal_mismatch_between_pilot_and_journal_is_refused(self):
        with self.assertRaisesRegex(self.m.InputError, "differs between inputs/pilot.json"):
            self.m.resolve_goals(journal(True), {"goals": [{"goal_id": "goal-a", "ground_xyz_m": [2.5, 0.0, 0.0]},
                                                           {"goal_id": "goal-b", "ground_xyz_m": [3.0, 0.0, 0.0]}]})


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg is not installed")
class RenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def render(self, run, name, *extra):
        output = self.root / "out" / (name + ".mp4")
        proc = subprocess.run([sys.executable, str(SCRIPT), str(run), "--output", str(output), "--preset", "ultrafast", *extra],
                              capture_output=True, text=True)
        return proc, output

    def test_render_writes_video_and_sidecar(self):
        run = write_run(self.root / "a")
        proc, output = self.render(run, "review")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        sidecar = json.loads(output.with_suffix(".json").read_text())
        self.assertEqual(sidecar["output"]["frames"], 5)
        self.assertEqual((sidecar["output"]["width"], sidecar["output"]["height"]), (1280, 720))
        self.assertEqual(sidecar["output"]["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertTrue(sidecar["frame_alignment"]["rule"].startswith("equal"))
        self.assertEqual(sidecar["frame_alignment"]["state_row_rules"], ["same_step"])
        self.assertEqual(sidecar["encoder"]["used"], "libx264")
        self.assertEqual(sidecar["missing_events"], [])
        self.assertEqual(sidecar["inputs"]["pilot_journal"]["sha256"],
                         hashlib.sha256((run / "returned_artifacts/pilot_journal.json").read_bytes()).hexdigest())
        proc, _ = self.render(run, "review")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("refusing to overwrite", proc.stderr)

    def test_one_extra_video_frame_is_tolerated_and_two_are_refused(self):
        run = write_run(self.root / "b", complete=False, video_frames=6)
        proc, output = self.render(run, "plus_one")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        sidecar = json.loads(output.with_suffix(".json").read_text())
        self.assertEqual(sidecar["frame_alignment"]["decoded_frames"], 6)
        self.assertEqual(sidecar["output"]["frames"], 5)
        self.assertTrue(sidecar["frame_alignment"]["rule"].startswith("video_plus_one"))
        self.assertEqual(sidecar["missing_events"], ["arrived_a", "goal_b_sent", "arrived_b"])
        run = write_run(self.root / "c", video_frames=7)
        proc, output = self.render(run, "plus_two")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("the video has 7 frames and camera_frames.jsonl has 5 rows", proc.stderr)
        self.assertFalse(output.exists())

    def test_missing_video_asks_for_override_and_override_works(self):
        run = write_run(self.root / "d")
        moved = self.root / "remote_original.mp4"
        (run / "returned_artifacts/runner_output/third_person_master.mp4").rename(moved)
        proc, _ = self.render(run, "missing")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("pass --video", proc.stderr)
        proc, output = self.render(run, "override", "--video", str(moved))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(output.with_suffix(".json").read_text())["inputs"]["video"]["path"], str(moved))


PINNED_TOOL_COMMIT = "20f24308afac3c5668722f058524b2942b8d1c3b"  # last make_walk_review.py before stance modes
STANCE_SEQUENCE = (["RL"] * 3 + ["STAND_SETTLING"] * 3 + ["STAND_TRANSITION"] * 4 + ["FIXED_STAND"] * 4
                   + ["REJOIN"] * 2 + ["RL"])


def stance_rows():
    rows = metric_rows()
    for row, mode in zip(rows, STANCE_SEQUENCE):
        row["stance_mode"] = mode
        row["stance_hold"] = "auto"
    return rows


def load_pinned_tool(tmp):
    repo = Path(subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], capture_output=True,
                               text=True).stdout.strip() or HERE)
    rel = SCRIPT.resolve().relative_to(repo.resolve()).as_posix()
    proc = subprocess.run(["git", "-C", str(repo), "show", "%s:%s" % (PINNED_TOOL_COMMIT, rel)], capture_output=True)
    if proc.returncode:
        return None
    path = Path(tmp) / "make_walk_review_pinned.py"
    path.write_bytes(proc.stdout)
    spec = importlib.util.spec_from_file_location("make_walk_review_pinned", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def context_for(module, run):
    artifacts = run / "returned_artifacts"
    paths = {
        "camera_frames": artifacts / "runner_output/camera_frames.jsonl",
        "metrics": artifacts / "runner_output/metrics.jsonl",
        "pilot_journal": artifacts / "pilot_journal.json",
        "pilot": run / "inputs/pilot.json",
        "run_request": None,
    }
    return module.build_context(run, paths)


def render_frame(module, ctx, index):
    renderer = module.Renderer(ctx)
    frame = bytes(range(256)) * (module.CAM_W * module.CAM_H * 3 // 256) + bytes(module.CAM_W * module.CAM_H * 3 % 256)
    cam_row = ctx["camera_rows"][index]
    state_idx, _ = ctx["state"].row_for_frame(cam_row)
    return bytes(renderer.render(frame, index, len(ctx["camera_rows"]), cam_row, state_idx))


class StanceModeTests(unittest.TestCase):
    def setUp(self):
        self.m = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write_run(self, name, rows):
        run = self.root / name / RUN_ID
        out = run / "returned_artifacts/runner_output"
        out.mkdir(parents=True)
        (run / "inputs").mkdir()
        (run / "inputs/pilot.json").write_text(json.dumps({"goal_xy_tolerance_m": 0.25, "goals": [
            {"goal_id": "goal-a", "ground_xyz_m": [2.0, 0.0, 0.0]}, {"goal_id": "goal-b", "ground_xyz_m": [3.0, 0.0, 0.0]}]}))
        (run / "returned_artifacts/pilot_journal.json").write_text(json.dumps(journal(True)))
        (out / "metrics.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        (out / "camera_frames.jsonl").write_text("".join(
            json.dumps({"frame_index": i, "step": 4 * i, "sim_time_s": 0.02 * (4 * i + 1)}) + "\n" for i in range(5)))
        return run

    def test_segments_and_optional_field(self):
        rows = stance_rows()
        sim = [r["sim_time_s"] for r in rows]
        stance = self.m.stance_segments(rows, sim)
        self.assertEqual([s["mode"] for s in stance["segments"]],
                         ["RL", "STAND_SETTLING", "STAND_TRANSITION", "FIXED_STAND", "REJOIN", "RL"])
        fixed = stance["segments"][3]
        self.assertAlmostEqual(fixed["start_s"], sim[10])
        self.assertAlmostEqual(fixed["end_s"], sim[14])
        self.assertEqual(fixed["rows"], 4)
        self.assertAlmostEqual(stance["mode_seconds"]["FIXED_STAND"], 0.08)
        self.assertIsNone(self.m.stance_segments(metric_rows(), sim))
        run = self.write_run("rows", rows)
        kept = self.m.load_state_rows(run / "returned_artifacts/runner_output/metrics.jsonl")
        self.assertEqual([r["stance_mode"] for r in kept], STANCE_SEQUENCE)
        self.assertNotIn("stance_hold", kept[0])
        old = self.m.load_state_rows(self.write_run("old", metric_rows()) / "returned_artifacts/runner_output/metrics.jsonl")
        self.assertNotIn("stance_mode", old[0])

    def test_old_run_frames_match_the_pinned_tool(self):
        pinned = load_pinned_tool(self.root)
        if pinned is None:
            self.skipTest("git history with commit %s is unavailable" % PINNED_TOOL_COMMIT)
        self.assertFalse(hasattr(pinned, "stance_segments"))
        run = self.write_run("old", metric_rows())
        new_ctx = context_for(self.m, run)
        old_ctx = context_for(pinned, run)
        self.assertIsNone(new_ctx.pop("stance"))
        self.assertEqual(set(new_ctx), set(old_ctx))
        for index in (0, 2, 4):
            self.assertEqual(render_frame(self.m, new_ctx, index), render_frame(pinned, old_ctx, index), index)

    def test_stance_run_shows_mode_label_and_shading(self):
        run = self.write_run("stance", stance_rows())
        ctx = context_for(self.m, run)
        renderer = self.m.Renderer(ctx)
        self.assertIsNotNone(renderer.banner_stance)
        spans = [p for p in renderer.speed_ax.patches if p.get_facecolor()[:3] == matplotlib_rgb("#1f77b4")]
        self.assertEqual(len(spans), 1)
        cam_row = ctx["camera_rows"][3]
        state_idx, _ = ctx["state"].row_for_frame(cam_row)
        self.assertEqual(ctx["stance"]["modes"][state_idx], "FIXED_STAND")
        frame = bytes(self.m.CAM_W * self.m.CAM_H * 3)
        renderer.render(frame, 3, 5, cam_row, state_idx)
        self.assertEqual(renderer.banner_stance.get_text(), "stance: FIXED_STAND")
        renderer.render(frame, 0, 5, ctx["camera_rows"][0], 0)
        self.assertEqual(renderer.banner_stance.get_text(), "stance: RL")
        plain = self.write_run("plain", metric_rows())
        self.assertNotEqual(render_frame(self.m, ctx, 3), render_frame(self.m, context_for(self.m, plain), 3))


def matplotlib_rgb(color):
    from matplotlib.colors import to_rgb
    return tuple(to_rgb(color))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg is not installed")
class StanceRenderTests(unittest.TestCase):
    def test_sidecar_lists_stance_segments_only_for_stance_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = write_run(Path(tmp) / "s")
            metrics = run / "returned_artifacts/runner_output/metrics.jsonl"
            metrics.write_text("".join(json.dumps(r) + "\n" for r in stance_rows()))
            output = Path(tmp) / "out/stance.mp4"
            proc = subprocess.run([sys.executable, str(SCRIPT), str(run), "--output", str(output), "--preset", "ultrafast"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            sidecar = json.loads(output.with_suffix(".json").read_text())
            self.assertEqual([s["mode"] for s in sidecar["stance_hold"]["segments"]][3], "FIXED_STAND")
            plain = write_run(Path(tmp) / "p")
            output = Path(tmp) / "out/plain.mp4"
            proc = subprocess.run([sys.executable, str(SCRIPT), str(plain), "--output", str(output), "--preset", "ultrafast"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn("stance_hold", json.loads(output.with_suffix(".json").read_text()))


if __name__ == "__main__":
    unittest.main()

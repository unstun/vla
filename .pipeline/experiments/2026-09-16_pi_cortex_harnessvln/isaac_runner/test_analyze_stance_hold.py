import contextlib
import io
import json
import math
from pathlib import Path
import tempfile
import unittest

import analyze_stance_hold as analyzer

HERE = Path(__file__).resolve().parent
OLD_STAND_RUN = HERE / "runs/stand_20260916T152235Z_p2b_fix1"
OLD_TWO_GOAL_RUN = HERE / "two_goal_runs/two_goal_20260917T090126Z_scanfix_e03"
C1_HOLD_AUTO_RUN = HERE / "runs/stand_20260917T125239Z_hold_auto"
C2_E06_RUN = HERE / "two_goal_runs/two_goal_20260918T030524Z_hold_e06"
PREVIOUS_THRESHOLDS = HERE / "stance_hold_thresholds_history/stance_hold_thresholds_fb8f9204.json"
PREVIOUS_THRESHOLDS_SHA256 = "fb8f9204c18e0b400ae2b7a2abc22bb052526538ff9713689759f15bff897c66"
AC7_THRESHOLDS = HERE / "stance_hold_thresholds_history/stance_hold_thresholds_12373448.json"
AC7_THRESHOLDS_SHA256 = "12373448a8aee02534b529c69189bc5155bbe13cb0d17b632d260b075e075da5"
AC8_THRESHOLDS = HERE / "stance_hold_thresholds_history/stance_hold_thresholds_683a8ca6.json"
AC8_THRESHOLDS_SHA256 = "683a8ca6d9d26fe4c45af22fc449c1c05525fde9eb0fb3dc4125c4f2831b43b8"
D6_THRESHOLDS = HERE / "stance_hold_thresholds_history/stance_hold_thresholds_0be59927.json"
D6_THRESHOLDS_SHA256 = "0be59927aa18ad97cc6dfc01a3179867ce84e71e712286ee971a485a5238a29d"
D5_SCRIPT = HERE / "command_scripts/walk_stop_start_stop_v1.json"
DT = 0.02


def stand_rows(seconds=60.0, settle_until=2.7, fixed_from=4.72, stance=True):
    rows = []
    for k in range(int(round(seconds / DT))):
        t = round((k + 1) * DT, 6)
        row = {
            "step": k,
            "sim_time_s": t,
            "base_xyz": [1.0 + 0.0001 * min(k, 50), 2.0, 0.35],
            "base_rpy_rad": [0.01, 0.02, 0.1],
            "horizontal_speed_mps": 0.005,
            "base_linear_velocity_world": [0.005, 0.0, 0.002 if k % 2 else -0.002],
            "yaw_rate_radps": 0.01 if k % 2 else -0.01,
            "admitted_command": [0.0, 0.0, 0.0],
            "foot_force_norms": [30.0, 30.0, 30.0, 30.0],
            "nonfoot_force_max_n": 0.0,
            "nonfoot_force_substep_max_n": 0.0,
            "applied_torque_max_ratio": 0.2,
            "torque_clip_joint_count": 0,
        }
        if stance:
            if t <= settle_until:
                mode, reason = "STAND_SETTLING", "waiting_for_quiet_four_contact"
            elif t < fixed_from:
                mode, reason = "STAND_TRANSITION", "quiet_four_contact_confirmed"
            else:
                mode, reason = "FIXED_STAND", "fixed_stand_active"
            row.update({"stance_hold": "auto", "stance_mode": mode, "stance_reason": reason,
                        "policy_owns_joints": mode == "STAND_SETTLING",
                        "delayed_target_torque_max_ratio_estimate": 0.3})
        else:
            row.update({"stance_hold": "off", "stance_mode": "OFF", "policy_owns_joints": True})
        rows.append(row)
    return rows


def write_run(root, name, rows, summary=None, case="stand_probe", mode="auto"):
    out = Path(root) / name / "returned_artifacts/runner_output"
    out.mkdir(parents=True)
    (out / "metrics.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    base = {"case": case, "status": "EXTERNAL_EPISODE_FINISHED", "max_nonfoot_force_n": 0.0,
            "nonfoot_contact_events_over_threshold": [], "stance_hold": {"mode": mode, "failure": None,
                                                                         "gain_writes": 1, "fsm": None}}
    base.update(summary or {})
    (out / "summary.json").write_text(json.dumps(base))
    return out.parents[1]


def move_rows():
    """Walk, stop and hold, then walk again through REJOIN."""
    rows = []
    plan = (["RL"] * 50 + ["STAND_SETTLING"] * 20 + ["STAND_TRANSITION"] * 100 + ["FIXED_STAND"] * 60
            + ["REJOIN"] * 13 + ["RL"] * 30)
    for k, mode in enumerate(plan):
        moving = k < 50 or k >= 230
        rows.append({
            "step": k,
            "sim_time_s": round((k + 1) * DT, 6),
            "base_xyz": [0.01 * k, 0.0, 0.35],
            "base_rpy_rad": [0.0, 0.03, 0.0],
            "horizontal_speed_mps": 0.3 if moving else 0.01,
            "base_linear_velocity_world": [0.3 if moving else 0.01, 0.0, 0.003],
            "yaw_rate_radps": 0.02,
            "admitted_command": [0.3, 0.0, 0.0] if moving else [0.0, 0.0, 0.0],
            "foot_force_norms": [30.0] * 4,
            "nonfoot_force_max_n": 0.0,
            "nonfoot_force_substep_max_n": 0.0,
            "stance_hold": "auto",
            "stance_mode": mode,
            "stance_reason": {"REJOIN": "new_command_rejoin"}.get(mode, "x"),
            "torque_clip_joint_count": 0,
            "applied_torque_max_ratio": 0.3,
            "delayed_target_torque_max_ratio_estimate": 0.4,
        })
    return rows


class ThresholdTests(unittest.TestCase):
    def test_thresholds_file_is_frozen_with_prd_values(self):
        loaded = analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS)
        self.assertTrue(loaded["frozen"])
        self.assertEqual(loaded["sha256"], analyzer.FROZEN_THRESHOLDS_SHA256)
        ac3 = loaded["values"]["ac3_stand"]
        self.assertEqual((ac3["min_foot_force_exclusive_n"], ac3["max_planar_drift_m"], ac3["max_horizontal_speed_mps"],
                          ac3["max_abs_yaw_rate_radps"], ac3["max_abs_roll_deg"], ac3["max_abs_pitch_deg"],
                          ac3["max_torque_clip_steps"], ac3["max_nonfinite_values"], ac3["max_time_to_fixed_stand_s"]),
                         (1.0, 0.02, 0.02, 0.05, 5.0, 5.0, 0, 0, 10.0))
        ac5 = loaded["values"]["ac5_transitions"]
        self.assertEqual((ac5["max_nonfoot_force_exclusive_n"], ac5["max_abs_roll_deg_during_rejoin"],
                          ac5["max_abs_pitch_deg_during_rejoin"], ac5["max_torque_clip_steps_at_entry_or_rejoin"]),
                         (5.0, 10.0, 10.0, 0))
        ac7 = loaded["values"]["ac7_entry"]
        self.assertEqual((ac7["window_s"], ac7["window_tolerance_s"], ac7["max_abs_yaw_rate_radps"],
                          ac7["max_abs_vertical_speed_mps"]), (1.0, 0.001, 0.15, 0.05))
        self.assertEqual(ac7["added"], "2026-09-17 before the C1 rerun, PRD D4")
        self.assertEqual(loaded["values"]["amendments"][0]["previous_sha256"], PREVIOUS_THRESHOLDS_SHA256)
        ac8 = loaded["values"]["ac8_walk"]
        self.assertEqual([(p["start_s"], p["end_s"], p["command"]) for p in ac8["phases"]], [
            (0.0, 4.0, [0.0, 0.0, 0.0]), (4.0, 7.0, [0.6, 0.0, 0.0]), (7.0, 12.0, [0.0, 0.0, 0.0]),
            (12.0, 14.5, [0.6, 0.0, 0.0]), (14.5, 20.0, [0.0, 0.0, 0.0])])
        self.assertEqual(ac8["finish_request_s"], 20.0)
        self.assertEqual(ac8["command_script"]["sha256"], analyzer.sha256_file(D5_SCRIPT))
        self.assertEqual(ac8["command_script"]["path"], str(D5_SCRIPT.relative_to(HERE)))
        c = ac8["c_start"]
        self.assertEqual((c["window_s"], c["max_nonfoot_force_exclusive_n"], c["max_abs_roll_deg"],
                          c["max_abs_pitch_deg"], c["max_abs_pitch_excess_over_off_deg"]), (1.0, 5.0, 10.0, 10.0, 3.0))
        self.assertEqual(ac8["d_run"]["completed_statuses"], ["EXTERNAL_EPISODE_FINISHED", "DURATION_REACHED"])
        self.assertEqual(ac8["d_run"]["max_planar_travel_relative_difference"], 0.2)
        r = ac8["reporting"]
        self.assertEqual((r["still_max_horizontal_speed_mps"], r["still_max_abs_yaw_rate_radps"],
                          r["still_duration_s"], r["phase_tail_s"], r["start_window_s"]), (0.05, 0.15, 0.5, 2.0, 1.0))
        self.assertIn("lowest max |yaw_rate_radps|", ac8["selection"]["rule"])
        self.assertEqual(loaded["values"]["amendments"][1]["previous_sha256"], AC7_THRESHOLDS_SHA256)
        self.assertEqual(loaded["values"]["amendments"][2]["previous_sha256"], AC8_THRESHOLDS_SHA256)
        self.assertIn("xfade1s, xfade2s (PRD D6)", ac8["run"])
        # PRD D7 (post-result): the AC7 window also ends at a restart.
        self.assertIs(ac7["end_at_restart"], True)
        self.assertIn("neither STAND_TRANSITION nor FIXED_STAND", ac7["restart"])
        amendment = ac7["amendment"]
        self.assertEqual((amendment["decision"], amendment["date"], amendment["by"], amendment["post_result"],
                          amendment["previous_sha256"], amendment["previous_copy"]),
                         ("PRD D7", "2026-09-18", "Dr Sun", True, D6_THRESHOLDS_SHA256,
                          str(D6_THRESHOLDS.relative_to(HERE))))
        self.assertEqual(amendment["quote"], "Change the AC7 rule to stop the evaluation window at a restart, and "
                                             "explicitly label it as a post-result change in the report.")
        self.assertIn("two_goal_20260918T030524Z_hold_e06", amendment["trigger"])
        self.assertIn("step 332", amendment["trigger"])
        self.assertEqual(loaded["values"]["amendments"][3]["previous_sha256"], D6_THRESHOLDS_SHA256)

    def test_amendment_only_adds_ac7_to_the_previous_frozen_file(self):
        self.assertEqual(analyzer.sha256_file(PREVIOUS_THRESHOLDS), PREVIOUS_THRESHOLDS_SHA256)
        previous = json.loads(PREVIOUS_THRESHOLDS.read_text())
        ac7_file = json.loads(AC7_THRESHOLDS.read_text())
        self.assertEqual(set(ac7_file) - set(previous), {"ac7_entry", "amendments"})
        self.assertEqual({k: v for k, v in ac7_file.items() if k in previous}, previous)
        self.assertEqual(ac7_file["amendments"][0]["previous_copy"],
                         str(PREVIOUS_THRESHOLDS.relative_to(HERE)))
        # The superseded file is refused like any other file, with a pointer to its history.
        with self.assertRaisesRegex(analyzer.AnalysisError, "superseded"):
            analyzer.load_thresholds(PREVIOUS_THRESHOLDS)
        self.assertIn(PREVIOUS_THRESHOLDS_SHA256, analyzer.SUPERSEDED_THRESHOLDS)
        self.assertNotEqual(analyzer.FROZEN_THRESHOLDS_SHA256, PREVIOUS_THRESHOLDS_SHA256)

    def test_amendment_only_adds_ac8_to_the_ac7_file(self):
        self.assertEqual(analyzer.sha256_file(AC7_THRESHOLDS), AC7_THRESHOLDS_SHA256)
        previous = json.loads(AC7_THRESHOLDS.read_text())
        current = json.loads(AC8_THRESHOLDS.read_text())
        self.assertEqual(set(current) - set(previous), {"ac8_walk"})
        self.assertEqual({k: v for k, v in current.items() if k not in ("amendments", "ac8_walk")},
                         {k: v for k, v in previous.items() if k != "amendments"})
        self.assertEqual(current["amendments"][:-1], previous["amendments"])
        last = current["amendments"][-1]
        self.assertEqual((last["previous_sha256"], last["previous_copy"]),
                         (AC7_THRESHOLDS_SHA256, str(AC7_THRESHOLDS.relative_to(HERE))))
        self.assertEqual(len(current["amendments"]), 2)
        with self.assertRaisesRegex(analyzer.AnalysisError, "superseded .*12373448"):
            analyzer.load_thresholds(AC7_THRESHOLDS)
        self.assertNotEqual(analyzer.FROZEN_THRESHOLDS_SHA256, AC7_THRESHOLDS_SHA256)

    def test_d6_amendment_only_renames_the_ac8_run_text(self):
        """PRD D6: the crossfade variants are named; no limit, window or rule changes."""
        self.assertEqual(analyzer.sha256_file(AC8_THRESHOLDS), AC8_THRESHOLDS_SHA256)
        self.assertEqual(analyzer.sha256_file(D6_THRESHOLDS), D6_THRESHOLDS_SHA256)
        previous = json.loads(AC8_THRESHOLDS.read_text())
        current = json.loads(D6_THRESHOLDS.read_text())
        self.assertEqual(set(current), set(previous))
        self.assertEqual({k: v for k, v in current.items() if k not in ("amendments", "ac8_walk")},
                         {k: v for k, v in previous.items() if k not in ("amendments", "ac8_walk")})
        self.assertEqual({k: v for k, v in current["ac8_walk"].items() if k != "run"},
                         {k: v for k, v in previous["ac8_walk"].items() if k != "run"})
        self.assertEqual(current["ac8_walk"]["run"],
                         previous["ac8_walk"]["run"].replace(
                             "(--stance-entry-kd ramp, step1, step2p5)",
                             "(--stance-entry-kd ramp, step1, step2p5, or xfade1s, xfade2s (PRD D6))"))
        self.assertEqual(current["amendments"][:-1], previous["amendments"])
        last = current["amendments"][-1]
        self.assertEqual((last["date"], last["previous_sha256"], last["previous_copy"], last["frozen_before"]),
                         ("2026-09-17", AC8_THRESHOLDS_SHA256, str(AC8_THRESHOLDS.relative_to(HERE)),
                          "the D6 scripted-walk runs"))
        self.assertIn("no limit, window, definition or selection rule changed", last["change"])
        self.assertEqual(len(current["amendments"]), 3)
        with self.assertRaisesRegex(analyzer.AnalysisError, "superseded .*683a8ca6"):
            analyzer.load_thresholds(AC8_THRESHOLDS)
        self.assertNotEqual(analyzer.FROZEN_THRESHOLDS_SHA256, AC8_THRESHOLDS_SHA256)
        self.assertEqual(analyzer.sha256_file(analyzer.DEFAULT_THRESHOLDS), analyzer.FROZEN_THRESHOLDS_SHA256)

    def test_d7_amendment_only_adds_the_restart_rule_to_ac7(self):
        """PRD D7 (post-result): ac7_entry gains the restart rule; limits, AC8 and every other section are unchanged."""
        self.assertEqual(analyzer.sha256_file(D6_THRESHOLDS), D6_THRESHOLDS_SHA256)
        previous = json.loads(D6_THRESHOLDS.read_text())
        current = json.loads(analyzer.DEFAULT_THRESHOLDS.read_text())
        self.assertEqual(set(current), set(previous))
        self.assertEqual({k: v for k, v in current.items() if k not in ("amendments", "ac7_entry")},
                         {k: v for k, v in previous.items() if k not in ("amendments", "ac7_entry")})
        self.assertEqual(set(current["ac7_entry"]) - set(previous["ac7_entry"]),
                         {"end_at_restart", "restart", "amendment"})
        self.assertEqual({k: v for k, v in current["ac7_entry"].items() if k in previous["ac7_entry"]},
                         previous["ac7_entry"])
        self.assertEqual(current["ac8_walk"]["b_entry_windows"], previous["ac8_walk"]["b_entry_windows"])
        self.assertEqual(current["amendments"][:-1], previous["amendments"])
        last = current["amendments"][-1]
        self.assertEqual((last["date"], last["post_result"], last["previous_sha256"], last["previous_copy"]),
                         ("2026-09-18", True, D6_THRESHOLDS_SHA256, str(D6_THRESHOLDS.relative_to(HERE))))
        self.assertIn("post-result", last["frozen_before"])
        self.assertEqual(len(current["amendments"]), 4)
        with self.assertRaisesRegex(analyzer.AnalysisError, "superseded .*0be59927"):
            analyzer.load_thresholds(D6_THRESHOLDS)
        self.assertIn(D6_THRESHOLDS_SHA256, analyzer.SUPERSEDED_THRESHOLDS)
        self.assertNotEqual(analyzer.FROZEN_THRESHOLDS_SHA256, D6_THRESHOLDS_SHA256)

    def test_changed_thresholds_are_refused_unless_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            values = json.loads(analyzer.DEFAULT_THRESHOLDS.read_text())
            values["ac3_stand"]["max_abs_yaw_rate_radps"] = 0.2
            path.write_text(json.dumps(values))
            with self.assertRaisesRegex(analyzer.AnalysisError, "not the frozen"):
                analyzer.load_thresholds(path)
            self.assertFalse(analyzer.load_thresholds(path, allow_unfrozen=True)["frozen"])


class StandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.thresholds = analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS)
        self.off = write_run(self.root, "off", stand_rows(stance=False), mode="off")

    def analyze(self, rows, name="on", summary=None):
        on = write_run(self.root, name, rows, summary=summary)
        return analyzer.analyze_stand(on, self.off, self.thresholds)

    def test_quiet_hold_passes_and_baseline_uses_the_same_window(self):
        result = self.analyze(stand_rows())
        ac3 = result["ac3"]
        self.assertEqual(ac3["verdict"], "pass", ac3["problems"])
        self.assertAlmostEqual(ac3["time_to_fixed_stand"]["seconds"], 4.72)
        self.assertAlmostEqual(ac3["checks"]["yaw_rate"]["value"], 0.01)
        self.assertAlmostEqual(ac3["fixed_stand"]["seconds"], (3000 - 235) * DT)
        self.assertEqual(ac3["fixed_stand"]["segments"], 1)
        window = ac3["baseline_off"]["window"]
        self.assertEqual((window["start_s"], window["end_s"]), (4.72, 60.0))
        self.assertEqual(ac3["baseline_off"]["stance_fields"], ["OFF"])
        self.assertEqual(result["ac5"]["on"]["verdict"], "pass")
        self.assertEqual(result["ac5"]["on"]["entries"], [{"step": 135, "sim_time_s": 2.72}])
        self.assertEqual(result["ac5"]["on"]["entry_or_rejoin_steps"], [135, 136])
        self.assertEqual(result["ac5"]["off"]["verdict"], "pass")
        self.assertEqual(result["ac5"]["off"]["entries"], [])
        ac7 = result["ac7"]["on"]
        self.assertEqual(ac7["verdict"], "pass", ac7["problems"])
        self.assertEqual(len(ac7["entry_windows"]), 1)
        window = ac7["entry_windows"][0]
        self.assertEqual((window["entry_step"], window["start_s"], window["end_s"], window["rows"]),
                         (135, 2.72, 3.72, 51))
        self.assertAlmostEqual(window["max_abs_vertical_speed_mps"], 0.002)
        self.assertEqual(result["ac7"]["off"]["verdict"], "not_applicable")
        json.dumps(result, allow_nan=False)

    def test_each_ac3_limit_fails(self):
        def mutate(name, **changes):
            rows = stand_rows()
            for row in rows[1000:1001]:
                row.update(changes)
            return name, rows

        cases = [
            ("yaw_rate", *mutate("yaw", yaw_rate_radps=-0.0501)),
            ("horizontal_speed", *mutate("speed", horizontal_speed_mps=0.021)),
            ("roll", *mutate("roll", base_rpy_rad=[math.radians(5.01), 0.0, 0.0])),
            ("pitch", *mutate("pitch", base_rpy_rad=[0.0, math.radians(-5.01), 0.0])),
            ("four_feet_above_min_force", *mutate("foot", foot_force_norms=[30.0, 1.0, 30.0, 30.0])),
            ("planar_drift", *mutate("drift", base_xyz=[1.03, 2.0, 0.35])),
            ("torque_clip_steps", *mutate("clip", torque_clip_joint_count=1)),
            ("nonfinite_values", *mutate("nan", applied_torque_max_ratio=float("nan"))),
        ]
        for check_name, name, rows in cases:
            with self.subTest(check=check_name):
                ac3 = self.analyze(rows, name=name)["ac3"]
                self.assertEqual(ac3["verdict"], "fail")
                self.assertFalse(ac3["checks"][check_name]["pass"])
                others = [k for k, v in ac3["checks"].items() if v["pass"] is False]
                self.assertEqual(others, [check_name])

    def test_late_missing_and_unevaluable_holds_fail(self):
        ac3 = self.analyze(stand_rows(fixed_from=10.04), name="late")["ac3"]
        self.assertFalse(ac3["checks"]["time_to_fixed_stand"]["pass"])
        rows = stand_rows(settle_until=61.0)
        ac3 = self.analyze(rows, name="never")["ac3"]
        self.assertEqual(ac3["verdict"], "fail")
        self.assertIn("FIXED_STAND was never reached", ac3["problems"])
        rows = stand_rows()
        del rows[2000]["torque_clip_joint_count"]
        ac3 = self.analyze(rows, name="noclip")["ac3"]
        self.assertIsNone(ac3["checks"]["torque_clip_steps"]["pass"])
        self.assertEqual(ac3["verdict"], "fail")
        ac3 = self.analyze(stand_rows(stance=False), name="off_as_on")["ac3"]
        self.assertIn("hold-on run rows are not stance_hold auto", ac3["problems"])
        legacy = stand_rows(stance=False)
        for row in legacy:
            for key in ("stance_hold", "stance_mode", "policy_owns_joints"):
                row.pop(key)
        ac3 = self.analyze(legacy, name="legacy_as_on", summary={"stance_hold": None})["ac3"]
        self.assertEqual(ac3["problems"], ["hold-on run has no stance fields", "FIXED_STAND was never reached"])
        ac3 = self.analyze(stand_rows(), name="wrong_case", summary={"case": "flat_nominal"})["ac3"]
        self.assertIn("hold-on run case is flat_nominal, not stand_probe", ac3["problems"])

    def test_early_end_or_hold_failure_fails_despite_quiet_rows(self):
        ac3 = self.analyze(stand_rows(), name="duration", summary={"status": "DURATION_REACHED"})["ac3"]
        self.assertEqual(ac3["verdict"], "pass", ac3["problems"])
        self.assertEqual(ac3["run_status"], "DURATION_REACHED")
        failure = {"type": "StanceHoldError", "message": "joint_pos is not finite", "step": 1500}
        cases = {
            "nonfinite": ({"status": "NONFINITE", "stance_hold": {"mode": "auto", "failure": failure}},
                          ["hold-on run status is NONFINITE", "recorded a stance hold failure"]),
            "terminated": ({"status": "TERMINATED"}, ["hold-on run status is TERMINATED"]),
            "wall_timeout": ({"status": "WALL_TIMEOUT"}, ["hold-on run status is WALL_TIMEOUT"]),
        }
        for name, (summary, messages) in cases.items():
            with self.subTest(case=name):
                ac3 = self.analyze(stand_rows(seconds=30.0), name=name, summary=summary)["ac3"]
                self.assertEqual(ac3["verdict"], "fail")
                self.assertTrue(all(v["pass"] for v in ac3["checks"].values()))
                for message in messages:
                    self.assertTrue(any(message in p for p in ac3["problems"]), ac3["problems"])
        on = write_run(self.root, "no_summary", stand_rows())
        (on / "returned_artifacts/runner_output/summary.json").unlink()
        ac3 = analyzer.analyze_stand(on, self.off, self.thresholds)["ac3"]
        self.assertIn("hold-on run has no summary.json", ac3["problems"])
        self.assertEqual(ac3["verdict"], "fail")

    def test_time_to_fixed_starts_at_the_zero_command_interval(self):
        rows = stand_rows(fixed_from=12.0)
        for row in rows[:300]:
            row["admitted_command"] = [0.2, 0.0, 0.0]
        ac3 = self.analyze(rows, name="moving_first")["ac3"]
        self.assertAlmostEqual(ac3["time_to_fixed_stand"]["zero_command_start_s"], 6.0)
        self.assertAlmostEqual(ac3["time_to_fixed_stand"]["seconds"], 6.0)
        self.assertTrue(ac3["checks"]["time_to_fixed_stand"]["pass"])

    def test_cli_writes_once_and_exit_code_follows_the_verdict(self):
        on = write_run(self.root, "cli_on", stand_rows())
        output = self.root / "report/ac3.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(analyzer.main(["stand", "--on", str(on), "--off", str(self.off), "--output", str(output)]), 0)
        report = json.loads(output.read_text())
        self.assertEqual(report["thresholds"]["sha256"], analyzer.FROZEN_THRESHOLDS_SHA256)
        self.assertEqual(report["ac3"]["verdict"], "pass")
        with self.assertRaisesRegex(SystemExit, "refusing to overwrite"):
            analyzer.main(["stand", "--on", str(on), "--off", str(self.off), "--output", str(output)])
        bad = write_run(self.root, "cli_bad", stand_rows(fixed_from=11.0))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(analyzer.main(["stand", "--on", str(bad), "--off", str(self.off)]), 1)
        with self.assertRaisesRegex(SystemExit, "no metrics.jsonl"):
            analyzer.main(["stand", "--on", str(self.root / "missing"), "--off", str(self.off)])


class EntrySmoothnessTests(unittest.TestCase):
    """AC7 (PRD D4) on synthetic rows. Entry row of stand_rows(): step 135, t0 = 2.72 s."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.thresholds = analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS)

    def ac7(self, rows, name, summary=None, case="stand_probe", mode="auto"):
        run = analyzer.load_run(write_run(self.root, name, rows, summary=summary, case=case, mode=mode))
        return analyzer.ac7(run, self.thresholds)

    def test_window_bounds_are_inclusive_and_use_absolute_values(self):
        cases = {
            # name: (row index, changes, expected verdict, failing check)
            "yaw_at_entry": (135, dict(yaw_rate_radps=0.1501), "fail", "yaw_rate"),
            "negative_yaw_at_end": (185, dict(yaw_rate_radps=-0.16), "fail", "yaw_rate"),
            "vertical_hop": (136, dict(base_linear_velocity_world=[0.0, 0.0, 0.21]), "fail", "vertical_speed"),
            "negative_vertical_at_end": (185, dict(base_linear_velocity_world=[0.0, 0.0, -0.0501]), "fail",
                                         "vertical_speed"),
            "at_limits": (150, dict(yaw_rate_radps=0.15, base_linear_velocity_world=[0.0, 0.0, 0.05]), "pass", None),
            "before_entry": (134, dict(yaw_rate_radps=0.5, base_linear_velocity_world=[0.0, 0.0, 0.3]), "pass", None),
            "after_window": (186, dict(yaw_rate_radps=0.5, base_linear_velocity_world=[0.0, 0.0, 0.3]), "pass", None),
            "horizontal_is_not_checked": (140, dict(base_linear_velocity_world=[0.4, 0.4, 0.0]), "pass", None),
        }
        for name, (index, changes, verdict, failing) in cases.items():
            with self.subTest(case=name):
                rows = stand_rows()
                rows[index].update(changes)
                result = self.ac7(rows, name)
                self.assertEqual(result["verdict"], verdict, result["problems"])
                window = result["entry_windows"][0]
                self.assertEqual((window["start_s"], window["end_s"], window["rows"]), (2.72, 3.72, 51))
                self.assertTrue(window["window_complete"])
                for check_name in ("yaw_rate", "vertical_speed"):
                    self.assertEqual(window[check_name]["pass"], check_name != failing)
                if failing:
                    self.assertEqual(len(result["problems"]), 1)
                    self.assertIn("entry at step 135", result["problems"][0])
                    self.assertIn("at step %d" % index, result["problems"][0])

    def test_missing_vertical_speed_in_the_window_is_not_evaluable(self):
        rows = stand_rows()
        del rows[160]["base_linear_velocity_world"]
        result = self.ac7(rows, "missing")
        self.assertEqual(result["verdict"], "fail")
        self.assertIsNone(result["entry_windows"][0]["vertical_speed"]["pass"])
        self.assertIn("not evaluable", result["problems"][0])
        rows = stand_rows()
        del rows[1000]["base_linear_velocity_world"]
        self.assertEqual(self.ac7(rows, "missing_outside")["verdict"], "pass")

    def test_every_entry_has_its_own_window(self):
        rows = move_rows() + [dict(row) for row in move_rows()]
        for k, row in enumerate(rows):
            row["step"] = k
            row["sim_time_s"] = round((k + 1) * DT, 6)
        # Second entry: row 273 + 70 = 343, t0 = 6.88 s; spike 0.5 s later.
        rows[343 + 25] = dict(rows[343 + 25], base_linear_velocity_world=[0.0, 0.0, 0.08])
        result = self.ac7(rows, "two_entries", case="flat_nominal")
        self.assertEqual([w["entry_step"] for w in result["entry_windows"]], [70, 343])
        self.assertEqual([w["vertical_speed"]["pass"] for w in result["entry_windows"]], [True, False])
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(len(result["problems"]), 1)
        self.assertIn("entry at step 343", result["problems"][0])
        self.assertEqual(result["entry_windows"][0]["modes"], ["STAND_TRANSITION"])

    def test_short_run_hold_off_and_no_entry(self):
        rows = stand_rows(seconds=3.0)
        result = self.ac7(rows, "short")
        self.assertEqual(result["verdict"], "pass")
        self.assertFalse(result["entry_windows"][0]["window_complete"])
        self.assertEqual(result["entry_windows"][0]["end_s"], 3.0)
        result = self.ac7(stand_rows(settle_until=61.0), "no_entry")
        self.assertEqual((result["verdict"], result["entry_windows"]), ("pass", []))
        self.assertIn("without an entry", result["note"])
        off = self.ac7(stand_rows(stance=False), "off", mode="off")
        self.assertEqual((off["verdict"], off["entry_windows"]), ("not_applicable", []))
        self.assertTrue(analyzer.ac7_ok(off))
        legacy = stand_rows(stance=False)
        for row in legacy:
            for key in ("stance_hold", "stance_mode", "policy_owns_joints", "base_linear_velocity_world"):
                row.pop(key)
        legacy_result = self.ac7(legacy, "legacy", summary={"stance_hold": None})
        self.assertEqual(legacy_result["verdict"], "not_applicable")
        self.assertEqual(legacy_result["stance_fields"], analyzer.NO_STANCE)

    def test_cli_exit_codes_include_ac7(self):
        off = write_run(self.root, "cli_off", stand_rows(stance=False), mode="off")
        hop = stand_rows()
        hop[136]["base_linear_velocity_world"] = [0.0, 0.0, 0.21]
        on = write_run(self.root, "cli_hop", hop)
        output = self.root / "report/hop.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(analyzer.main(["stand", "--on", str(on), "--off", str(off), "--output", str(output)]), 1)
        report = json.loads(output.read_text())
        self.assertEqual((report["ac3"]["verdict"], report["ac5"]["on"]["verdict"], report["ac7"]["on"]["verdict"]),
                         ("pass", "pass", "fail"))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(analyzer.main(["run", str(on)]), 1)
            self.assertEqual(analyzer.main(["run", str(off)]), 0)
            self.assertEqual(analyzer.main(["run", str(write_run(self.root, "cli_quiet", stand_rows()))]), 0)

    def test_recorded_c1_hop_fails_ac7(self):
        if not (C1_HOLD_AUTO_RUN / "returned_artifacts/runner_output/metrics.jsonl").is_file():
            self.skipTest("local C1 run artifacts are absent")
        result = analyzer.ac7(analyzer.load_run(C1_HOLD_AUTO_RUN), self.thresholds)
        self.assertEqual(result["verdict"], "fail")
        window = result["entry_windows"][0]
        self.assertEqual(window["entry_step"], 19)
        self.assertAlmostEqual(window["start_s"], 0.4, places=6)
        self.assertEqual((window["rows"], window["modes"]), (51, ["STAND_TRANSITION"]))
        self.assertAlmostEqual(window["max_abs_yaw_rate_radps"], 0.302, places=3)
        self.assertAlmostEqual(window["max_abs_vertical_speed_mps"], 0.210, places=3)
        self.assertEqual((window["max_abs_yaw_rate_step"], window["max_abs_vertical_speed_step"]), (20, 20))
        self.assertEqual(len(result["entry_windows"]), 1)
        # No restart inside the window: the D7 amendment gives the same verdict.
        self.assertEqual((window["amended"]["window_end"], window["amended"]["rows"]), ("window_s", 51))
        self.assertEqual(result["as_frozen_before_results"]["verdict"], "fail")


    # ---- PRD D7 restart window (post-result amendment) ----
    # stand_rows(): entry row index 135 (step 135, t0 = 2.72 s); the full window ends at row 185 (3.72 s).
    def with_modes(self, rows, start, modes):
        for offset, mode in enumerate(modes):
            rows[start + offset].update(stance_mode=mode, policy_owns_joints=mode in ("RL", "REJOIN"))
        return rows

    def test_restart_inside_the_window_truncates_the_amended_window(self):
        rows = self.with_modes(stand_rows(), 145, ["REJOIN"] * 13 + ["RL"] * 40)
        rows[150]["yaw_rate_radps"] = -0.174  # inside REJOIN, after the restart row 145
        rows[152]["base_linear_velocity_world"] = [0.0, 0.0, 0.06]
        result = self.ac7(rows, "restart")
        self.assertEqual(result["verdict"], "pass", result["problems"])
        self.assertEqual(result["verdict_rule"], "amended_end_at_restart")
        self.assertIn("post-result", result["window_rule"])
        self.assertIn("PRD D7", result["window_rule"])
        self.assertEqual(result["post_result_amendment"]["decision"], "PRD D7")
        self.assertIs(result["limits"]["end_at_restart"], True)
        self.assertEqual(result["windows_ended_at_restart"], 1)
        frozen = result["as_frozen_before_results"]
        self.assertEqual(frozen["verdict"], "fail")
        self.assertEqual(len(frozen["problems"]), 2)
        self.assertIn("|yaw rate| 0.1740 rad/s at step 150", frozen["problems"][0])
        self.assertIn("as frozen before the results", frozen["window_rule"])
        window = result["entry_windows"][0]
        # Top-level window fields stay the full window.
        self.assertEqual((window["start_s"], window["end_s"], window["rows"]), (2.72, 3.72, 51))
        self.assertAlmostEqual(window["max_abs_yaw_rate_radps"], 0.174)
        self.assertEqual((window["yaw_rate"]["pass"], window["vertical_speed"]["pass"]), (False, False))
        self.assertEqual(window["modes"], ["REJOIN", "RL", "STAND_TRANSITION"])
        amended = window["amended"]
        self.assertEqual((amended["window_end"], amended["restart_step"], amended["restart_s"], amended["restart_mode"]),
                         ("restart", 145, 2.92, "REJOIN"))
        self.assertEqual((amended["end_s"], amended["rows"], amended["modes"]), (2.9, 10, ["STAND_TRANSITION"]))
        self.assertTrue(amended["window_complete"])
        self.assertEqual((amended["max_abs_yaw_rate_radps"], amended["max_abs_vertical_speed_mps"]), (0.01, 0.002))
        self.assertEqual((amended["yaw_rate"]["pass"], amended["vertical_speed"]["pass"]), (True, True))
        # A spike on the restart row itself is excluded; one row earlier counts.
        rows[145]["yaw_rate_radps"] = 0.3
        self.assertEqual(self.ac7(rows, "restart_row_spike")["verdict"], "pass")
        rows[144]["yaw_rate_radps"] = 0.16
        result = self.ac7(rows, "before_restart_spike")
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(len(result["problems"]), 1)
        self.assertIn("at step 144 exceeds 0.15 (window ends before the restart at step 145)", result["problems"][0])

    def test_restart_after_the_window_changes_nothing(self):
        rows = self.with_modes(stand_rows(), 186, ["REJOIN"] * 13)
        rows[160]["yaw_rate_radps"] = 0.2
        result = self.ac7(rows, "late_restart")
        window = result["entry_windows"][0]
        amended = window["amended"]
        self.assertEqual((amended["window_end"], amended["restart_step"], amended["restart_s"], amended["restart_mode"]),
                         ("window_s", None, None, None))
        for key in ("end_s", "rows", "modes", "max_abs_yaw_rate_radps", "max_abs_yaw_rate_step",
                    "max_abs_vertical_speed_mps", "max_abs_vertical_speed_step", "yaw_rate", "vertical_speed",
                    "window_complete"):
            self.assertEqual(amended[key], window[key], key)
        self.assertEqual((result["verdict"], result["as_frozen_before_results"]["verdict"]), ("fail", "fail"))
        self.assertEqual(result["problems"], result["as_frozen_before_results"]["problems"])
        self.assertEqual(result["windows_ended_at_restart"], 0)

    def test_direct_exit_to_rl_is_a_restart(self):
        rows = self.with_modes(stand_rows(), 160, ["RL"] * 30)
        rows[170]["yaw_rate_radps"] = 0.25
        result = self.ac7(rows, "direct_exit")
        amended = result["entry_windows"][0]["amended"]
        self.assertEqual((amended["window_end"], amended["restart_step"], amended["restart_mode"], amended["rows"]),
                         ("restart", 160, "RL", 25))
        self.assertEqual((result["verdict"], result["as_frozen_before_results"]["verdict"]), ("pass", "fail"))

    def test_fixed_stand_inside_the_window_is_not_a_restart(self):
        rows = stand_rows(fixed_from=3.2)  # FIXED_STAND from row 159, inside the 1.0 s window
        rows[170]["yaw_rate_radps"] = 0.2
        result = self.ac7(rows, "fixed_inside")
        window = result["entry_windows"][0]
        self.assertEqual(window["modes"], ["FIXED_STAND", "STAND_TRANSITION"])
        self.assertEqual((window["amended"]["window_end"], window["amended"]["rows"]), ("window_s", 51))
        self.assertEqual((result["verdict"], result["as_frozen_before_results"]["verdict"]), ("fail", "fail"))

    def test_as_frozen_fields_for_hold_off_and_no_entry_runs(self):
        off = self.ac7(stand_rows(stance=False), "off_fields", mode="off")
        self.assertEqual(off["as_frozen_before_results"]["verdict"], "not_applicable")
        self.assertTrue(analyzer.ac7_ok(off["as_frozen_before_results"]))
        self.assertEqual(off["verdict_rule"], "amended_end_at_restart")
        none = self.ac7(stand_rows(settle_until=61.0), "no_entry_fields")
        self.assertEqual((none["verdict"], none["as_frozen_before_results"]["verdict"]), ("pass", "pass"))
        self.assertEqual(none["windows_ended_at_restart"], 0)

    def test_superseded_thresholds_reproduce_the_full_window_verdict(self):
        """Loading the pre-D7 file (allowed explicitly) gives the old verdict and no amended window."""
        rows = self.with_modes(stand_rows(), 145, ["REJOIN"] * 13 + ["RL"] * 40)
        rows[150]["yaw_rate_radps"] = -0.174
        run = analyzer.load_run(write_run(self.root, "old_rule", rows))
        old = analyzer.ac7(run, analyzer.load_thresholds(D6_THRESHOLDS, allow_unfrozen=True))
        self.assertEqual((old["verdict"], old["verdict_rule"], old["limits"]["end_at_restart"]),
                         ("fail", "full_window", False))
        self.assertNotIn("amended", old["entry_windows"][0])
        self.assertIsNone(old["windows_ended_at_restart"])
        self.assertIsNone(old["post_result_amendment"])
        self.assertEqual(old["problems"], old["as_frozen_before_results"]["problems"])
        new = analyzer.ac7(run, self.thresholds)
        self.assertEqual(new["as_frozen_before_results"]["problems"], old["problems"])
        self.assertEqual({k: v for k, v in new["entry_windows"][0].items() if k != "amended"},
                         old["entry_windows"][0])

    def test_recorded_c2_e06_passes_amended_and_fails_as_frozen(self):
        if not (C2_E06_RUN / "returned_artifacts/runner_output/metrics.jsonl").is_file():
            self.skipTest("local C2 episode 6 artifacts are absent")
        result = analyzer.ac7(analyzer.load_run(C2_E06_RUN), self.thresholds)
        self.assertEqual(result["verdict"], "pass", result["problems"])
        frozen = result["as_frozen_before_results"]
        self.assertEqual(frozen["verdict"], "fail")
        self.assertEqual(len(frozen["problems"]), 1)
        self.assertIn("entry at step 332: |yaw rate| 0.1744 rad/s at step 345", frozen["problems"][0])
        window = next(w for w in result["entry_windows"] if w["entry_step"] == 332)
        self.assertAlmostEqual(window["max_abs_yaw_rate_radps"], 0.1744, places=4)
        amended = window["amended"]
        self.assertEqual((amended["window_end"], amended["restart_step"], amended["restart_mode"], amended["rows"]),
                         ("restart", 341, "REJOIN", 9))
        self.assertLessEqual(amended["max_abs_yaw_rate_radps"], 0.15)
        self.assertLessEqual(amended["max_abs_vertical_speed_mps"], 0.05)


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.thresholds = analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS)

    def ac5(self, rows, name, summary=None):
        run = analyzer.load_run(write_run(self.root, name, rows, summary=summary, case="flat_nominal"))
        return analyzer.ac5(run, self.thresholds)

    def test_entry_and_rejoin_windows(self):
        result = self.ac5(move_rows(), "move")
        self.assertEqual(result["verdict"], "pass", result["problems"])
        self.assertEqual(result["entries"], [{"step": 70, "sim_time_s": 1.42}])
        self.assertEqual(result["rejoins"][0]["first_step"], 230)
        self.assertEqual(result["rejoins"][0]["rows"], 13)
        self.assertEqual(result["entry_or_rejoin_steps"], [70, 71] + list(range(230, 245)))
        self.assertAlmostEqual(result["max_abs_pitch_deg_during_rejoin"], math.degrees(0.03))
        intervals = analyzer.zero_command_intervals(analyzer.load_run(self.root / "move"), self.thresholds)
        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0]["start_s"], 1.0)
        self.assertAlmostEqual(intervals[0]["time_to_fixed_stand_s"], 2.42)

    def test_ac5_failures(self):
        cases = {}
        rows = move_rows()
        rows[71]["torque_clip_joint_count"] = 2
        cases["clip_entry_next_row"] = (rows, None, "torque clip at entry or rejoin steps [71]")
        rows = move_rows()
        rows[244]["torque_clip_joint_count"] = 1
        cases["clip_after_rejoin"] = (rows, None, "torque clip at entry or rejoin steps [244]")
        rows = move_rows()
        rows[235]["base_rpy_rad"] = [math.radians(10.5), 0.0, 0.0]
        cases["rejoin_roll"] = (rows, None, "roll 10.500 deg during REJOIN")
        rows = move_rows()
        rows[240]["base_rpy_rad"] = [0.0, math.radians(-10.2), 0.0]
        cases["rejoin_pitch"] = (rows, None, "pitch 10.200 deg during REJOIN")
        rows = move_rows()
        rows[10]["nonfoot_force_substep_max_n"] = 5.0
        cases["nonfoot_at_guard"] = (rows, None, "reaches the 5.0 N guard")
        cases["nonfoot_event"] = (move_rows(), {"nonfoot_contact_events_over_threshold": [{"force_n": 6.0}]},
                                  "events 1")
        rows = move_rows()
        del rows[70]["torque_clip_joint_count"]
        cases["missing_clip_field"] = (rows, None, "torque clip fields are missing")
        for name, (rows, summary, message) in cases.items():
            with self.subTest(case=name):
                result = self.ac5(rows, name, summary)
                self.assertEqual(result["verdict"], "fail")
                self.assertTrue(any(message in problem for problem in result["problems"]), result["problems"])

    def test_clip_outside_windows_and_estimate_are_reported_only(self):
        rows = move_rows()
        rows[100]["torque_clip_joint_count"] = 1
        rows[70]["delayed_target_torque_max_ratio_estimate"] = 1.2
        rows[4]["nonfoot_force_max_n"] = 4.99
        result = self.ac5(rows, "outside")
        self.assertEqual(result["verdict"], "pass", result["problems"])
        self.assertEqual(result["delayed_target_estimated_clip_steps"], [70])
        self.assertAlmostEqual(result["max_nonfoot_force_n"], 4.99)


class OldRunTests(unittest.TestCase):
    def test_runs_without_stance_fields_are_reported_as_hold_off(self):
        thresholds = analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS)
        with tempfile.TemporaryDirectory() as tmp:
            rows = stand_rows(seconds=3.0, stance=False)
            for row in rows:
                for key in ("stance_hold", "stance_mode", "policy_owns_joints", "applied_torque_max_ratio",
                            "torque_clip_joint_count"):
                    row.pop(key)
            run = write_run(tmp, "legacy", rows, summary={"stance_hold": None})
            payload = analyzer.analyze_runs([run], thresholds)
        ac5 = payload["runs"][0]["ac5"]
        self.assertEqual(ac5["stance_fields"], analyzer.NO_STANCE)
        self.assertEqual((ac5["verdict"], ac5["entries"], ac5["segments"]), ("pass", [], []))
        self.assertIsNone(ac5["stance_hold_mode"])
        self.assertEqual(len(payload["runs"][0]["zero_command_intervals"]), 1)

    def test_recorded_legacy_runs_load(self):
        runs = [path for path in (OLD_STAND_RUN, OLD_TWO_GOAL_RUN)
                if (path / "returned_artifacts/runner_output/metrics.jsonl").is_file()]
        if not runs:
            self.skipTest("local legacy run artifacts are absent")
        payload = analyzer.analyze_runs(runs, analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS))
        for item in payload["runs"]:
            self.assertEqual(item["ac5"]["stance_fields"], analyzer.NO_STANCE)
            self.assertEqual(item["ac5"]["entries"], [])
            self.assertEqual(item["ac7"]["verdict"], "not_applicable")
            self.assertTrue(item["zero_command_intervals"])
        json.dumps(payload, allow_nan=False)


# ---- AC8 scripted walk ---------------------------------------------------------
FROZEN_SCRIPT_SHA = analyzer.sha256_file(D5_SCRIPT)
WALK_STARTS = (4.0, 12.0)
WALK_STOPS = (7.0, 14.5)


def walk_command(now):
    """The D5 script at loop-top time now (float)."""
    if 4.0 - 1e-4 <= now < 7.0 - 1e-4 or 12.0 - 1e-4 <= now < 14.5 - 1e-4:
        return [0.6, 0.0, 0.0]
    return [0.0, 0.0, 0.0]


def segment_at(now):
    return sum(1 for start in (4.0, 7.0, 12.0, 14.5) if start <= now + 1e-4)


def walk_rows(stance=True, seconds=21.3, entry_delay=(0.4, 0.8, 0.8), entry_yaw=0.02, start_pitch_deg=2.0,
              speed=0.6, rejoin_rows=13):
    """Synthetic scripted-walk rows: stand, walk, stop, walk, stop. Hold-on rows follow a simple FSM timeline."""
    rows = []
    x = -1.6
    zero_starts = (0.0,) + WALK_STOPS
    entries = [start + delay for start, delay in zip(zero_starts, entry_delay)]
    v = 0.0
    for k in range(int(round(seconds / DT))):
        now = round(k * DT, 9)
        t = round((k + 1) * DT, 9)
        command = walk_command(now)
        moving = command[0] > 0.0
        v = min(speed, v + speed * DT / 0.5) if moving else max(0.0, v - speed * DT / 0.4)
        x += v * DT
        yaw_rate = 0.02 if k % 2 else -0.02
        pitch = math.radians(1.0)
        if any(start < t <= start + 1.0 for start in WALK_STARTS):
            pitch = math.radians(start_pitch_deg)
        if stance:
            mode = "RL"
            zero_index = max(i for i, start in enumerate(zero_starts) if start <= now + 1e-4) if not moving else None
            if moving:
                start = max(s for s in WALK_STARTS if s <= now + 1e-4)
                previous_zero = zero_starts.index(max(z for z in zero_starts if z < start))
                had_hold = entries[previous_zero] + 2.0 <= start + 1e-9 or entries[previous_zero] <= start
                if had_hold and t <= start + rejoin_rows * DT + 1e-9:
                    mode = "REJOIN"
            else:
                entry = entries[zero_index]
                if t < entry - 1e-9:
                    mode = "STAND_SETTLING"
                elif t < entry + 2.0 - 1e-9:
                    mode = "STAND_TRANSITION"
                    if t < entry + 1.0 + 1e-9:
                        yaw_rate = entry_yaw if k % 2 else -entry_yaw
                else:
                    mode = "FIXED_STAND"
        still = not moving and v == 0.0
        row = {
            "step": k,
            "sim_time_s": t,
            "base_xyz": [x, -4.54, 1.91],
            "base_rpy_rad": [0.01, pitch, 0.057],
            "horizontal_speed_mps": v,
            "base_linear_velocity_world": [v, 0.0, 0.004 if k % 2 else -0.004],
            "yaw_rate_radps": yaw_rate if (not moving or stance) else 0.05,
            "admitted_command": command,
            "foot_force_norms": [30.0, 30.0, 30.0, 30.0] if still else [30.0, 2.0, 2.0, 30.0],
            "nonfoot_force_max_n": 0.0,
            "nonfoot_force_substep_max_n": 0.0,
            "applied_torque_max_ratio": 0.3,
            "torque_clip_joint_count": 0,
            "script_segment": segment_at(now),
        }
        if stance:
            row.update({"stance_hold": "auto", "stance_mode": mode, "stance_reason": "x",
                        "policy_owns_joints": mode in ("RL", "STAND_SETTLING"),
                        "delayed_target_torque_max_ratio_estimate": 0.3})
        else:
            row.update({"stance_hold": "off", "stance_mode": "OFF", "policy_owns_joints": True})
        rows.append(row)
    return rows


def walk_summary(mode="auto", entry_kd="ramp", **changes):
    summary = {
        "case": "scripted_walk", "status": "EXTERNAL_EPISODE_FINISHED", "max_nonfoot_force_n": 0.0,
        "nonfoot_contact_events_over_threshold": [], "autoresets": 0, "pose_injection_events": 0,
        "reset_attempts": 0, "pose_write_attempts": 0, "case_failed": False,
        "contact_guard": {"failed": False, "failure": None},
        "stance_hold": {"mode": mode, "entry_kd": entry_kd, "failure": None, "gain_writes": 30, "fsm": None},
        "scripted_walk": {"command_script": {"sha256": FROZEN_SCRIPT_SHA}},
    }
    summary.update(changes)
    return summary


def write_walk_run(root, name, rows, summary):
    out = Path(root) / name / "returned_artifacts/runner_output"
    out.mkdir(parents=True)
    (out / "metrics.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    (out / "summary.json").write_text(json.dumps(summary))
    (out / "scripted_walk_setup.json").write_text(json.dumps({"command_script": {"sha256": FROZEN_SCRIPT_SHA}}))
    return out.parents[1]


class WalkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.thresholds = analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS)
        self.off = write_walk_run(self.root, "off", walk_rows(stance=False, start_pitch_deg=1.5),
                                  walk_summary(mode="off"))

    def on(self, name, rows=None, entry_kd="ramp", summary=None, **row_options):
        return write_walk_run(self.root, name, rows if rows is not None else walk_rows(**row_options),
                              summary if summary is not None else walk_summary(entry_kd=entry_kd))

    def analyze(self, *ons, off=None):
        return analyzer.analyze_walk(off or self.off, list(ons), self.thresholds)

    def test_quiet_walk_passes_and_reports_every_phase(self):
        result = self.analyze(self.on("ramp"))
        off, on = result["runs"]
        self.assertEqual((off["role"], on["role"]), ("off", "on"))
        self.assertEqual(off["baseline_problems"], [])
        self.assertEqual(on["ac8"]["verdict"], "pass", on["ac8"]["problems"])
        self.assertEqual((on["ac5"]["verdict"], on["ac7"]["verdict"]), ("pass", "pass"))
        self.assertEqual(off["ac7"]["verdict"], "not_applicable")
        self.assertEqual(on["entry_kd"], "ramp")
        self.assertEqual([p["phase"] for p in on["zero_phases"]], ["stand_initial", "stop_1", "stop_2"])
        self.assertEqual([p["command_step_s"] for p in on["zero_phases"]], [0.0, 7.0, 14.5])
        for phase, want in zip(on["zero_phases"], (2.4, 2.8, 2.8)):
            self.assertAlmostEqual(phase["time_to_fixed_stand_s"], want, places=6)
            self.assertTrue(phase["fixed_stand_reached"])
            self.assertEqual(phase["mode_at_end"], "FIXED_STAND")
        self.assertEqual(on["zero_phases"][-1]["end_s"], 20.0)
        # Speed falls 0.03 m/s per step from 0.6: the first row at or below 0.05 m/s is 7.38 s.
        self.assertAlmostEqual(on["zero_phases"][1]["time_to_still_s"], 0.38, places=6)
        self.assertAlmostEqual(on["zero_phases"][1]["still_confirmed_s"], 7.88, places=6)
        self.assertEqual(on["zero_phases"][0]["time_to_still_s"], 0.02)
        tail = on["zero_phases"][1]["tail"]
        self.assertEqual((tail["start_s"], tail["end_s"], tail["rows"]), (10.0, 12.0, 101))
        self.assertEqual(tail["planar_drift_m"], 0.0)
        self.assertEqual(off["zero_phases"][1]["time_to_fixed_stand_s"], None)
        self.assertIsNone(off["zero_phases"][1]["fixed_stand_reached"])
        starts = on["starts"]
        self.assertEqual([s["command_step_s"] for s in starts], [4.0, 12.0])
        self.assertEqual([(s["window_start_s"], s["window_end_s"], s["window_rows"]) for s in starts],
                         [(4.02, 5.0, 50), (12.02, 13.0, 50)])
        self.assertTrue(all(s["window_complete"] for s in starts))
        self.assertAlmostEqual(starts[0]["max_abs_pitch_deg"], 2.0)
        self.assertEqual(starts[0]["modes"], ["REJOIN", "RL"])
        self.assertAlmostEqual(starts[0]["max_abs_vertical_speed_mps"], 0.004)
        self.assertEqual(starts[0]["min_base_height_change_m"], 0.0)
        self.assertAlmostEqual(starts[0]["walk_phase_distance_m"], 0.6 * 3.0 - 0.15, delta=0.02)
        self.assertAlmostEqual(starts[1]["walk_phase_distance_m"], 0.6 * 2.5 - 0.15, delta=0.02)
        self.assertAlmostEqual(on["planar_travel_m"], off["planar_travel_m"])
        self.assertEqual(on["zero_phases"][-1]["phase"], "stop_2")
        c = on["ac8"]["c_starts"]
        self.assertAlmostEqual(c[0]["pitch_excess_over_off_deg"], 0.5)
        self.assertEqual(result["selection"]["selected"]["run"], on["run"])
        self.assertIsNone(result["selection"]["note"])
        json.dumps(result, allow_nan=False)

    def test_selection_picks_the_lowest_entry_yaw_among_passing_variants(self):
        ramp = self.on("ramp", entry_kd="ramp", entry_yaw=0.12)
        step1 = self.on("step1", entry_kd="step1", entry_yaw=0.05)
        # Lowest yaw, but its start pitch is 3.6 deg above the baseline: fails AC8 c.
        step2p5 = self.on("step2p5", entry_kd="step2p5", entry_yaw=0.01, start_pitch_deg=5.1)
        result = self.analyze(ramp, step1, step2p5)
        candidates = result["selection"]["candidates"]
        self.assertEqual([c["entry_kd"] for c in candidates], ["ramp", "step1", "step2p5"])
        self.assertEqual([c["eligible"] for c in candidates], [True, True, False])
        self.assertEqual([c["max_entry_window_abs_yaw_rate_radps"] for c in candidates], [0.12, 0.05, 0.01])
        self.assertEqual(result["selection"]["selected"]["entry_kd"], "step1")
        failing = result["runs"][3]["ac8"]
        self.assertEqual(failing["verdict"], "fail")
        self.assertTrue(any("above the hold-off" in p for p in failing["problems"]), failing["problems"])
        # Ties go to the earlier --on argument.
        again = self.analyze(self.on("tie_a", entry_kd="step1", entry_yaw=0.05), step1)
        self.assertEqual(again["selection"]["selected"]["run"], str(self.root / "tie_a"))
        self.assertIn("tie", again["selection"]["note"])

    def test_no_selection_when_every_variant_fails_or_the_baseline_is_invalid(self):
        noisy = self.on("noisy", entry_yaw=0.2)
        result = self.analyze(noisy)
        self.assertIsNone(result["selection"]["selected"])
        self.assertIn("no hold-on run passes", result["selection"]["note"])
        b = result["runs"][1]["ac8"]["b_entry_windows"]
        self.assertEqual((b["verdict"], b["entry_windows"]), ("fail", 3))
        self.assertTrue(any(p.startswith("b: entry at step") for p in result["runs"][1]["ac8"]["problems"]))
        broken_off = write_walk_run(self.root, "broken_off", walk_rows(stance=False, seconds=15.0),
                                    walk_summary(mode="off", status="TERMINATED"))
        result = self.analyze(self.on("fine"), off=broken_off)
        self.assertIsNone(result["selection"]["selected"])
        self.assertIn("baseline is not valid", result["selection"]["note"])
        problems = result["runs"][0]["baseline_problems"]
        self.assertTrue(any("before the finish request" in p for p in problems), problems)
        self.assertTrue(any("status is TERMINATED" in p for p in problems), problems)
        with self.assertRaisesRegex(analyzer.AnalysisError, "is a stance_hold auto run"):
            self.analyze(self.on("fine2"), off=self.on("on_as_off"))

    def test_crossfade_variants_and_the_landing_grace_need_no_analyzer_change(self):
        """PRD D6: the xfade names pass through, and the grace still leaves AC8 a margin."""
        # Landing grace 1.0 s + settle dwell 0.25 s on a 0.02 s grid: entry 1.28 s,
        # FIXED_STAND 3.28 s, before the 4.0 s start of the first walk phase.
        one = self.on("xfade1s", entry_kd="xfade1s", entry_delay=(1.28, 0.8, 0.8), entry_yaw=0.09)
        two = self.on("xfade2s", entry_kd="xfade2s", entry_delay=(1.28, 0.8, 0.8), entry_yaw=0.04)
        result = self.analyze(one, two)
        for report in result["runs"][1:]:
            self.assertEqual(report["ac8"]["verdict"], "pass", report["ac8"]["problems"])
            self.assertEqual((report["ac5"]["verdict"], report["ac7"]["verdict"]), ("pass", "pass"))
            self.assertEqual([c["pass"] for c in report["ac8"]["a_fixed_stand"]], [True, True, True])
            self.assertAlmostEqual(report["zero_phases"][0]["first_transition_s"], 1.28, places=6)
            self.assertAlmostEqual(report["zero_phases"][0]["time_to_fixed_stand_s"], 3.28, places=6)
            self.assertEqual(report["ac8"]["b_entry_windows"]["entry_windows"], 3)
        candidates = result["selection"]["candidates"]
        self.assertEqual([c["entry_kd"] for c in candidates], ["xfade1s", "xfade2s"])
        self.assertEqual([c["eligible"] for c in candidates], [True, True])
        self.assertEqual([c["max_entry_window_abs_yaw_rate_radps"] for c in candidates], [0.09, 0.04])
        self.assertEqual(result["selection"]["selected"]["entry_kd"], "xfade2s")
        self.assertIsNone(result["selection"]["note"])
        # A settle that keeps blocking past ~1.7 s pushes FIXED_STAND beyond the
        # 4.0 s deadline and AC8 a fails; the margin after the grace is about 0.7 s.
        blocked = self.on("blocked", entry_kd="xfade1s", entry_delay=(2.1, 0.8, 0.8))
        ac8 = self.analyze(blocked)["runs"][1]["ac8"]
        self.assertEqual([c["pass"] for c in ac8["a_fixed_stand"]], [False, True, True])
        self.assertTrue(any("a: phase stand_initial did not reach FIXED_STAND" in p for p in ac8["problems"]),
                        ac8["problems"])

    def test_b_keeps_the_full_window_when_ac7_ends_at_a_restart(self):
        """PRD D7 applies to AC7 only: AC8 b and the D5 selection value use the full 1.0 s entry window."""
        # stop_1 entry at 11.5 s; the walk_2 command at 12.0 s starts REJOIN inside that entry's window.
        rows = walk_rows(entry_delay=(0.4, 4.5, 0.8))
        spike = next(i for i, row in enumerate(rows) if abs(row["sim_time_s"] - 12.2) < 1e-6)
        self.assertEqual(rows[spike]["stance_mode"], "REJOIN")
        rows[spike]["yaw_rate_radps"] = 0.3
        report = self.analyze(self.on("restart", rows=rows))["runs"][1]
        ac7 = report["ac7"]
        self.assertEqual(ac7["verdict"], "pass", ac7["problems"])
        self.assertEqual(ac7["as_frozen_before_results"]["verdict"], "fail")
        window = ac7["entry_windows"][1]
        self.assertEqual((window["amended"]["window_end"], window["amended"]["restart_mode"]), ("restart", "REJOIN"))
        self.assertAlmostEqual(window["amended"]["restart_s"], 12.02, places=6)
        b = report["ac8"]["b_entry_windows"]
        self.assertEqual((b["verdict"], b["entry_windows"]), ("fail", 3))
        self.assertEqual(b["problems"], ac7["as_frozen_before_results"]["problems"])
        self.assertIn("full window", b["window_rule"])
        self.assertTrue(any(p.startswith("b: entry at step") and "0.3000" in p for p in report["ac8"]["problems"]))
        self.assertEqual(report["max_entry_window_abs_yaw_rate_radps"], 0.3)

    def test_a_requires_fixed_stand_in_every_zero_phase(self):
        # Entry 3.1 s after the 7 s stop: FIXED_STAND would start at 12.1 s, after the 12 s start.
        late = self.on("late", entry_delay=(0.4, 3.1, 0.8))
        ac8 = self.analyze(late)["runs"][1]["ac8"]
        self.assertEqual(ac8["verdict"], "fail")
        self.assertEqual([c["pass"] for c in ac8["a_fixed_stand"]], [True, False, True])
        self.assertTrue(any("a: phase stop_1 did not reach FIXED_STAND" in p for p in ac8["problems"]))
        # Last phase: FIXED_STAND at 20.3 s is after the 20 s finish request.
        tail_late = self.on("tail_late", entry_delay=(0.4, 0.8, 3.8))
        ac8 = self.analyze(tail_late)["runs"][1]["ac8"]
        self.assertEqual([c["pass"] for c in ac8["a_fixed_stand"]], [True, True, False])

    def test_c_start_window_limits_and_bounds(self):
        def mutate(name, index, **changes):
            rows = walk_rows()
            rows[index].update(changes)
            return self.on(name, rows=rows)

        cases = {
            # row 200 is the first row under the 4.0 s command (t = 4.02); row 249 ends the window (t = 5.0).
            "nonfoot": (mutate("nonfoot", 200, nonfoot_force_substep_max_n=5.0), "non-foot force 5.000"),
            "roll": (mutate("roll", 249, base_rpy_rad=[math.radians(10.5), 0.0, 0.0]), "|roll| 10.500"),
            "pitch": (mutate("pitch", 620, base_rpy_rad=[0.0, math.radians(-10.2), 0.0]), "|pitch| 10.200"),
        }
        for name, (run, message) in cases.items():
            with self.subTest(case=name):
                ac8 = self.analyze(run)["runs"][1]["ac8"]
                self.assertEqual(ac8["verdict"], "fail")
                self.assertTrue(any(message in p for p in ac8["problems"]), ac8["problems"])
        outside = {
            "before_window": 199,  # t = 4.0, the command step row itself
            "after_window": 250,   # t = 5.02
        }
        for name, index in outside.items():
            with self.subTest(case=name):
                run = mutate(name, index, nonfoot_force_substep_max_n=9.0,
                             base_rpy_rad=[math.radians(12.0), math.radians(12.0), 0.0])
                ac8 = self.analyze(run)["runs"][1]["ac8"]
                self.assertEqual(ac8["c_starts"][0]["pass"], True, ac8["c_starts"][0])
        event = self.on("event", summary=walk_summary(nonfoot_contact_events_over_threshold=[
            {"sim_time_s": 12.5, "force_n": 6.0}, "not-a-dict"]))
        ac8 = self.analyze(event)["runs"][1]["ac8"]
        self.assertEqual([c["pass"] for c in ac8["c_starts"]], [True, False])
        # AC5 sees the same over-threshold event.
        self.assertEqual(self.analyze(event)["runs"][1]["ac5"]["verdict"], "fail")

    def test_d_run_integrity_and_travel(self):
        cases = {
            "status": (walk_summary(status="NONFINITE"), "status is NONFINITE"),
            "case": (walk_summary(case="stand_probe"), "case is stand_probe"),
            "reset": (walk_summary(reset_attempts=1), "reset_attempts is 1"),
            "pose": (walk_summary(pose_write_attempts=2), "pose_write_attempts is 2"),
            "missing_counter": ({k: v for k, v in walk_summary().items() if k != "autoresets"},
                                "autoresets is missing"),
            "case_failed": (walk_summary(case_failed=True), "case_failed is True"),
            "guard": (walk_summary(contact_guard={"failed": True, "failure": {"body": "TORSO"}}),
                      "contact guard failed"),
            "hold_failure": (walk_summary(stance_hold={"mode": "auto", "entry_kd": "ramp",
                                                       "failure": {"message": "nan"}}), "stance hold failure"),
            "duration_is_fine": (walk_summary(status="DURATION_REACHED"), None),
        }
        for name, (summary, message) in cases.items():
            with self.subTest(case=name):
                ac8 = self.analyze(self.on(name, summary=summary))["runs"][1]["ac8"]
                if message is None:
                    self.assertEqual(ac8["verdict"], "pass", ac8["problems"])
                else:
                    self.assertEqual(ac8["verdict"], "fail")
                    self.assertTrue(any(p.startswith("d: ") and message in p for p in ac8["problems"]),
                                    ac8["problems"])
        rows = walk_rows()
        rows[900]["applied_torque_max_ratio"] = float("nan")
        ac8 = self.analyze(self.on("nan", rows=rows))["runs"][1]["ac8"]
        self.assertTrue(any("non-finite" in p for p in ac8["problems"]))
        other = self.on("other_script")
        (other / "returned_artifacts/runner_output/scripted_walk_setup.json").write_text(
            json.dumps({"command_script": {"sha256": "f" * 64}}))
        ac8 = self.analyze(other)["runs"][1]["ac8"]
        self.assertTrue(any("is not the frozen" in p for p in ac8["problems"]))
        short = self.on("short_walk", speed=0.45)
        ac8 = self.analyze(short)["runs"][1]["ac8"]
        self.assertEqual(ac8["verdict"], "fail")
        self.assertGreater(ac8["d_run"]["relative_difference"], 0.2)
        self.assertTrue(any("planar travel" in p for p in ac8["problems"]))
        near = self.on("near_walk", speed=0.52)
        ac8 = self.analyze(near)["runs"][1]["ac8"]
        self.assertLess(ac8["d_run"]["relative_difference"], 0.2)
        self.assertEqual(ac8["verdict"], "pass", ac8["problems"])

    def test_phase_structure_problems(self):
        ended = self.on("ended", seconds=19.0)
        ac8 = self.analyze(ended)["runs"][1]["ac8"]
        self.assertTrue(any("before the finish request" in p for p in ac8["problems"]), ac8["problems"])
        rows = walk_rows()
        for row in rows[200:205]:
            row["admitted_command"] = [0.0, 0.0, 0.0]
        shifted = self.analyze(self.on("shifted", rows=rows))["runs"][1]
        self.assertTrue(any("command step at 4.1000 s" in p for p in shifted["phase_problems"]),
                        shifted["phase_problems"])
        rows = walk_rows()
        rows[300]["script_segment"] = 3
        report = self.analyze(self.on("segment", rows=rows))["runs"][1]
        self.assertTrue(any("walk_1 rows carry script_segment [1, 3]" in p for p in report["phase_problems"]),
                        report["phase_problems"])
        rows = walk_rows()
        for row in rows[300:320]:
            row["admitted_command"] = [0.3, 0.0, 0.0]
        report = self.analyze(self.on("slow", rows=rows))["runs"][1]
        self.assertTrue(any("command [0.3, 0.0, 0.0] differs" in p for p in report["phase_problems"]))
        rows = walk_rows()
        for row in rows[500:510]:
            row["admitted_command"] = [0.2, 0.0, 0.0]
        report = self.analyze(self.on("extra", rows=rows))["runs"][1]
        self.assertTrue(any("do not match the script phases" in p for p in report["phase_problems"]))
        self.assertEqual(report["ac8"]["verdict"], "fail")
        post = self.analyze(self.on("post"))["runs"][1]
        self.assertEqual(post["recorded_phase_count"], 5)
        self.assertEqual(post["last_row_s"], 21.3)

    def test_not_a_hold_run_fails_ac8_and_missing_section_is_refused(self):
        off_as_on = write_walk_run(self.root, "off_as_on", walk_rows(stance=False), walk_summary(mode="off"))
        run = self.analyze(off_as_on)["runs"][1]
        self.assertIn("not a stance_hold auto run", run["ac8"]["problems"])
        self.assertIn("a: phase stand_initial did not reach FIXED_STAND before 4.0 s", run["ac8"]["problems"])
        stripped = dict(self.thresholds, values={k: v for k, v in self.thresholds["values"].items() if k != "ac8_walk"})
        with self.assertRaisesRegex(analyzer.AnalysisError, "no ac8_walk"):
            analyzer.analyze_walk(self.off, [self.on("x")], stripped)

    def test_variant_falls_back_to_the_setup_record(self):
        summary = walk_summary()
        del summary["stance_hold"]["entry_kd"]
        run = self.on("fallback", summary=summary)
        out = run / "returned_artifacts/runner_output"
        (out / "stance_hold_setup.json").write_text(json.dumps({"mode": "auto", "entry_kd": "step2p5"}))
        self.assertEqual(self.analyze(run)["runs"][1]["entry_kd"], "step2p5")

    def test_cli_walk(self):
        good = self.on("cli_good", entry_kd="step1")
        output = self.root / "report/walk.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(analyzer.main(["walk", "--off", str(self.off), "--on", str(good),
                                            "--on", str(self.on("cli_ramp", entry_yaw=0.1)),
                                            "--output", str(output)]), 0)
        report = json.loads(output.read_text())
        self.assertEqual(report["kind"], "walk")
        self.assertEqual(report["thresholds"]["sha256"], analyzer.FROZEN_THRESHOLDS_SHA256)
        self.assertEqual(report["selection"]["selected"]["entry_kd"], "step1")
        self.assertEqual(len(report["runs"]), 3)
        with self.assertRaisesRegex(SystemExit, "refusing to overwrite"):
            analyzer.main(["walk", "--off", str(self.off), "--on", str(good), "--output", str(output)])
        bad = self.on("cli_bad", entry_yaw=0.3)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(analyzer.main(["walk", "--off", str(self.off), "--on", str(bad)]), 1)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            analyzer.main(["walk", "--off", str(self.off)])
        with self.assertRaisesRegex(SystemExit, "is a stance_hold auto run"):
            analyzer.main(["walk", "--off", str(good), "--on", str(good)])


if __name__ == "__main__":
    unittest.main()

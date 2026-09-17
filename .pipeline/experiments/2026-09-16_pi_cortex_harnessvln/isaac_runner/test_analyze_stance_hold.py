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
            self.assertTrue(item["zero_command_intervals"])
        json.dumps(payload, allow_nan=False)


if __name__ == "__main__":
    unittest.main()

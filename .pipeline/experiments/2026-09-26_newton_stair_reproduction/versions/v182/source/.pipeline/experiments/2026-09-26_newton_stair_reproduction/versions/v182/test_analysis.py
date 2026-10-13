import json
from pathlib import Path
import tempfile
import unittest
from analyze import analyze


class AnalysisTests(unittest.TestCase):
    def fixture(self, root, n=500):
        (root / "probe_request.json").write_text(json.dumps(dict(terrain="flat", attempt=1)))
        (root / "result.json").write_text(json.dumps(dict(execution_completed=True)))
        rows = []
        for i in range(n):
            t = (i + 1) * .02
            x = min(t, 2.) * .1
            rows.append(dict(phase="stop1", physics_time_s=t, command_applied_start_s=0.,
                command_start_base_xyz=[0., 0., .3], joint_q=[x, 0., .3], joint_qd=[.1 if t < 2 else 0., 0.],
                base_up_z=1., effective_command=[0., 0., 0.], stance_mode="POLICY_ONLY", policy_owns_joints=True,
                foot_positions_world=[[x, 0., 0.]] * 4, foot_forces_n=[30.] * 4))
        (root / "telemetry.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
        return rows

    def test_braking_not_mislabelled_late_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            stop = analyze(root)["stops"][0]
            self.assertAlmostEqual(stop["net_xy_m"], .2)
            self.assertEqual(stop["late_max_excursion_m"], 0.)
            self.assertTrue(stop["complete_10s_window"])

    def test_partial_stop_is_not_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root, 50)
            self.assertFalse(analyze(root)["stops"][0]["complete_10s_window"])

    def test_hold_contamination_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); rows = self.fixture(root)
            rows[25]["stance_mode"] = "FIXED_STAND"
            (root / "telemetry.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
            with self.assertRaises(ValueError):
                analyze(root)


if __name__ == "__main__":
    unittest.main()

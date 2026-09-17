import ast
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

import command_script as cs

HERE = Path(__file__).resolve().parent
D5_SCRIPT = HERE / "command_scripts/walk_stop_start_stop_v1.json"
NATIVE = {"max_vx": 1.0, "max_vy": 0.35, "max_wz": 1.0, "max_horizontal_norm": 1.0}
STAND = {"max_vx": 0.30, "max_vy": 0.30, "max_wz": 0.8, "max_horizontal_norm": 0.30}


def script(*segments, **top):
    payload = {"schema_version": 1, "segments": [
        dict(zip(("t_start_s", "vx", "vy", "wz"), item)) if isinstance(item, tuple) else item for item in segments]}
    payload.update(top)
    return payload


class ParseTests(unittest.TestCase):
    def test_d5_script_is_the_prd_plan(self):
        loaded = cs.load_command_script(D5_SCRIPT, NATIVE)
        self.assertEqual(loaded["sha256"], hashlib.sha256(D5_SCRIPT.read_bytes()).hexdigest())
        self.assertEqual(loaded["script"]["name"], "walk_stop_start_stop_v1")
        phases = cs.command_script_phases(loaded["script"], 20.0)
        self.assertEqual([(p["label"], p["start_s"], p["end_s"], p["command"]) for p in phases], [
            ("stand_initial", 0.0, 4.0, [0.0, 0.0, 0.0]),
            ("walk_1", 4.0, 7.0, [0.6, 0.0, 0.0]),
            ("stop_1", 7.0, 12.0, [0.0, 0.0, 0.0]),
            ("walk_2", 12.0, 14.5, [0.6, 0.0, 0.0]),
            ("stop_2", 14.5, 20.0, [0.0, 0.0, 0.0]),
        ])
        self.assertEqual([p["zero"] for p in phases], [True, False, True, False, True])
        commanded = sum(0.6 * (p["end_s"] - p["start_s"]) for p in phases if not p["zero"])
        self.assertAlmostEqual(commanded, 3.3)
        # The stand limits refuse it: the walk needs the native baseline limits.
        with self.assertRaisesRegex(cs.CommandScriptError, "exceeds the runner limit max_vx"):
            cs.load_command_script(D5_SCRIPT, STAND)

    def test_normalized_copy_and_optional_fields(self):
        parsed = cs.parse_command_script(script((0, 0, 0, 0), {"t_start_s": 1, "vx": 0.2, "vy": -0.1, "wz": 0.5,
                                                                "label": "turn"}, note="n"), NATIVE)
        self.assertEqual(parsed["segments"][1], {"index": 1, "t_start_s": 1.0, "vx": 0.2, "vy": -0.1, "wz": 0.5,
                                                 "label": "turn"})
        self.assertEqual((parsed["name"], parsed["note"], parsed["schema_version"]), (None, "n", 1))
        self.assertIsInstance(parsed["segments"][0]["t_start_s"], float)
        self.assertEqual(parsed["limits"], {k: float(v) for k, v in NATIVE.items()})
        json.dumps(parsed, allow_nan=False)

    def test_limits_are_inclusive_with_the_runner_slack(self):
        edge = script((0.0, 1.0, 0.0, -1.0), (1.0, 0.0, 0.35, 1.0))
        cs.parse_command_script(edge, NATIVE)
        cs.parse_command_script(script((0.0, 0.3 + 5e-10, 0.0, 0.0)), STAND)
        diagonal = script((0.0, 0.3, 0.3, 0.0))
        with self.assertRaisesRegex(cs.CommandScriptError, "horizontal norm"):
            cs.parse_command_script(diagonal, STAND)
        cases = [
            (script((0.0, 1.0001, 0.0, 0.0)), "max_vx"),
            (script((0.0, -1.0001, 0.0, 0.0)), "max_vx"),
            (script((0.0, 0.0, 0.3501, 0.0)), "max_vy"),
            (script((0.0, 0.0, 0.0, -1.0001)), "max_wz"),
            (script((0.0, 0.95, 0.35, 0.0)), "max_horizontal_norm"),
        ]
        for payload, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(cs.CommandScriptError, message):
                cs.parse_command_script(payload, NATIVE)

    def test_malformed_scripts_are_refused(self):
        good = (0.0, 0.0, 0.0, 0.0)
        cases = [
            ([], "JSON object"),
            ({"segments": [dict(zip(("t_start_s", "vx", "vy", "wz"), good))]}, "schema_version"),
            (script(good, schema_version=2), "schema_version"),
            (script(good, schema_version=True), "schema_version"),
            (script(good, schema_version=1.0), "schema_version"),
            (script(good, extra=1), "unknown keys"),
            (script(good, name=3), "name must be a string"),
            ({"schema_version": 1, "segments": []}, "non-empty"),
            ({"schema_version": 1, "segments": {}}, "non-empty"),
            (script(*[(float(i), 0.0, 0.0, 0.0) for i in range(65)]), "at most 64"),
            (script([1, 2]), "must be an object"),
            (script({"t_start_s": 0.0, "vx": 0.0, "vy": 0.0}), "lacks"),
            (script({"t_start_s": 0.0, "vx": 0.0, "vy": 0.0, "wz": 0.0, "wx": 0.0}), "unknown keys"),
            (script({"t_start_s": 0.0, "vx": 0.0, "vy": 0.0, "wz": 0.0, "label": 5}), "label must be a string"),
            (script((0.5, 0.0, 0.0, 0.0)), "first segment must start at 0.0"),
            (script(good, (2.0, 0.1, 0.0, 0.0), (2.0, 0.0, 0.0, 0.0)), "does not increase"),
            (script(good, (2.0, 0.1, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)), "does not increase"),
            (script(good, (601.0, 0.0, 0.0, 0.0)), "outside"),
            (script((0.0, math.nan, 0.0, 0.0)), "not finite"),
            (script((0.0, 0.0, math.inf, 0.0)), "not finite"),
            (script((0.0, "0.1", 0.0, 0.0)), "must be a number"),
            (script((0.0, True, 0.0, 0.0)), "must be a number"),
            (script((0.0, None, 0.0, 0.0)), "must be a number"),
        ]
        for payload, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(cs.CommandScriptError, message):
                cs.parse_command_script(payload, NATIVE)
        for limits, message in (({"max_vx": 1.0}, "missing"), (dict(NATIVE, max_wz=0.0), "positive"),
                                (dict(NATIVE, max_vy=math.nan), "not finite"), (None, "mapping")):
            with self.subTest(limits=limits), self.assertRaisesRegex(cs.CommandScriptError, message):
                cs.parse_command_script(script(good), limits)
        self.assertTrue(issubclass(cs.CommandScriptError, ValueError))

    def test_file_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_bytes(b"{not json")
            with self.assertRaisesRegex(cs.CommandScriptError, "not UTF-8 JSON"):
                cs.load_command_script(path, NATIVE)
            path.write_bytes(b"\xff\xfe")
            with self.assertRaisesRegex(cs.CommandScriptError, "not UTF-8 JSON"):
                cs.load_command_script(path, NATIVE)
            # json accepts NaN literals; the parser refuses them.
            path.write_text('{"schema_version": 1, "segments": [{"t_start_s": 0, "vx": NaN, "vy": 0, "wz": 0}]}')
            with self.assertRaisesRegex(cs.CommandScriptError, "not finite"):
                cs.load_command_script(path, NATIVE)
            with self.assertRaises(FileNotFoundError):
                cs.load_command_script(Path(tmp) / "missing.json", NATIVE)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.script = cs.load_command_script(D5_SCRIPT, NATIVE)["script"]

    def test_segment_by_time_including_float32_boundaries(self):
        cases = {
            0.0: 0, 3.98: 0, 3.9998: 0, float(np.float32(4.0) - np.float32(4.0) * 1e-7): 1,
            float(np.float32(3.9999998)): 1, 4.0: 1, 4.0000002: 1, 6.98: 1, 7.0: 2, 11.98: 2,
            12.0: 3, 14.48: 3, float(np.float32(14.5)): 4, 14.5: 4, 20.0: 4, 1000.0: 4,
        }
        for now, index in cases.items():
            with self.subTest(now=now):
                segment, command = cs.command_script_at(self.script, now)
                self.assertEqual(segment, index)
                self.assertEqual(command, (0.6, 0.0, 0.0) if index in (1, 3) else (0.0, 0.0, 0.0))
                self.assertTrue(all(isinstance(v, float) for v in command))

    def test_control_step_sequence_at_20_ms(self):
        steps = []
        for k in range(1300):
            # Loop-top time as the runner computes it: float32-derived absolute time minus the origin.
            now = float(np.float32(123.4 + k * 0.02)) - float(np.float32(123.4))
            steps.append(cs.command_script_at(self.script, now)[0])
        changes = [k for k in range(1, len(steps)) if steps[k] != steps[k - 1]]
        # float32 rounding moves an edge by at most one control step.
        for got, want in zip(changes, (200, 350, 600, 725)):
            self.assertLessEqual(abs(got - want), 1)
        self.assertEqual(len(changes), 4)
        exact = [cs.command_script_at(self.script, round(k * 0.02, 9))[0] for k in range(1300)]
        self.assertEqual([k for k in range(1, 1300) if exact[k] != exact[k - 1]], [200, 350, 600, 725])

    def test_invalid_time_and_phase_end(self):
        with self.assertRaises(cs.CommandScriptError):
            cs.command_script_at(self.script, math.nan)
        with self.assertRaisesRegex(cs.CommandScriptError, "no command segment"):
            cs.command_script_at(self.script, -0.01)
        self.assertEqual(cs.command_script_at(self.script, -0.00005)[0], 0)
        with self.assertRaises(cs.CommandScriptError):
            cs.command_script_phases(self.script, 14.5)
        with self.assertRaises(cs.CommandScriptError):
            cs.command_script_phases(self.script, math.inf)

    def test_zero_helper(self):
        self.assertTrue(cs.command_script_is_zero(self.script["segments"][4]))
        self.assertFalse(cs.command_script_is_zero(self.script["segments"][3]))


class ModuleTests(unittest.TestCase):
    def test_module_imports_only_stdlib(self):
        tree = ast.parse(Path(cs.__file__).read_text(encoding="utf-8"), feature_version=(3, 8))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add((node.module or "").split(".")[0])
        self.assertEqual(names, {"hashlib", "json", "math"})


if __name__ == "__main__":
    unittest.main()

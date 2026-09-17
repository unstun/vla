import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
BASE_FILE = HERE / "builds/scan_03/src/plan_manage/src/planner_manager.cpp"


def load(name):
    spec = importlib.util.spec_from_file_location(name, str(HERE / (name + ".py")))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


fix = load("apply_scan_terminal_accel_fix")
compare = load("compare_scan_trees")


class ApplyTerminalAccelFixTests(unittest.TestCase):
    def setUp(self):
        if not BASE_FILE.is_file():
            self.skipTest("local-only scan_03 source is absent")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.build = Path(self.tmp.name) / "scan_test"
        self.target = self.build / fix.TARGET_REL
        self.target.parent.mkdir(parents=True)
        shutil.copyfile(BASE_FILE, self.target)
        self.original = self.target.read_bytes()

    def assert_untouched(self):
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse((self.build / fix.MANIFEST_NAME).exists())

    def test_base_copy_matches_recorded_hash(self):
        self.assertEqual(hashlib.sha256(self.original).hexdigest(), fix.BASE_SHA256)

    def test_correct_application_changes_exactly_one_line(self):
        manifest = fix.apply_fix(self.build)
        after = self.target.read_bytes()
        before_lines, after_lines = fix.split_lines(self.original), fix.split_lines(after)
        self.assertEqual(len(before_lines), len(after_lines))
        changed = [i + 1 for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
        self.assertEqual(changed, [171])
        self.assertEqual(after_lines[170], fix.AFTER_LINE.encode() + b"\r\n")
        self.assertEqual(after, self.original.replace(b"evaluateAcc(t)", b"evaluateAcc(time)"))
        written = json.loads((self.build / fix.MANIFEST_NAME).read_text(encoding="utf-8"))
        self.assertEqual(written, manifest)
        self.assertEqual(written["before_sha256"], fix.BASE_SHA256)
        self.assertEqual(written["after_sha256"], hashlib.sha256(after).hexdigest())
        self.assertEqual(written["changed_line_numbers"], [171])
        self.assertEqual(written["line_terminator"], "\r\n")
        self.assertIn("-" + fix.BEFORE_LINE, written["unified_diff"])
        self.assertIn("+" + fix.AFTER_LINE, written["unified_diff"])
        self.assertIn("time_is_true_end", written["rationale"])

        reference = Path(self.tmp.name) / "reference"
        (reference / fix.TARGET_REL).parent.mkdir(parents=True)
        shutil.copyfile(BASE_FILE, reference / fix.TARGET_REL)
        result = compare.compare_trees(reference / "src", self.build / "src")
        self.assertTrue(result["exactly_one_file_one_line"])
        self.assertEqual(result["changed_files"][0]["opcodes"],
                         [{"tag": "replace", "reference_lines": [171, 171], "candidate_lines": [171, 171]}])

    def test_wrong_hash_is_refused(self):
        self.target.write_bytes(self.original + b"// drift\n")
        self.original = self.target.read_bytes()
        with self.assertRaisesRegex(fix.FixRefused, "base hash mismatch"):
            fix.apply_fix(self.build)
        self.assert_untouched()

    def test_wrong_line_is_refused_even_with_matching_expected_hash(self):
        lines = fix.split_lines(self.original)
        lines[170] = b"        start_end_derivatives.push_back(gl_traj.evaluateAcc(t + 0));\r\n"
        self.target.write_bytes(b"".join(lines))
        self.original = self.target.read_bytes()
        with self.assertRaisesRegex(fix.FixRefused, "line 171 text mismatch"):
            fix.apply_fix(self.build, expected_sha256=hashlib.sha256(self.original).hexdigest())
        self.assert_untouched()

    def test_double_application_is_refused(self):
        fix.apply_fix(self.build)
        patched = self.target.read_bytes()
        with self.assertRaisesRegex(fix.FixRefused, "manifest already exists"):
            fix.apply_fix(self.build)
        (self.build / fix.MANIFEST_NAME).unlink()
        with self.assertRaisesRegex(fix.FixRefused, "already applied"):
            fix.apply_fix(self.build)
        self.assertEqual(self.target.read_bytes(), patched)

    def test_recorded_build_is_refused(self):
        (self.build / "source_sha256.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(fix.FixRefused, "must precede build_scan"):
            fix.apply_fix(self.build)
        self.assert_untouched()

    def test_cli_refuses_recorded_build_names(self):
        with self.assertRaisesRegex(fix.FixRefused, "immutable"):
            fix.main(["scan_03"])


class CompareScanTreesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a = Path(self.tmp.name) / "a"
        self.b = Path(self.tmp.name) / "b"
        for root in (self.a, self.b):
            (root / "pkg").mkdir(parents=True)
            (root / "pkg/file.cpp").write_bytes(b"one\r\ntwo\nthree\r\n")

    def test_identical_trees_are_not_one_line(self):
        result = compare.compare_trees(self.a, self.b)
        self.assertEqual(result["changed_files"], [])
        self.assertFalse(result["exactly_one_file_one_line"])

    def test_extra_file_and_two_line_change_are_listed(self):
        (self.b / "pkg/file.cpp").write_bytes(b"ONE\r\nTWO\nthree\r\n")
        (self.b / "pkg/extra.txt").write_text("x", encoding="utf-8")
        (self.b / "empty").mkdir()
        result = compare.compare_trees(self.a, self.b)
        self.assertEqual(result["only_in_candidate"], ["pkg/extra.txt"])
        self.assertEqual(result["candidate_other_entries"], [{"path": "empty", "kind": "empty_directory"}])
        self.assertFalse(result["changed_files"][0]["single_line_replacement"])
        self.assertFalse(result["exactly_one_file_one_line"])

    def test_line_ending_only_change_is_detected(self):
        (self.b / "pkg/file.cpp").write_bytes(b"one\ntwo\nthree\r\n")
        result = compare.compare_trees(self.a, self.b)
        self.assertTrue(result["exactly_one_file_one_line"])
        self.assertEqual(result["changed_files"][0]["opcodes"][0]["reference_lines"], [1, 1])


if __name__ == "__main__":
    unittest.main()

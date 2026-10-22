"""Check task startup without executing project hooks or touching real tasks."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class TaskStartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vla no hooks ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(
            ROOT / ".trellis/scripts", self.root / ".trellis/scripts",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        for platform in (".claude", ".cursor", ".codex"):
            (self.root / platform).mkdir()
        (self.root / ".trellis/spec").mkdir()
        (self.root / ".trellis/spec/example.md").write_text("# Example spec\n")
        self.env = dict(
            os.environ, TRELLIS_CONTEXT_ID="no-hooks-test",
            TRELLIS_DEVELOPER="review", PYTHONDONTWRITEBYTECODE="1",
        )
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            self.env.pop(key, None)
        subprocess.run(
            ["git", "init", "-q", "-b", "main", str(self.root)],
            env=self.env, check=True,
        )
        self.set_mode("inline")
        result = self.run_task(
            "create", "Startup regression", "--slug", "startup",
            "--description", "Test only", "--base-branch", "main", "--no-start",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.task = self.root / result.stdout.strip().splitlines()[-1]
        self.assertEqual((self.task / "implement.jsonl").read_text(), "")
        self.assertEqual((self.task / "check.jsonl").read_text(), "")

    def set_mode(self, mode):
        (self.root / ".trellis/config.yaml").write_text(
            f"session_auto_commit: false\ncodex:\n  dispatch_mode: {mode}\n"
        )

    def run_task(self, *args):
        return subprocess.run(
            [sys.executable, str(self.root / ".trellis/scripts/task.py"),
             *map(str, args)], cwd=self.root, env=self.env,
            text=True, capture_output=True,
        )

    def status(self):
        return json.loads((self.task / "task.json").read_text())["status"]

    def test_inline_start_with_other_platforms_and_empty_manifests(self):
        result = self.run_task("start", self.task)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.status(), "in_progress")
        self.assertEqual((self.task / "implement.jsonl").read_text(), "")
        self.assertEqual((self.task / "check.jsonl").read_text(), "")
        current = self.run_task("current")
        self.assertIn(self.task.name, current.stdout)

    def test_auto_mode_keeps_empty_context_gate(self):
        for mode in ("auto", "sub-agent"):
            with self.subTest(mode=mode):
                self.set_mode(mode)
                result = self.run_task("start", self.task)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("no curated entries", result.stdout)
                self.assertEqual(self.status(), "planning")

    def test_auto_mode_starts_with_curated_context(self):
        self.set_mode("auto")
        for role in ("implement", "check"):
            result = self.run_task(
                "add-context", self.task, role,
                ".trellis/spec/example.md", "Test context",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.run_task("start", self.task)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.status(), "in_progress")

    def test_auto_mode_explicit_override_remains_available(self):
        self.set_mode("auto")
        result = self.run_task("start", self.task, "--allow-empty-context")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.status(), "in_progress")


if __name__ == "__main__":
    unittest.main()

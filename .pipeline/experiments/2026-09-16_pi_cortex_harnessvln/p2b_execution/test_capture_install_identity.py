import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SCAN_03_IDENTITY = HERE / "builds/scan_03/install_identity.json"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


capture = load("capture_install_identity", HERE / "capture_install_identity.py")
launcher = load("run_two_goal_pilot_for_capture_test", capture.LAUNCHER)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CaptureInstallIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name) / "workspace"
        for rel, data in {
            "src/pkg/a.cpp": b"int a;\r\n",
            "install/setup.bash": b"# setup\n",
            "install/pkg/lib/libpkg.a": b"\x00lib",
            "install/pkg/lib/python3.8/site-packages/pkg/__init__.py": b"",
            "install/pkg/lib/python3.8/site-packages/pkg/__pycache__/__init__.cpython-38.pyc": b"pyc",
        }.items():
            (self.ws / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.ws / rel).write_bytes(data)
        self.sources = {"src/pkg/a.cpp": digest(self.ws / "src/pkg/a.cpp")}
        self.base = Path(self.tmp.name) / "build"
        self.base.mkdir()
        self.calls = []

    def job(self, sources=None):
        sources = self.sources if sources is None else sources
        return {
            "build_name": "scan_test",
            "base": self.base,
            "remote_workspace": str(self.ws),
            "build_result": {"passed": True, "image_id": "image-id", "remote_workspace": str(self.ws)},
            "expected_source": sources,
            "preconditions": {"all": True},
            "command": capture.SSH + ["python3 -"],
            "script": capture.remote_script(launcher, str(self.ws), sources),
            "launcher_sha256": "launcher",
        }

    def local_runner(self, command, **kwargs):
        """Stand-in for SSH: run the exact remote script with a local interpreter."""
        self.calls.append(command)
        return subprocess.run([sys.executable, "-"], **kwargs)

    def test_capture_writes_scan_03_form_and_the_launch_gate_accepts_it(self):
        record = capture.capture(self.job(), runner=self.local_runner)
        self.assertEqual(self.calls, [capture.SSH + ["python3 -"]])
        text = (self.base / "install_identity.json").read_text(encoding="utf-8")
        identity = json.loads(text)
        self.assertEqual(list(identity), ["installed_files", "source_file_count", "source_matches", "remote_workspace", "image_id"])
        self.assertEqual(text, json.dumps(identity, indent=2) + "\n")
        self.assertEqual(identity["installed_files"], {
            "install/pkg/lib/libpkg.a": digest(self.ws / "install/pkg/lib/libpkg.a"),
            "install/pkg/lib/python3.8/site-packages/pkg/__init__.py": digest(self.ws / "install/pkg/lib/python3.8/site-packages/pkg/__init__.py"),
            "install/setup.bash": digest(self.ws / "install/setup.bash"),
        })
        self.assertEqual(identity["source_file_count"], 1)
        self.assertEqual(identity["image_id"], "image-id")
        self.assertTrue(record["wrote_install_identity"])
        self.assertEqual(record["install_excluded"], ["install/pkg/lib/python3.8/site-packages/pkg/__pycache__/__init__.cpython-38.pyc"])
        self.assertTrue((self.base / "install_identity_capture.log").exists())

        gate = {"workspace_gate": {"expected_source_files": self.sources, "expected_remote_workspace": str(self.ws)},
                "install_identity": identity}
        self.assertTrue(launcher.scan_workspace_gate(self.ws, gate)["passed"])

    def test_capture_refuses_source_mismatch_without_writing_identity(self):
        with self.assertRaisesRegex(RuntimeError, "not written"):
            capture.capture(self.job(sources={"src/pkg/a.cpp": "0" * 64}), runner=self.local_runner)
        self.assertFalse((self.base / "install_identity.json").exists())
        record = json.loads((self.base / "install_identity_capture.json").read_text(encoding="utf-8"))
        self.assertEqual(record["source_comparison"]["mismatched"], ["src/pkg/a.cpp"])
        self.assertFalse(record["wrote_install_identity"])

    def test_capture_refuses_failed_preconditions_before_contact(self):
        job = self.job()
        job["preconditions"] = {"outputs_absent": False}
        with self.assertRaisesRegex(RuntimeError, "preconditions failed"):
            capture.capture(job, runner=self.local_runner)
        self.assertEqual(self.calls, [])

    def test_recorded_builds_fail_capture_preconditions(self):
        job = capture.plan("scan_03")
        self.assertFalse(job["preconditions"]["not_a_recorded_build"])
        self.assertFalse(job["preconditions"]["outputs_absent"])

    def test_dry_run_prints_command_and_contacts_nothing(self):
        real_run = capture.subprocess.run
        capture.subprocess.run = lambda *a, **k: self.fail("dry run must not execute commands")
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                rc = capture.main(["scan_04", "--dry-run"])
        finally:
            capture.subprocess.run = real_run
        self.assertEqual(rc, 0)
        printed = json.loads(out.getvalue())
        self.assertEqual(printed["command"], ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "gpu5070ti", "python3 -"])
        self.assertEqual(printed["remote_workspace"], "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_04")
        self.assertIn("def scan_tree_hashes", printed["stdin_script"])
        compile(printed["stdin_script"], "remote_capture.py", "exec")

    def test_compare_existing_reports_install_difference(self):
        job = self.job()
        capture.capture(job, runner=self.local_runner)
        (self.ws / "install/pkg/lib/libpkg.a").write_bytes(b"changed")
        result = capture.compare_existing(job, runner=self.local_runner)
        self.assertFalse(result["passed"])
        self.assertEqual(result["install_comparison"]["mismatched"], ["install/pkg/lib/libpkg.a"])

    def test_scan_03_identity_has_no_bytecode_entries(self):
        if not SCAN_03_IDENTITY.exists():
            self.skipTest("scan_03 identity absent")
        installed = json.loads(SCAN_03_IDENTITY.read_text(encoding="utf-8"))["installed_files"]
        self.assertEqual(len(installed), 380)
        self.assertFalse([k for k in installed if "__pycache__" in k or k.endswith((".pyc", ".pyo"))])


if __name__ == "__main__":
    unittest.main()

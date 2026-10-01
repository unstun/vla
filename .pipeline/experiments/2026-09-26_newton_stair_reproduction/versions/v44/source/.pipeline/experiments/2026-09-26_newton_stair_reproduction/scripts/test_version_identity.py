"""Prove a changed source cannot silently reuse a frozen version label."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_local_episode as launcher


class VersionIdentityTest(unittest.TestCase):
    def test_source_identity_and_mutation_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "controller.py"
            source.write_text("original\n")
            version = root / "versions/v4"
            version.mkdir(parents=True)
            manifest = {"version":"v4", "source_files":{"controller.py":hashlib.sha256(source.read_bytes()).hexdigest()}}
            (version / "manifest.json").write_text(json.dumps(manifest))
            out = root / "out"
            out.mkdir()
            with patch.object(launcher, "BASE", root), patch.object(launcher, "PROJECT", root):
                self.assertEqual(launcher.verify_integration_version(out, "v4"), "v4")
                self.assertEqual(json.loads((out / "integration_version.json").read_text()), manifest)
                source.write_text("different controller\n")
                with self.assertRaisesRegex(ValueError, "register a new version"):
                    launcher.verify_integration_version(out, "v4")
                with self.assertRaisesRegex(ValueError, "integer integration version"):
                    launcher.verify_integration_version(out, "../../v3")


if __name__ == "__main__":
    unittest.main()

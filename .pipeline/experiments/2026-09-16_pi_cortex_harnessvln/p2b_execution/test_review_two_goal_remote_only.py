"""The remote-only rule in review_two_goal.py, checked on a linked copy of the accepted actual4 package."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import review_two_goal as review_mod

HERE = Path(__file__).resolve().parent
ACTUAL4 = HERE.parent / "isaac_runner/two_goal_runs/two_goal_20260916T162236Z_p2b_actual4"
BULK = review_mod.REMOTE_ONLY_FILES


def link_or_copy(src, dst):
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


@unittest.skipUnless((ACTUAL4 / "returned_artifacts/artifact_hashes.json").is_file(), "actual4 package not present")
class RemoteOnlyReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name) / ACTUAL4.name
        shutil.copytree(ACTUAL4, self.run, symlinks=True, copy_function=link_or_copy)
        self.manifest = json.loads((self.run / "returned_artifacts/artifact_hashes.json").read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def drop_bulk(self):
        for rel in BULK:
            (self.run / "returned_artifacts" / rel).unlink()

    def write_record(self, all_match=True, override=None):
        files = []
        for rel in BULK:
            digest = (override or {}).get(rel, self.manifest[rel])
            files.append({"path": rel, "bytes": 1, "sha256": digest, "manifest_sha256": self.manifest[rel]})
        record = {"schema_version": 1, "files": files, "all_match": all_match}
        (self.run / "remote_only_artifacts.json").write_text(json.dumps(record))

    def checks(self):
        result = review_mod.review(self.run)
        return result, result["checks"]

    def test_full_package_unchanged(self):
        result, checks = self.checks()
        self.assertEqual(len(checks), 41)
        self.assertTrue(result["passed"])
        self.assertEqual(result["remote_only_accepted"], [])

    def test_missing_bulk_without_record_fails(self):
        self.drop_bulk()
        result, checks = self.checks()
        self.assertFalse(checks["returned_hashes_match"])
        self.assertEqual([k for k, v in checks.items() if not v], ["returned_hashes_match"])

    def test_missing_bulk_with_valid_record_passes(self):
        self.drop_bulk()
        self.write_record()
        result, checks = self.checks()
        self.assertTrue(result["passed"])
        self.assertEqual(result["remote_only_accepted"], sorted(BULK))

    def test_record_hash_mismatch_fails(self):
        self.drop_bulk()
        self.write_record(override={BULK[0]: "0" * 64})
        _, checks = self.checks()
        self.assertFalse(checks["returned_hashes_match"])

    def test_record_not_all_match_fails(self):
        self.drop_bulk()
        self.write_record(all_match=False)
        _, checks = self.checks()
        self.assertFalse(checks["returned_hashes_match"])

    def test_other_missing_file_fails_even_with_record(self):
        self.drop_bulk()
        self.write_record()
        (self.run / "returned_artifacts/logs/pct_worker.log").unlink()
        _, checks = self.checks()
        self.assertFalse(checks["returned_hashes_match"])

    def test_changed_returned_file_fails(self):
        path = self.run / "returned_artifacts/logs/pct_worker.log"
        data = path.read_bytes()
        path.unlink()  # break the hardlink before writing
        path.write_bytes(data + b"x")
        _, checks = self.checks()
        self.assertFalse(checks["returned_hashes_match"])


if __name__ == "__main__":
    unittest.main()

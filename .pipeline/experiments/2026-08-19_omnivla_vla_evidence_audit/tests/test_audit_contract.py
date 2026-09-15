import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

import sys

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT / "scripts"))

from audit_contract import (  # noqa: E402
    RecordError,
    base_record,
    expected_run_id,
    load_records,
    retain_record,
    scheduled_attempts,
    validate_record,
)
from generate_fixtures import build as build_fixtures  # noqa: E402


SOURCE = "5182600cb4a9ee07684e17cdd2a6cbafc56b8a68"
REVISION = "e36a84d4923c041149d441f93f3bdb7092bb5f07"


def fixture_manifest():
    images = {}
    for image_id in (
        "real_lite3",
        "upstream_sample",
        "real_lite3_mirror",
        "real_lite3_blur",
    ):
        images[image_id] = {
            "id": image_id,
            "path": "inputs/%s.jpg" % image_id,
            "sha256": "a" * 64,
            "width": 1280,
            "height": 720,
            "transform": {"name": "test"},
        }
    return {"schema_version": 1, "images": images}


def success_record():
    row = scheduled_attempts("omnivla_original")[0]
    record = base_record(
        row,
        fixture_manifest(),
        SOURCE,
        REVISION,
        "What action should the robot take to {instruction}?",
    )
    record.update(
        {
            "status": "success",
            "trajectory_normalized": [[float(i), 0.0, 1.0, 0.0] for i in range(8)],
            "failure": None,
            "timings_seconds": {"preprocess": 0.1, "forward": 0.2, "postprocess": 0.01},
            "process": {"exit_code": 0, "warnings": []},
        }
    )
    return record


class ContractTests(unittest.TestCase):
    def test_matrix_has_24_unique_attempts(self):
        rows = scheduled_attempts("omnivla_original")
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({expected_run_id(row) for row in rows}), 24)

    def test_valid_success(self):
        self.assertEqual(validate_record(success_record())["status"], "success")

    def test_invalid_shape_is_rejected(self):
        record = success_record()
        record["trajectory_normalized"] = [[0.0] * 4] * 7
        with self.assertRaises(RecordError):
            validate_record(record)

    def test_nan_and_inf_are_rejected(self):
        for bad in (math.nan, math.inf, -math.inf):
            record = success_record()
            record["trajectory_normalized"][0][0] = bad
            with self.assertRaises(RecordError):
                validate_record(record)

    def test_identity_mismatch_is_rejected(self):
        record = success_record()
        with self.assertRaisesRegex(RecordError, "checkpoint identity mismatch"):
            validate_record(record, expected_checkpoint_revision="b" * 40)

    def test_failure_is_retained_and_loaded(self):
        record = success_record()
        record["status"] = "failure"
        record["trajectory_normalized"] = None
        record["failure"] = {"type": "RuntimeError", "reason": "synthetic failure"}
        record["process"] = {"exit_code": 1, "warnings": []}
        with tempfile.TemporaryDirectory() as directory:
            path = retain_record(record, Path(directory))
            loaded = load_records([path])
        self.assertEqual(loaded[0]["status"], "failure")
        self.assertEqual(loaded[0]["failure"]["reason"], "synthetic failure")

    def test_record_is_immutable(self):
        record = success_record()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            retain_record(record, target)
            with self.assertRaises(FileExistsError):
                retain_record(record, target)


class FixtureTests(unittest.TestCase):
    def test_fixture_transforms_are_deterministic(self):
        repo_root = Path(__file__).resolve().parents[4]
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            manifest_a = build_fixtures(repo_root, Path(first))
            manifest_b = build_fixtures(repo_root, Path(second))
        hashes_a = {key: value["sha256"] for key, value in manifest_a["images"].items()}
        hashes_b = {key: value["sha256"] for key, value in manifest_b["images"].items()}
        self.assertEqual(hashes_a, hashes_b)


if __name__ == "__main__":
    unittest.main()

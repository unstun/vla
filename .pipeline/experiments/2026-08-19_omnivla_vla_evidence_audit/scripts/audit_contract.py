#!/usr/bin/env python3
"""Single owner for the immutable OmniVLA audit run-record contract."""

from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional


SCHEMA_VERSION = 1
MODEL_IDS = ("omnivla_original", "omnivla_edge")
IMAGE_IDS = (
    "real_lite3",
    "upstream_sample",
    "real_lite3_mirror",
    "real_lite3_blur",
)
PROMPTS = {
    "move_forward": "move forward",
    "turn_left": "turn left",
    "turn_right": "turn right",
    "stop": "stop",
}


class RecordError(ValueError):
    """A retained attempt violates the frozen audit contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def scheduled_attempts(model_id: str) -> List[Dict[str, Any]]:
    if model_id not in MODEL_IDS:
        raise RecordError("unknown model_id: %s" % model_id)
    rows: List[Dict[str, Any]] = []
    for prompt_id in ("move_forward", "turn_left", "turn_right", "stop"):
        for repeat in range(1, 4):
            rows.append(
                {
                    "model_id": model_id,
                    "panel": "language",
                    "image_id": "real_lite3",
                    "prompt_id": prompt_id,
                    "repeat_index": repeat,
                }
            )
    for image_id in IMAGE_IDS:
        for repeat in range(1, 4):
            rows.append(
                {
                    "model_id": model_id,
                    "panel": "vision",
                    "image_id": image_id,
                    "prompt_id": "move_forward",
                    "repeat_index": repeat,
                }
            )
    if len(rows) != 24:
        raise AssertionError("frozen matrix must contain 24 attempts per model")
    return rows


def expected_run_id(row: Mapping[str, Any]) -> str:
    return "%s__%s__%s__%s__r%d" % (
        row["model_id"],
        row["panel"],
        row["image_id"],
        row["prompt_id"],
        row["repeat_index"],
    )


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RecordError("%s must be numeric" % label)
    result = float(value)
    if not math.isfinite(result):
        raise RecordError("%s must be finite" % label)
    return result


def validate_trajectory(value: Any) -> List[List[float]]:
    if not isinstance(value, list) or len(value) != 8:
        raise RecordError("trajectory_normalized must have shape [8,4]")
    result: List[List[float]] = []
    for row_index, row in enumerate(value):
        if not isinstance(row, list) or len(row) != 4:
            raise RecordError("trajectory_normalized must have shape [8,4]")
        result.append(
            [
                _finite_number(item, "trajectory[%d][%d]" % (row_index, column_index))
                for column_index, item in enumerate(row)
            ]
        )
    return result


def validate_record(
    value: Any,
    expected_model_id: Optional[str] = None,
    expected_source_commit: Optional[str] = None,
    expected_checkpoint_revision: Optional[str] = None,
) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise RecordError("record must be an object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise RecordError("schema_version mismatch")
    model_id = value.get("model_id")
    if model_id not in MODEL_IDS:
        raise RecordError("unknown model_id")
    if expected_model_id is not None and model_id != expected_model_id:
        raise RecordError("model identity mismatch")
    row = {
        "model_id": model_id,
        "panel": value.get("panel"),
        "image_id": value.get("image_id"),
        "prompt_id": value.get("prompt_id"),
        "repeat_index": value.get("repeat_index"),
    }
    if row not in scheduled_attempts(model_id):
        raise RecordError("attempt is not in the frozen matrix")
    if value.get("run_id") != expected_run_id(row):
        raise RecordError("run_id does not match the frozen matrix row")
    if value.get("actuation_enabled") is not False:
        raise RecordError("actuation_enabled must be false")
    if value.get("instruction") != PROMPTS[row["prompt_id"]]:
        raise RecordError("instruction mismatch")
    if value.get("instruction_utf8_hex") != value["instruction"].encode("utf-8").hex():
        raise RecordError("instruction UTF-8 bytes mismatch")
    if value.get("source_commit") is None or value.get("checkpoint_revision") is None:
        raise RecordError("source and checkpoint identities are required")
    if expected_source_commit is not None and value["source_commit"] != expected_source_commit:
        raise RecordError("source identity mismatch")
    if expected_checkpoint_revision is not None and value["checkpoint_revision"] != expected_checkpoint_revision:
        raise RecordError("checkpoint identity mismatch")
    image = value.get("image")
    if not isinstance(image, dict) or image.get("id") != row["image_id"]:
        raise RecordError("image identity mismatch")
    if not isinstance(image.get("sha256"), str) or len(image["sha256"]) != 64:
        raise RecordError("image sha256 is required")
    if not isinstance(image.get("width"), int) or not isinstance(image.get("height"), int):
        raise RecordError("image dimensions are required")
    if value.get("modality_id") != 7 or value.get("modality_name") != "language only":
        raise RecordError("language-only modality identity mismatch")
    status = value.get("status")
    if status == "success":
        value["trajectory_normalized"] = validate_trajectory(value.get("trajectory_normalized"))
        if value.get("failure") is not None:
            raise RecordError("success record must not contain a failure")
    elif status == "failure":
        failure = value.get("failure")
        if not isinstance(failure, dict) or not str(failure.get("reason", "")).strip():
            raise RecordError("failure record must retain a reason")
        if value.get("trajectory_normalized") is not None:
            validate_trajectory(value["trajectory_normalized"])
    else:
        raise RecordError("status must be success or failure")
    timings = value.get("timings_seconds")
    if not isinstance(timings, dict):
        raise RecordError("timings_seconds is required")
    for label, item in timings.items():
        if item is not None and _finite_number(item, "timing %s" % label) < 0:
            raise RecordError("timings must be non-negative")
    canonical_bytes(value)
    return value


def base_record(
    row: Mapping[str, Any],
    fixtures: Mapping[str, Any],
    source_commit: str,
    checkpoint_revision: str,
    prompt_wrapper: str,
) -> Dict[str, Any]:
    fixture = fixtures["images"][row["image_id"]]
    instruction = PROMPTS[row["prompt_id"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": expected_run_id(row),
        "model_id": row["model_id"],
        "panel": row["panel"],
        "image_id": row["image_id"],
        "prompt_id": row["prompt_id"],
        "repeat_index": row["repeat_index"],
        "source_commit": source_commit,
        "checkpoint_revision": checkpoint_revision,
        "image": fixture,
        "instruction": instruction,
        "instruction_utf8_hex": instruction.encode("utf-8").hex(),
        "prompt_wrapper": prompt_wrapper,
        "modality_id": 7,
        "modality_name": "language only",
        "determinism": {
            "serial_execution": True,
            "model_eval": True,
            "torch_grad_enabled": False,
            "seed": 0,
        },
        "actuation_enabled": False,
        "created_utc": utc_now(),
    }


def retain_record(record: Dict[str, Any], records_dir: Path) -> Path:
    validate_record(record)
    records_dir.mkdir(parents=True, exist_ok=True)
    path = records_dir / (record["run_id"] + ".json")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(str(path), flags, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(canonical_bytes(record))
    return path


def load_records(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    seen = set()
    for path in paths:
        record = validate_record(json.loads(path.read_text(encoding="utf-8")))
        if record["run_id"] in seen:
            raise RecordError("duplicate run_id: %s" % record["run_id"])
        seen.add(record["run_id"])
        records.append(record)
    return records


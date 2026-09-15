#!/usr/bin/env python3
"""Load pinned OmniVLA-original once and retain the frozen 24-forward matrix."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import traceback
from pathlib import Path

from audit_contract import (
    base_record,
    canonical_bytes,
    retain_record,
    scheduled_attempts,
    sha256_file,
    utc_now,
    validate_record,
)


SOURCE_COMMIT = "5182600cb4a9ee07684e17cdd2a6cbafc56b8a68"
CHECKPOINT_REVISION = "e36a84d4923c041149d441f93f3bdb7092bb5f07"


def event(path: Path, kind: str, **fields) -> None:
    payload = {"utc": utc_now(), "kind": kind}
    payload.update(fields)
    with path.open("ab") as stream:
        stream.write(canonical_bytes(payload))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--checkpoint-path", type=Path, required=True)
    args = parser.parse_args()
    experiment_root = args.experiment_root.resolve()
    runtime_root = args.runtime_root.resolve()
    sys.path.insert(0, str(runtime_root))
    from omnivla_lite3_receive_only.engine_original import OriginalEngine

    import numpy as np
    import torch

    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    fixtures = json.loads((experiment_root / "fixtures.json").read_text(encoding="utf-8"))
    records_dir = experiment_root / "raw/omnivla_original/records"
    events_path = experiment_root / "raw/omnivla_original/attempt_events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    if records_dir.exists() and any(records_dir.iterdir()):
        raise SystemExit("refusing to reuse immutable original records directory")
    event(events_path, "batch_start", model_id="omnivla_original")
    load_started = time.monotonic()
    engine = OriginalEngine(args.upstream_root, args.checkpoint_path)
    load_seconds = time.monotonic() - load_started
    event(events_path, "model_loaded", load_seconds=load_seconds)
    success_count = 0
    failure_count = 0
    for row in scheduled_attempts("omnivla_original"):
        run_id = "%s__%s__%s__%s__r%d" % (
            row["model_id"], row["panel"], row["image_id"], row["prompt_id"], row["repeat_index"]
        )
        event(events_path, "attempt_start", run_id=run_id)
        record = base_record(
            row,
            fixtures,
            SOURCE_COMMIT,
            CHECKPOINT_REVISION,
            "What action should the robot take to {instruction}?",
        )
        record["host"] = {"role": "gpu40901", "hostname": None}
        record["model_load_seconds"] = load_seconds
        image_path = experiment_root / fixtures["images"][row["image_id"]]["path"]
        if sha256_file(image_path) != fixtures["images"][row["image_id"]]["sha256"]:
            raise RuntimeError("fixture identity changed during batch")
        started = time.monotonic()
        try:
            trajectory = engine.infer(image_path.read_bytes(), record["instruction"])
            forward_seconds = time.monotonic() - started
            record.update(
                {
                    "status": "success",
                    "trajectory_normalized": trajectory,
                    "failure": None,
                    "timings_seconds": {
                        "preprocess": None,
                        "forward_and_transforms": forward_seconds,
                        "postprocess": None,
                    },
                    "process": {"exit_code": 0, "warnings": []},
                }
            )
            validate_record(
                record,
                expected_model_id="omnivla_original",
                expected_source_commit=SOURCE_COMMIT,
                expected_checkpoint_revision=CHECKPOINT_REVISION,
            )
            success_count += 1
            event(events_path, "attempt_success", run_id=run_id, forward_seconds=forward_seconds)
        except Exception as exc:
            elapsed = time.monotonic() - started
            record.update(
                {
                    "status": "failure",
                    "trajectory_normalized": None,
                    "failure": {
                        "type": type(exc).__name__,
                        "reason": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                    "timings_seconds": {
                        "preprocess": None,
                        "forward_and_transforms": elapsed,
                        "postprocess": None,
                    },
                    "process": {"exit_code": 1, "warnings": []},
                }
            )
            failure_count += 1
            event(events_path, "attempt_failure", run_id=run_id, reason=str(exc))
        retain_record(record, records_dir)
    event(
        events_path,
        "batch_end",
        success_count=success_count,
        failure_count=failure_count,
        retained_count=success_count + failure_count,
    )
    print(json.dumps({"success": success_count, "failure": failure_count, "retained": success_count + failure_count}))


if __name__ == "__main__":
    main()


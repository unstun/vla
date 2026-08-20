#!/usr/bin/env python3
"""P1 benchmark for the official resident DynaNav predict_async path."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np

from tic_vla_lite3.model_runtime import AsyncModelRuntime


def percentile(values, q):
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dynav-overlay", required=True, type=Path)
    parser.add_argument("--base-model", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cycles", type=int, default=100)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with AsyncModelRuntime(args.dynav_overlay, args.base_model, args.checkpoint) as runtime:
        first_started = time.perf_counter()
        first = runtime.predict_async(
            [args.image] * 4, "Move forward safely and efficiently.",
            [0.0] * 5, 0, {"position": [0.0, 0.0, 0.0],
                            "quaternion": [0.0, 0.0, 0.0, 1.0]},
            0.0, [args.image] * 4)
        first_generation_seconds = time.perf_counter() - first_started
        if first.waypoints.shape != (1, 30, 2) or not np.isfinite(first.waypoints).all():
            raise RuntimeError("first_generation_output_invalid")
        for measured_index in range(args.cycles):
            step = measured_index + 1
            started = time.perf_counter()
            result = runtime.predict_async(
                [args.image] * 4, "Move forward safely and efficiently.",
                [0.0] * 5, step, {"position": [0.0, 0.0, 0.0],
                                  "quaternion": [0.0, 0.0, 0.0, 1.0]},
                0.0, [args.image] * 4)
            elapsed = time.perf_counter() - started
            record = {
                "step": step,
                "measured_index": measured_index,
                "seconds": elapsed,
                "shape": list(result.waypoints.shape),
                "finite": bool(np.isfinite(result.waypoints).all()),
                "cache_available": result.cache_available,
                "cuda_allocated_bytes": runtime._torch.cuda.memory_allocated(),
                "cuda_reserved_bytes": runtime._torch.cuda.memory_reserved(),
            }
            records.append(record)
            print(json.dumps(record, sort_keys=True), flush=True)
        reset_started = time.perf_counter()
        runtime.reset()
        reset_seconds = time.perf_counter() - reset_started
    fast = [record["seconds"] for record in records]
    summary = {
        "cycles": len(records),
        "finite_cycles": sum(record["finite"] for record in records),
        "shape_cycles": sum(record["shape"] == [1, 30, 2] for record in records),
        "first_generation_seconds": first_generation_seconds,
        "fast_mean_seconds": statistics.mean(fast),
        "fast_p95_seconds": percentile(fast, 95),
        "fast_p99_seconds": percentile(fast, 99),
        "reserved_growth_bytes": records[-1]["cuda_reserved_bytes"] - records[0]["cuda_reserved_bytes"],
        "reset_during_background_seconds": reset_seconds,
        "gate_pass": (len(records) == args.cycles and
                      all(record["finite"] and record["shape"] == [1, 30, 2]
                          for record in records) and percentile(fast, 95) <= 0.250),
        "claim_boundary": "offline replay async benchmark; no network sender or motor path",
    }
    args.output.write_text(json.dumps({"summary": summary, "records": records},
                                      indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    if not summary["gate_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

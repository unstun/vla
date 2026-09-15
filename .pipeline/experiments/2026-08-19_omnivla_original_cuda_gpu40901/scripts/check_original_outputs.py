#!/usr/bin/env python3
"""Validate an OmniVLA-original remote run bundle without loading the model."""

import json
import math
from pathlib import Path
import sys


def check(run: Path) -> list:
    failures = []
    outputs_path = run / "outputs.json"
    meta_path = run / "meta.json"
    guard_path = run / "vram_guard.txt"
    if not outputs_path.is_file():
        return ["outputs.json missing"]
    if not meta_path.is_file():
        return ["meta.json missing"]
    outputs = json.loads(outputs_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    waypoints = outputs.get("waypoints_raw")
    if not isinstance(waypoints, list) or len(waypoints) != 8:
        failures.append("waypoints_raw must have 8 rows")
    elif any(not isinstance(row, list) or len(row) != 4 for row in waypoints):
        failures.append("every waypoint row must have 4 values")
    else:
        flat = [value for row in waypoints for value in row]
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in flat):
            failures.append("waypoints_raw contains a non-finite or non-numeric value")

    if outputs.get("waypoints_raw_shape") != [8, 4]:
        failures.append("waypoints_raw_shape is not [8, 4]")
    if outputs.get("all_finite") is not True:
        failures.append("all_finite is not true")
    if outputs.get("cuda_memory_fraction_env") != "0.45":
        failures.append("recorded CUDA memory fraction is not 0.45")
    if not str(outputs.get("device", "")).startswith("cuda"):
        failures.append("model output device is not CUDA")

    velocity = outputs.get("linear_vel_limited")
    angular = outputs.get("angular_vel_limited")
    if not isinstance(velocity, (int, float)) or not math.isfinite(velocity):
        failures.append("limited linear velocity diagnostic is not finite")
    elif abs(velocity) > 0.3 + 1e-9:
        failures.append("limited linear velocity diagnostic exceeds 0.3")
    if not isinstance(angular, (int, float)) or not math.isfinite(angular):
        failures.append("limited angular velocity diagnostic is not finite")
    elif abs(angular) > 0.3 + 1e-9:
        failures.append("limited angular velocity diagnostic exceeds 0.3")

    if meta.get("exit_code") != 0:
        failures.append("model exit_code is not zero")
    if meta.get("preflight_minimum_free_mib", 0) < 24576:
        failures.append("preflight minimum free VRAM is below 24576 MiB")
    if meta.get("cuda_memory_fraction") != 0.45:
        failures.append("meta CUDA memory fraction is not 0.45")
    if not guard_path.is_file() or "required_mib=24576" not in guard_path.read_text():
        failures.append("VRAM guard record is missing or malformed")

    figures = tuple(run.glob("*.jpg"))
    if len(figures) != 1:
        failures.append("run must contain exactly one output figure")
    elif figures[0].stat().st_size <= 10240:
        failures.append("output figure is unexpectedly small")
    return failures


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_original_outputs.py RUN_DIR [RUN_DIR ...]", file=sys.stderr)
        return 64
    result = 0
    for argument in sys.argv[1:]:
        run = Path(argument)
        failures = check(run)
        print("=== %s ===" % run.name)
        if failures:
            result = 1
            for failure in failures:
                print("FAIL: %s" % failure)
        else:
            print("ALL CHECKS PASSED")
    return result


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import json
import math
import pathlib
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_outputs.py RUN_DIR")
    run_dir = pathlib.Path(sys.argv[1])
    payload = json.loads((run_dir / "outputs.json").read_text())
    waypoints = payload.get("waypoints_raw")
    if payload.get("waypoints_raw_shape") != [8, 4]:
        raise SystemExit("wrong declared waypoint shape")
    if not isinstance(waypoints, list) or len(waypoints) != 8:
        raise SystemExit("wrong waypoint row count")
    flat = []
    for row in waypoints:
        if not isinstance(row, list) or len(row) != 4:
            raise SystemExit("wrong waypoint column count")
        flat.extend(row)
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in flat):
        raise SystemExit("non-finite or non-numeric waypoint")
    if payload.get("all_finite") is not True:
        raise SystemExit("runner did not report finite output")
    if payload.get("device") != "cuda:0":
        raise SystemExit("runner did not use cuda:0")
    if payload.get("modality_id") != 7 or payload.get("modality_name") != "language only":
        raise SystemExit("unexpected modality")
    if payload.get("language_instruction") != "move forward":
        raise SystemExit("unexpected instruction")
    summary = {
        "validated": True,
        "shape": [8, 4],
        "all_finite": True,
        "device": payload["device"],
        "modality_id": payload["modality_id"],
        "language_instruction": payload["language_instruction"],
        "forward_seconds": payload["forward_seconds"],
    }
    (run_dir / "validation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

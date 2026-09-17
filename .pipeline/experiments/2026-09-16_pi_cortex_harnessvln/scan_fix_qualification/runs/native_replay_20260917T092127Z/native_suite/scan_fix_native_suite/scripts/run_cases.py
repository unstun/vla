#!/usr/bin/env python3
"""Run scan_fix_native_suite cases from a fixture JSON file.

Derived from scan_replan_diagnosis/native_repro/scan_replan_native_repro/scripts/run_cases.py
(sha256 d7fee684751120530b009c1b7c4857c897a9207c0eb6c47028f1fcee16ffca5f). A case without the new
suite fields produces exactly the original command. This script uses only the Python standard
library and expects the C++ executable to already be built inside the ROS/Foxy container.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def vec_arg(values: Iterable[Any]) -> str:
    vals = list(values)
    if len(vals) != 3:
        raise ValueError(f"expected 3-vector, got {vals!r}")
    return ",".join(str(float(v)) for v in vals)


def bool_arg(value: Any) -> str:
    return "true" if bool(value) else "false"


def offsets_arg(values: Iterable[Any]) -> str:
    vals = [float(v) for v in values]
    if not vals or any(v <= 0.0 for v in vals) or any(b <= a for a, b in zip(vals, vals[1:])):
        raise ValueError(f"follow-up offsets must be positive and strictly increasing, got {vals!r}")
    return ",".join(repr(v) for v in vals)


def build_command(executable: str, params_file: str, case: Dict[str, Any], samples: int,
                  fixtures_root: Optional[str] = None, print_samples: bool = True) -> List[str]:
    command = [
        executable,
        "--start", vec_arg(case["start"]),
        "--start-vel", vec_arg(case.get("start_velocity", [0, 0, 0])),
        "--start-acc", vec_arg(case.get("start_acceleration", [0, 0, 0])),
        "--target", vec_arg(case["target"]),
        "--target-vel", vec_arg(case.get("target_velocity", [0, 0, 0])),
        "--poly-init", bool_arg(case.get("poly_init", True)),
        "--random-poly", bool_arg(case.get("random_poly", False)),
        "--seed", str(int(case.get("seed", 0))),
        "--samples", str(samples),
    ]
    boxes = case.get("occupied_boxes")
    if boxes:
        path = Path(boxes)
        if not path.is_absolute():
            if fixtures_root is None:
                raise ValueError("relative occupied_boxes path requires fixtures_root")
            path = Path(fixtures_root) / path
        command += ["--occupied-boxes", str(path)]
    offsets = case.get("follow_up_offsets_s") or []
    if offsets:
        command += ["--follow-up-offsets", offsets_arg(offsets)]
    if case.get("dump_samples"):
        command += ["--dump-samples", "true"]
    if not print_samples:
        command += ["--print-samples", "false"]
    command += ["--ros-args", "--params-file", params_file]
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, help="Path to a fixture JSON with a 'runs' or 'cases' list")
    parser.add_argument("--params", required=True, help="ROS params YAML passed to scan_planner_node")
    parser.add_argument("--executable", required=True, help="Built rebound_replan_suite executable path")
    parser.add_argument("--samples", type=int, default=41)
    parser.add_argument("--case-id", action="append", default=[], help="Run only matching label/id; repeatable")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    doc = json.loads(cases_path.read_text())
    cases = doc.get("runs", doc.get("cases"))
    if not isinstance(cases, list):
        raise SystemExit("fixture JSON must contain a list at key 'runs' or 'cases'")
    wanted = set(args.case_id)
    selected = [c for c in cases if not wanted or c.get("label", c.get("id")) in wanted]
    if wanted and len(selected) != len(wanted):
        found = {c.get("label", c.get("id")) for c in selected}
        raise SystemExit(f"missing requested case ids: {sorted(wanted - found)}")

    overall = 0
    for case in selected:
        case_id = case.get("label", case.get("id", "<missing-id>"))
        cmd = build_command(args.executable, args.params, case, args.samples, str(cases_path.parent))
        print(f"CASE_BEGIN {case_id}", flush=True)
        print("COMMAND " + json.dumps(cmd), flush=True)
        if not args.dry_run:
            completed = subprocess.run(cmd, text=True)
            if completed.returncode != 0:
                overall = completed.returncode if overall == 0 else overall
            print(f"CASE_END {case_id} returncode={completed.returncode}", flush=True)
        else:
            print(f"CASE_END {case_id} dry_run=true", flush=True)
    return overall


if __name__ == "__main__":
    sys.exit(main())

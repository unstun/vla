#!/usr/bin/env python3
"""Run scan_replan_native_repro cases from the parent-provided JSON fixture.

This script intentionally uses only the Python standard library. It expects the
C++ executable to already be built inside the ROS/Foxy container.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


def vec_arg(values: Iterable[Any]) -> str:
    vals = list(values)
    if len(vals) != 3:
        raise ValueError(f"expected 3-vector, got {vals!r}")
    return ",".join(str(float(v)) for v in vals)


def bool_arg(value: Any) -> str:
    return "true" if bool(value) else "false"


def build_command(executable: str, params_file: str, case: Dict[str, Any], samples: int) -> List[str]:
    return [
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
        "--ros-args", "--params-file", params_file,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, help="Path to cases.json")
    parser.add_argument("--params", required=True, help="ROS params YAML passed to scan_planner_node")
    parser.add_argument("--executable", required=True, help="Built rebound_replan_repro executable path")
    parser.add_argument("--samples", type=int, default=41)
    parser.add_argument("--case-id", action="append", default=[], help="Run only matching case id; repeatable")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    args = parser.parse_args()

    doc = json.loads(Path(args.cases).read_text())
    cases = doc.get("cases")
    if not isinstance(cases, list):
        raise SystemExit("cases JSON must contain a list at key 'cases'")
    wanted = set(args.case_id)
    selected = [c for c in cases if not wanted or c.get("id") in wanted]
    if wanted and len(selected) != len(wanted):
        found = {c.get("id") for c in selected}
        raise SystemExit(f"missing requested case ids: {sorted(wanted - found)}")

    overall = 0
    for case in selected:
        case_id = case.get("id", "<missing-id>")
        cmd = build_command(args.executable, args.params, case, args.samples)
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

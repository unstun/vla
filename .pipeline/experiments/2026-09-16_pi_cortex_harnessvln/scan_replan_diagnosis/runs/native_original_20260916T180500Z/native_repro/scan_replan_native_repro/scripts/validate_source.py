#!/usr/bin/env python3
"""Local source-only validation for the native repro package."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[5]
CPP = ROOT / "src" / "rebound_replan_repro.cpp"
CMAKE = ROOT / "CMakeLists.txt"
PKG = ROOT / "package.xml"
CASES = REPO / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/inputs/cases.json"
PARAMS = REPO / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/inputs/planner.yaml"
SCAN = REPO / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/builds/scan_03/src/plan_manage/src/planner_manager.cpp"


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    for p in [CPP, CMAKE, PKG, CASES, PARAMS, SCAN]:
        require(p.exists(), f"missing {p}")
    cpp = CPP.read_text()
    cmake = CMAKE.read_text()
    scan = SCAN.read_text()
    require("manager.reboundReplan" in cpp, "C++ must call native manager.reboundReplan")
    require("PlanningVisualization" in cpp and "std::make_shared" in cpp, "C++ must create visualization")
    require("dynamics_only_empty_grid_no_clouds" in cpp, "C++ must label empty-grid isolation")
    require("POLY_INIT_END_DERIVATIVES" in cpp, "C++ must emit poly derivative diagnostics")
    require("std::srand(opt.seed);\n    const bool ok" in cpp, "C++ must reseed before native replan")
    require("${SCAN03_PLANNER_MANAGER_CPP}" in cmake, "CMake must compile selected planner_manager.cpp")
    require("SCAN03_SOURCE_ROOT" in cmake, "CMake must require scan_03 source root")
    require("SCAN_MANAGER_CPP" in cmake, "CMake must allow isolated instrumented manager source override")
    require("reboundReplan" in scan and "gl_traj.evaluateAcc(t)" in scan, "scan_03 source expected native replan pattern absent")
    cases = json.loads(CASES.read_text())
    require(cases.get("schema") == "scan_minimized_repro_cases_v1", "unexpected cases schema")
    require(len(cases.get("cases", [])) >= 4, "expected at least four cases")
    params = PARAMS.read_text()
    require("scan_planner_node:" in params, "planner params must be scoped to scan_planner_node")
    require("manager.max_vel: 1.0" in params, "planner params should carry accepted max_vel 1.0")
    require("manager.max_acc: 0.5" in params, "planner params should carry accepted max_acc 0.5")
    print("validate_source: OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"validate_source: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

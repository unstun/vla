#!/usr/bin/env python3
"""Local source-only validation for the native suite package."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT.parents[2]
CPP = ROOT / "src" / "rebound_replan_suite.cpp"
CMAKE = ROOT / "CMakeLists.txt"
PKG = ROOT / "package.xml"
PARAMS = EXPERIMENT / "scan_replan_diagnosis/inputs/planner.yaml"
SCAN = EXPERIMENT / "p2b_execution/builds/scan_03/src/plan_manage/src/planner_manager.cpp"


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    for p in [CPP, CMAKE, PKG, PARAMS]:
        require(p.exists(), f"missing {p}")
    cpp = CPP.read_text()
    cmake = CMAKE.read_text()
    require("manager.reboundReplan" in cpp, "C++ must call native manager.reboundReplan")
    require("PlanningVisualization" in cpp and "std::make_shared" in cpp, "C++ must create visualization")
    require("dynamics_only_empty_grid_no_clouds" in cpp, "C++ must keep the empty-grid label")
    require("MAP_CONDITION boxes=" in cpp and "setOccupied" in cpp, "C++ must mark boxes with setOccupied")
    require("rcl_set_ros_time_override" in cpp, "C++ must control the simulated clock for follow-ups")
    require("SUITE_CALL_BEGIN" in cpp and "SUITE_CALL_END" in cpp and "SUITE_PATH" in cpp, "C++ must emit suite records")
    require("POLY_INIT_END_DERIVATIVES" in cpp, "C++ must keep poly derivative diagnostics")
    require("std::srand(opt.seed);\n    print_call_begin(0, 0" in cpp, "C++ must reseed right before the first native replan")
    require("${SCAN03_PLANNER_MANAGER_CPP}" in cmake, "CMake must compile selected planner_manager.cpp")
    require("SCAN03_SOURCE_ROOT" in cmake and "SCAN_MANAGER_CPP" in cmake, "CMake must keep the manager override")
    require("file(SHA256" in cmake, "CMake must embed the manager hash")
    if SCAN.exists():
        scan = SCAN.read_text()
        require("reboundReplan" in scan and "gl_traj.evaluateAcc(t)" in scan, "scan_03 native replan pattern absent")
    params = PARAMS.read_text()
    require("scan_planner_node:" in params, "planner params must be scoped to scan_planner_node")
    require("use_sim_time: true" in params, "follow-up timing requires use_sim_time true")
    require("manager.max_acc: 0.5" in params, "planner params should carry accepted max_acc 0.5")
    print("validate_source: OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"validate_source: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

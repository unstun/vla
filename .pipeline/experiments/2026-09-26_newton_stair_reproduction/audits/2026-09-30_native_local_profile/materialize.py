"""Derive diagnostic-only timing scopes from exact frozen v36 native bytes."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
PARENT = BASE / "runtime/scan67_nav2_contract_v36"
NATIVE = HERE / "native_profile"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not NATIVE.exists()
    parent = json.loads((PARENT / "source_sha256.json").read_text())
    assert all(sha(PARENT / name) == value for name, value in parent.items())
    shutil.copytree(PARENT / "src", NATIVE / "src")
    patch = []
    scopes = {
        "src/plan_manage/src/scan_replan_fsm.cpp": [("bool SCANReplanFSM::planFromCurrentTraj()", 0)],
        "src/plan_manage/src/planner_manager.cpp": [("bool SCANPlannerManager::reboundReplanAttempt(", 1)],
        "src/bspline_opt/src/bspline_optimizer.cpp": [("bool BsplineOptimizer::rebound_optimize()", 2),
            ("void BsplineOptimizer::combineCostRebound(", 3), ("void BsplineOptimizer::calcDistanceCostRebound(", 4),
            ("bool BsplineOptimizer::check_collision_and_rebound(", 5)],
        "src/path_searching/src/dyn_a_star.cpp": [("ASTAR_RET AStar::AstarSearch(", 6)],
        "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc": [("int GridMap::reactiveOccupancy(", 7),
            ("bool GridMap::reactiveFootprintSupportQuery(", 9)],
        "src/plan_env/include/plan_env/reactive_collision.h": [("Verdict decide(", 10)],
        "src/bspline_opt/src/uniform_bspline.cpp": [("Eigen::VectorXd UniformBspline::evaluateDeBoor(", 11)],
    }
    for name, functions in scopes.items():
        path = NATIVE / name
        before = path.read_bytes()
        after = before
        for needle, index in functions:
            start = after.index(needle.encode())
            brace = after.index(b"{", start)
            after = after[:brace+1] + f"\n    local_profile::Scope profile_scope({index});".encode() + after[brace+1:]
        if name.endswith("scan_reactive_grid_methods.inc"):
            marker = b"      bool contributor = false;"
            assert after.count(marker) == 1
            after = after.replace(marker, b"      local_profile::Scope raw_profile_scope(8);\n" + marker)
        after = b"#include <plan_env/local_hotspot_profile.h>\n" + after
        path.write_bytes(after)
        patch += difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                     fromfile="a/"+name, tofile="b/"+name)
    cmake = NATIVE / "src/plan_env/CMakeLists.txt"
    before = cmake.read_text()
    after = before.replace("add_library(plan_env src/grid_map.cpp", "add_library(plan_env src/profile_state.cpp src/grid_map.cpp")
    assert after != before
    cmake.write_text(after)
    patch += difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile="a/src/plan_env/CMakeLists.txt", tofile="b/src/plan_env/CMakeLists.txt")
    shutil.copyfile(HERE / "local_hotspot_profile.h", NATIVE / "src/plan_env/include/plan_env/local_hotspot_profile.h")
    shutil.copyfile(HERE / "profile_state.cpp", NATIVE / "src/plan_env/src/profile_state.cpp")
    contract = HERE / "contract"
    contract.mkdir()
    for name in ("CMakeLists.txt", "performance_probe.cpp"):
        shutil.copyfile(BASE / "versions/v36/contract" / name, contract / name)
    cmake = contract / "CMakeLists.txt"
    text = cmake.read_text()
    start, end = text.index("add_executable(native_probe"), text.index("add_executable(performance_probe")
    cmake.write_text(text[:start] + text[end:])
    probe = contract / "performance_probe.cpp"
    text = probe.read_text()
    text = "#include <plan_env/local_hotspot_profile.h>\n" + text
    text = text.replace("  const auto budget_started =", "  local_profile::start();\n  const auto budget_started =")
    text = text.replace("  std::cout << \"V36_NATIVE_PLAN_BUDGET", "  local_profile::stop(); local_profile::report();\n  std::cout << \"V36_NATIVE_PLAN_BUDGET")
    probe.write_text(text)
    native = {str(p.relative_to(NATIVE)): sha(p) for p in (NATIVE / "src").rglob("*") if p.is_file()}
    (NATIVE / "source_sha256.json").write_text(json.dumps(native, indent=2) + "\n")
    (HERE / "profile_changes.patch").write_text("".join(patch))
    (HERE / "source_identity.json").write_text(json.dumps({"parent_native_source": parent,
        "profile_native_source": native, "diagnostic_only": True, "navigation_run": False,
        "claim": "Inclusive timer scopes; instrumentation overhead prevents using this as production speed acceptance."}, indent=2) + "\n")
    print(json.dumps({"parent_files": len(parent), "derived_native_files": len(native), "diagnostic_only": True}))


if __name__ == "__main__":
    main()

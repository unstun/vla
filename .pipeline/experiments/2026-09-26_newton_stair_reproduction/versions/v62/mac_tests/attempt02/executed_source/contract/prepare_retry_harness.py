"""Script solver outcomes while compiling the original retry/epoch control flow.

The fixture admits targets and replaces reboundReplanAttempt, not the calling
FSM, retry manager, timestamp capture, prefix budget or publication. It cannot
qualify occupancy, optimizer output, dynamics or real-time performance.
"""
from pathlib import Path
import hashlib
import json
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def closing_brace(source, start):
    depth = 0
    state = "code"
    i = start
    while i < len(source):
        c = source[i]
        pair = source[i:i + 2]
        if state == "line":
            if c == "\n":
                state = "code"
        elif state == "block":
            if pair == "*/":
                state = "code"
                i += 1
        elif state in ("string", "char"):
            if c == "\\":
                i += 1
            elif c == ('"' if state == "string" else "'"):
                state = "code"
        elif pair in ("//", "/*"):
            state = "line" if pair == "//" else "block"
            i += 1
        elif c in ('"', "'"):
            state = "string" if c == '"' else "char"
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("Unclosed source function")


def replace_body(source, signature, replacement):
    assert source.count(signature) == 1, signature
    start = source.index("{", source.index(signature))
    end = closing_brace(source, start)
    return source[:start] + "{\n" + replacement + "\n  }" + source[end + 1:]


def main():
    parent, candidate, destination, provenance = map(Path, sys.argv[1:])
    destination.mkdir(parents=True, exist_ok=False)
    hooks = """#pragma once
#include <plan_manage/scan_replan_fsm.h>
bool epoch_test_target(scan_planner::SCANReplanFSM *);
bool epoch_test_solve(scan_planner::SCANPlannerManager *,
    const Eigen::Vector3d &, const Eigen::Vector3d &, const Eigen::Vector3d &,
    const Eigen::Vector3d &, const Eigen::Vector3d &, bool &, bool *,
    const rclcpp::Time *);
"""
    records = {}
    for label, root in (("parent", parent), ("candidate", candidate)):
        out = destination / label
        out.mkdir()
        (out / "epoch_hooks.h").write_text(hooks)
        manager = root / "src/plan_manage/src/planner_manager.cpp"
        fsm = root / "src/plan_manage/src/scan_replan_fsm.cpp"
        manager_text = replace_body(manager.read_text(),
            "bool SCANPlannerManager::reboundReplanAttempt(",
            "    return epoch_test_solve(this, start_pt, start_vel, start_acc,\n"
            "        local_target_pt, local_target_vel, optimization_attempted,\n"
            "        used_warm_start, trajectory_origin);")
        fsm_text = replace_body(fsm.read_text(),
            "bool SCANReplanFSM::getLocalTarget()",
            "    return epoch_test_target(this);")
        fsm_text = replace_body(fsm_text,
            "int SCANReplanFSM::recoveryTargetOccupancy(", "    return 0;")
        for name, contents in (("planner_manager.cpp", manager_text),
                               ("scan_replan_fsm.cpp", fsm_text)):
            (out / name).write_text('#include "epoch_hooks.h"\n' + contents)
        records[label] = {
            "root": str(root),
            "original": {str(p.relative_to(root)): sha(p) for p in (manager, fsm)},
            "transformed": {p.name: sha(p) for p in out.iterdir()},
        }
    provenance.write_text(json.dumps({
        "scope": "Actual FSM/manager retry flow with scripted target admission and solver outcomes",
        "excluded_claims": ["occupancy", "stair support", "optimizer", "dynamics", "30 Hz", "tail latency"],
        "records": records,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()

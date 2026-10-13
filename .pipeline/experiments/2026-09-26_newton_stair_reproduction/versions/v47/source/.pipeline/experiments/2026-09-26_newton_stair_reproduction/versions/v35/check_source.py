"""Check the exact v34 delta and preserved planning/safety functions."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan65_evidence_floor_v34"
NEW = BASE / "runtime/scan66_periodic_replan_v35"
SOURCE = "src/plan_manage/src/scan_replan_fsm.cpp"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
old = json.loads((OLD / "source_sha256.json").read_text())
new = json.loads((NEW / "source_sha256.json").read_text())
assert all(sha(OLD / name) == digest for name, digest in old.items())
assert all(sha(NEW / name) == digest for name, digest in new.items())
assert set(old) == set(new)
changed = sorted(name for name in new if new[name] != old[name])
assert changed == sorted([SOURCE, "src/plan_manage/include/plan_manage/scan_replan_fsm.h"])
with tempfile.TemporaryDirectory(prefix="v35-patch-") as temp:
    temp = Path(temp)
    shutil.copytree(HERE / "parent_source", temp, dirs_exist_ok=True)
    result = subprocess.run(["patch", "-p1", "-i", str(HERE / "changes.patch")],
                            cwd=temp, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    patch_reproduces = {name: sha(temp / name) == new[name] for name in changed}
    patch_reproduces.update({name: sha(temp / name) == sha(HERE / name)
                            for name in ("building_planner.yaml", "flat_planner.yaml")})
    assert all(patch_reproduces.values())


def section(path, begin, end):
    data = path.read_bytes()
    return data[data.index(begin.encode()):data.index(end.encode(), data.index(begin.encode()) + 1)]


boundaries = {
    "PVA_and_native_replan": ("  bool SCANReplanFSM::planFromCurrentTraj()", "  void SCANReplanFSM::setStartStateFromOdomOrCurrentTraj()"),
    "collision_safety": ("  void SCANReplanFSM::checkCollisionCallback()", "  bool SCANReplanFSM::callReboundReplan("),
    "complete_planner_and_publication": ("  bool SCANReplanFSM::callReboundReplan(", "  bool SCANReplanFSM::callEmergencyStop("),
    "emergency_stop_publication": ("  bool SCANReplanFSM::callEmergencyStop(", "  bool SCANReplanFSM::getLocalTarget()"),
    "exhausted_retry_stop": ("  void SCANReplanFSM::finishProcess()", "  bool SCANReplanFSM::planFromCurrentTraj()"),
}
preserved = {name: section(OLD / SOURCE, *bounds) == section(NEW / SOURCE, *bounds)
             for name, bounds in boundaries.items()}
assert all(preserved.values())
parent = json.loads((HERE.parent / "v34/manifest.json").read_text())
parent_current = all(sha(ROOT / name) == digest for name, digest in parent["source_files"].items())
parent_snapshot = all(sha(HERE.parent / "v34/source" / name) == digest for name, digest in parent["source_files"].items())
assert parent_current and parent_snapshot
result = {"passed": True, "native_source_files": len(new), "changed_native_files": changed,
          "unchanged_native_files": len(new) - len(changed), "patch_reproduces": patch_reproduces,
          "byte_exact_preserved_functions": preserved,
          "frozen_parent_files": len(parent["source_files"]),
          "frozen_parent_current_matches": parent_current, "frozen_parent_snapshot_matches": parent_snapshot,
          "native_build_passed": json.loads((NEW / "build_result.json").read_text())["passed"]}
assert result["native_build_passed"]
(HERE / "source_checks.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))

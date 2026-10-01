"""Derive v35 from hash-verified frozen v34; preserve exact parent bytes."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan65_evidence_floor_v34"
NEW = BASE / "runtime/scan66_periodic_replan_v35"
HEADER = "src/plan_manage/include/plan_manage/scan_replan_fsm.h"
SOURCE = "src/plan_manage/src/scan_replan_fsm.cpp"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


EDITS = {
    HEADER: [
        ("    double no_replan_thresh_, replan_thresh_;\n",
         "    double no_replan_thresh_, replan_thresh_;\n"
         "    double replan_frequency_{0.0}; // Zero preserves legacy distance scheduling.\n"
         "    double last_nominal_replan_s_{-1.0}; // ROS clock; attempt start, not completion.\n"),
        ("    void execFSMCallback();\n",
         "    bool nominalReplanDue(bool mark_attempt);\n    void execFSMCallback();\n"),
    ],
    SOURCE: [
        ('    replan_thresh_ = load_parameter<double>(node_, "fsm.thresh_replan", -1.0);\n',
         '    replan_frequency_ = load_parameter<double>(node_, "fsm.replan_frequency", 0.0);\n'
         '    if (!std::isfinite(replan_frequency_) || replan_frequency_ < 0.0 ||\n'
         '        replan_frequency_ > 100.0 ||\n'
         '        (replan_frequency_ > 0.0 && !std::isfinite(1.0 / replan_frequency_)))\n'
         '      throw std::runtime_error("fsm.replan_frequency must be zero or a finite frequency in (0, 100] Hz");\n'
         '    last_nominal_replan_s_ = -1.0;\n'
         '    replan_thresh_ = load_parameter<double>(node_, "fsm.thresh_replan", -1.0);\n'),
        ("  void SCANReplanFSM::execFSMCallback()\n",
         """  bool SCANReplanFSM::nominalReplanDue(bool mark_attempt)
  {
    if (replan_frequency_ <= 0.0) return true;
    const double now_s = node_->now().seconds();
    // A reset starts a fresh interval. Paused time and missed periods never
    // create a catch-up queue; each actual attempt records its current start.
    if (last_nominal_replan_s_ >= 0.0 && now_s < last_nominal_replan_s_)
    {
      last_nominal_replan_s_ = now_s;
      return false;
    }
    if (last_nominal_replan_s_ >= 0.0 &&
        now_s - last_nominal_replan_s_ + 1e-9 < 1.0 / replan_frequency_)
      return false;
    if (mark_attempt)
    {
      last_nominal_replan_s_ = now_s;
      RCLCPP_INFO(node_->get_logger(), "nominal_replan frequency_hz=%.6f start_ros_s=%.9f state=%d",
                  replan_frequency_, now_s, static_cast<int>(exec_state_));
    }
    return true;
  }

  void SCANReplanFSM::execFSMCallback()
"""),
        ("    case GEN_NEW_TRAJ:\n    {\n      setStartStateFromOdomOrCurrentTraj();\n",
         "    case GEN_NEW_TRAJ:\n    {\n      if (!nominalReplanDue(true)) break;\n"
         "      setStartStateFromOdomOrCurrentTraj();\n"),
        ("    case REPLAN_TRAJ:\n    {\n\n      if (planFromCurrentTraj())\n",
         "    case REPLAN_TRAJ:\n    {\n      if (!nominalReplanDue(true)) break;\n\n"
         "      if (planFromCurrentTraj())\n"),
        ("      else if ((info->start_pos_ - pos).norm() < replan_thresh_)\n",
         """      else if (replan_frequency_ > 0.0)
      {
        // Periodic scheduling replaces the displacement trigger. The controller
        // continues the accepted curve; safety replanning has its own callback.
        if (!go2_execution_frozen_ && nominalReplanDue(false))
          changeFSMExecState(REPLAN_TRAJ, "PERIODIC");
      }
      else if ((info->start_pos_ - pos).norm() < replan_thresh_)
"""),
    ],
}


def main():
    assert not NEW.exists() and not (HERE / "prepared.json").exists()
    frozen = json.loads((HERE.parent / "v34/manifest.json").read_text())
    for name, digest in frozen["source_files"].items():
        assert sha(ROOT / name) == digest, name
        assert sha(HERE.parent / "v34/source" / name) == digest, name
    parent = json.loads((OLD / "source_sha256.json").read_text())
    for name, digest in parent.items():
        assert sha(OLD / name) == digest, name
    shutil.copytree(OLD / "src", NEW / "src")
    patch = []
    for name, edits in EDITS.items():
        path = NEW / name
        before = path.read_bytes()
        after = before
        for old, new in edits:
            # FSM files use one line-ending style; preserve it without rewriting.
            eol = b"\r\n" if b"\r\n" in before else b"\n"
            old_bytes = old.encode().replace(b"\n", eol)
            new_bytes = new.encode().replace(b"\n", eol)
            assert after.count(old_bytes) == 1, (name, old[:80])
            after = after.replace(old_bytes, new_bytes, 1)
        preimage = HERE / "parent_source" / name
        preimage.parent.mkdir(parents=True, exist_ok=True)
        preimage.write_bytes(before)
        path.write_bytes(after)
        patch.extend(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                         fromfile="v34/" + name, tofile="v35/" + name))
    for name in ("building_planner.yaml", "flat_planner.yaml"):
        before = (HERE.parent / "v34" / name).read_bytes()
        anchor = b"    fsm.thresh_replan: 1.0\n"
        assert before.count(anchor) == 1
        after = before.replace(anchor, anchor + b"    fsm.replan_frequency: 2.0\n")
        (HERE / name).write_bytes(after)
        (HERE / "parent_source" / name).write_bytes(before)
        patch.extend(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                         fromfile="v34/" + name, tofile="v35/" + name))
    (HERE / "changes.patch").write_bytes("".join(patch).encode())
    manifest = {str(p.relative_to(NEW)): sha(p) for p in sorted((NEW / "src").rglob("*")) if p.is_file()}
    assert set(manifest) == set(parent)
    assert {name for name in manifest if manifest[name] != parent[name]} == set(EDITS)
    (NEW / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (HERE / "native_source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    identity = {
        "version": "v35", "parent": "v34", "status": "unfrozen_candidate",
        "native_build": str(NEW.relative_to(ROOT)), "native_parent": str(OLD.relative_to(ROOT)),
        "source_sha256": manifest, "changed_native_files": list(EDITS), "replan_frequency_hz": 2.0,
        "frozen_parent_files_verified": len(frozen["source_files"]),
        "claim": "Unvalidated scheduling candidate; no new physics run or navigation acceptance.",
    }
    (HERE / "prepared.json").write_text(json.dumps(identity, indent=2) + "\n")
    print(json.dumps({key: value for key, value in identity.items() if key != "source_sha256"}, indent=2))


if __name__ == "__main__":
    main()

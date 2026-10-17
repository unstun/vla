"""Create one hash-gated candidate with shared resolution-aware progress."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

BASE = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = BASE / "runtime/scan44_height_v5"
TARGET = BASE / "runtime/scan45_progress_v6"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(data, old, new):
    if data.count(old) != 1:
        raise ValueError("Pinned progress anchor mismatch: " + repr(old))
    return data.replace(old, new)


def main():
    for name in ("source_sha256.json", "install_sha256.json"):
        for path, expected in json.loads((SOURCE / name).read_text()).items():
            if sha(SOURCE / path) != expected:
                raise ValueError("Parent identity changed: " + path)
    TARGET.mkdir(exist_ok=False)
    shutil.copytree(SOURCE / "src", TARGET / "src")
    cpp = TARGET / "src/plan_manage/src/planner_manager.cpp"
    header = TARGET / "src/plan_manage/include/plan_manage/planner_manager.h"
    fsm = TARGET / "src/plan_manage/src/scan_replan_fsm.cpp"

    data = cpp.read_bytes()
    data = replace(data, b"#include <iomanip>", b"#include <cmath>\n#include <iomanip>")
    anchor = b'    pp_.planning_horizon_ = get_double("manager.planning_horizon", 5.0);'
    addition = b'''
    if (!node->has_parameter("manager.resolution_aware_progress"))
      node->declare_parameter<bool>("manager.resolution_aware_progress", false);
    resolution_aware_progress_ = node->get_parameter("manager.resolution_aware_progress").as_bool();
    RCLCPP_INFO(node->get_logger(), "local_progress_mode=%s",
                resolution_aware_progress_ ? "map_resolution" : "legacy_0.2m");'''
    data = replace(data, anchor, anchor + addition)
    anchor = b"  // SECTION rebond replanning\r\n"
    helper = b'''  bool SCANPlannerManager::hasLocalTranslation(const Eigen::Vector3d &start,
                                               const Eigen::Vector3d &target) const
  {
    if (!start.allFinite() || !target.allFinite()) return false;
    if (!resolution_aware_progress_) return (target - start).norm() >= 0.2;
    if (!grid_map_ || !grid_map_->isInMap(start) || !grid_map_->isInMap(target)) return false;
    const double resolution = grid_map_->getResolution();
    if (!std::isfinite(resolution) || resolution <= 0.0) return false;
    // Nav2 Smac 3c3db59 distinguishes same-cell and translated goals. Require
    // a full resolution as well so a tiny cross-boundary move is not progress.
    const double translation_cells = (target - start).head<2>().norm() / resolution;
    if (translation_cells + 1e-9 < 1.0) return false;
    Eigen::Vector3i start_cell, target_cell;
    grid_map_->posToIndex(start, start_cell);
    grid_map_->posToIndex(target, target_cell);
    return start_cell.x() != target_cell.x() || start_cell.y() != target_cell.y();
  }

'''
    data = replace(data, anchor, helper + anchor)
    data = replace(data, b"if ((start_pt - local_target_pt).norm() < 0.2)",
                   b"if (!hasLocalTranslation(start_pt, local_target_pt))")
    cpp.write_bytes(data)

    data = header.read_bytes()
    anchor = b"    /* main planning interface */\r\n"
    data = replace(data, anchor, anchor + b"    bool hasLocalTranslation(const Eigen::Vector3d &start, const Eigen::Vector3d &target) const;\n")
    data = replace(data, b"    rclcpp::Node *node_{nullptr};",
                   b"    rclcpp::Node *node_{nullptr};\n    bool resolution_aware_progress_{false};")
    header.write_bytes(data)

    data = fsm.read_bytes()
    for old, new in (
        (b"(path.back() - start_pt_).norm() >= 0.2",
         b"planner_manager_->hasLocalTranslation(start_pt_, path.back())"),
        (b"(candidate - start_pt_).norm() < 0.2",
         b"!planner_manager_->hasLocalTranslation(start_pt_, candidate)"),
        (b"(local_target_pt_ - start_pt_).norm() < 0.2",
         b"!planner_manager_->hasLocalTranslation(start_pt_, local_target_pt_)"),
    ):
        data = replace(data, old, new)
    fsm.write_bytes(data)

    manifest = {str(p.relative_to(TARGET)): sha(p)
                for p in (TARGET / "src").rglob("*") if p.is_file()}
    (TARGET / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    identity = {"source_sha256": manifest, "baseline": str(SOURCE),
                "integration_version": "v6",
                "change": "Optional shared resolution-aware local translation; legacy finite-input behavior preserved by default"}
    (BASE / "repairs/2026-09-26_generic_occupancy/candidate45_progress_v6_identity.json").write_text(
        json.dumps(identity, indent=2) + "\n")
    diff = []
    for path in (cpp, header, fsm):
        relative = path.relative_to(TARGET)
        diff.extend(difflib.unified_diff(
            (SOURCE / relative).read_text().splitlines(True), path.read_text().splitlines(True),
            fromfile="v5/" + str(relative), tofile="v6/" + str(relative), n=0))
    (HERE / "native_changes.patch").write_text("".join(diff))
    shutil.copyfile(__file__, TARGET / "executed_materialize.py")
    print(json.dumps({"candidate": str(TARGET), "source_files": len(manifest),
                      "changed_files": [str(p.relative_to(TARGET)) for p in (cpp, header, fsm)]}))


if __name__ == "__main__":
    main()

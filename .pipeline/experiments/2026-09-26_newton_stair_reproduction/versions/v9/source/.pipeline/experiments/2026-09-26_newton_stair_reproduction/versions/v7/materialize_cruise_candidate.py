"""Create a hash-gated SCAN candidate for a minimum planned cruise speed."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

BASE = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = BASE / "runtime/scan45_progress_v6"
TARGET = BASE / "runtime/scan46_cruise_v7"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(data, old, new):
    if data.count(old) != 1:
        raise ValueError("Pinned cruise anchor mismatch: " + repr(old))
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
    helper = TARGET / "src/plan_manage/include/plan_manage/minimum_cruise.h"
    shutil.copyfile(HERE / helper.name, helper)
    data = header.read_bytes()
    data = replace(data, b"    bool resolution_aware_progress_{false};",
                   b"    bool resolution_aware_progress_{false};\n    double min_cruise_speed_{0.0};")
    anchor = b"    bool checkDynamicFeasibility(UniformBspline position_traj);"
    data = replace(data, anchor, anchor + b'''
    bool enforceMinimumCruise(UniformBspline &curve,
                             vector<Eigen::Vector3d> &boundary, double &interval);
''')
    header.write_bytes(data)
    data = cpp.read_bytes()
    data = replace(data, b"#include <plan_manage/planner_manager.h>",
                   b"#include <plan_manage/planner_manager.h>\n#include <plan_manage/minimum_cruise.h>")
    anchor = b'    pp_.max_jerk_ = get_double("manager.max_jerk", -1.0);'
    data = replace(data, anchor, anchor + b'''
    min_cruise_speed_ = get_double("manager.min_cruise_speed", 0.0);
    if (!std::isfinite(min_cruise_speed_) || min_cruise_speed_ < 0.0 ||
        (min_cruise_speed_ > 0.0 &&
         (!std::isfinite(pp_.max_vel_) || min_cruise_speed_ > pp_.max_vel_ ||
          !std::isfinite(pp_.max_acc_) || pp_.max_acc_ <= 0.0 ||
          !std::isfinite(pp_.max_jerk_) || pp_.max_jerk_ <= 0.0)))
      throw std::runtime_error("Invalid minimum cruise speed or nominal dynamic limits");
    RCLCPP_INFO(node_->get_logger(), "minimum_planned_cruise_speed=%.3f m/s; boundary ramps and stops exempt",
                min_cruise_speed_);
''')
    anchor = b"    // A later native soft refit may change PVA. Reject that drift rather than"
    data = replace(data, anchor, b'''    if (flag_step_2_success && min_cruise_speed_ > 0.0) {
      flag_step_2_success = enforceMinimumCruise(pos, start_end_derivatives, ts);
      if (flag_step_2_success) capture_curve("minimum_cruise_checked");
    }

''' + anchor)
    anchor = b"  bool SCANPlannerManager::reparamBspline("
    implementation = b'''  bool SCANPlannerManager::enforceMinimumCruise(
      UniformBspline &curve, vector<Eigen::Vector3d> &boundary, double &interval)
  {
    if (min_cruise_speed_ == 0.0) return true;
    for (int attempt = 0; attempt <= 3; ++attempt) {
      const auto report = measureMinimumCruise(curve, min_cruise_speed_, pp_.max_acc_, pp_.max_jerk_);
      RCLCPP_INFO(node_->get_logger(),
          "minimum_cruise_check attempt=%d valid=%d passed=%d samples=%d min=%.9f requested=%.9f length=%.9f entry=%.9f exit=%.9f dt=%.9f",
          attempt, report.valid, report.passed, report.cruise_samples, report.minimum_speed,
          min_cruise_speed_, report.path_length, report.entry_distance, report.exit_distance, report.sample_dt);
      if (!report.valid) return false;
      if (report.passed) return true;
      if (attempt == 3 || report.minimum_speed <= 1e-6) break;
      // Reuse SCAN's native knot reallocation, boundary-PVA fit and refinement.
      // Limit each compression step; no downstream command-floor override.
      const double ratio = std::clamp(0.98 * report.minimum_speed / min_cruise_speed_, 0.7, 0.98);
      Eigen::MatrixXd controls;
      if (!refineTrajAlgo(curve, boundary, ratio, interval, controls)) return false;
      curve = UniformBspline(controls, 3, interval);
      curve.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);
      double feasibility_ratio = 0.0;
      if (!curve.checkFeasibility(feasibility_ratio, false) || !checkDynamicFeasibility(curve)) {
        RCLCPP_WARN(node_->get_logger(), "minimum_cruise_dynamic_limit_rejected");
        return false;
      }
    }
    RCLCPP_WARN(node_->get_logger(), "minimum_cruise_unreachable; no slower cruise published");
    return false;
  }

'''
    data = replace(data, anchor, implementation + anchor)
    cpp.write_bytes(data)
    changed = [cpp, header, helper]
    manifest = {str(p.relative_to(TARGET)): sha(p)
                for p in sorted((TARGET / "src").rglob("*")) if p.is_file()}
    (TARGET / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    diff = []
    for path in changed:
        relative = path.relative_to(TARGET)
        parent = SOURCE / relative
        diff.extend(difflib.unified_diff(
            parent.read_text().splitlines(True) if parent.exists() else [],
            path.read_text().splitlines(True),
            fromfile="v6/" + str(relative), tofile="v7/" + str(relative), n=3))
    (HERE / "native_changes.patch").write_text("".join(diff))
    shutil.copyfile(__file__, TARGET / "executed_materialize.py")
    print(json.dumps({"candidate": str(TARGET), "source_files": len(manifest),
                      "changed_files": [str(p.relative_to(TARGET)) for p in changed]}))


if __name__ == "__main__":
    main()

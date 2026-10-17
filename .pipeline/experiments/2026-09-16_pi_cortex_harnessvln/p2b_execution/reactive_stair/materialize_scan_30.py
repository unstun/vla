"""Use the same complete curve predicate in optimizer and manager acceptance."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_29"
OUT = HERE.parent / "builds/scan_30"


def check_call(indent):
    lines = '''const auto collision = reactive_stair::checkFullCubicTrajectory(
    traj, 0.0, grid_map_->getResolution(), GridMap::collision_heading_lookahead_s,
    [this](const Eigen::Vector3d& p, const Eigen::Vector3d& ahead, const Eigen::Vector3d& v) {
      return grid_map_->collisionTrajectoryYaw(p, ahead, v);
    }, [this](const Eigen::Vector3d& p, double yaw) { return grid_map_->getInflateOccupancy(p, yaw) != 0; });'''
    return "\n".join(indent + line for line in lines.splitlines())


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((BASE / "build_result.json").read_text())["passed"]:
        raise ValueError("scan29 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    source = OUT / "src/bspline_opt/src/bspline_optimizer.cpp"
    source.write_bytes(b"#include <bspline_opt/full_trajectory_collision.h>\n" + source.read_bytes())
    text = source.read_text()
    start = text.index("        double tm, tmp;", text.index("  bool BsplineOptimizer::rebound_optimize()"))
    end = text.index("        if (!flag_occ)", start)
    old = text[start:end]
    # Retain the original early-collision failure/diagnostic branch.
    early = old[old.index("            static bool diagnosed_initial_collision"):
                old.index("            break;")]
    replacement = check_call("        ") + '''
        RCLCPP_INFO(rclcpp::get_logger("bspline_opt"),
                    "optimizer_full_curve stage=rebound status=%d first_t=%.12f duration=%.12f samples=%zu control_sqnorm=%.17g",
                    static_cast<int>(collision.status), collision.first_time_s, collision.duration_s,
                    collision.samples, cps_.points.squaredNorm());
        if (!collision.clear() && collision.status != reactive_stair::TrajectoryCheckStatus::Collision)
          return false; // Invalid geometry/time or exhausted sample budget is not a repairable collision.
        flag_occ = !collision.clear();
        if (flag_occ) {
          const double t = collision.first_time_s;
          const Eigen::Vector3d pos = traj.evaluateDeBoorT(t);
          const Eigen::Vector3d ahead = traj.evaluateDeBoorT(std::min(t + GridMap::collision_heading_lookahead_s, collision.duration_s));
          const double spline_yaw = grid_map_->collisionTrajectoryYaw(pos, ahead, traj.getDerivative().evaluateDeBoorT(t));
''' + early + '''        }

'''
    once(source, old, replacement)
    text = source.read_text()
    start = text.index("      double tm, tmp;", text.index("  bool BsplineOptimizer::refine_optimize()"))
    end = text.index("      if (!flag_safe)", start)
    once(source, text[start:end], check_call("      ") + '''
      flag_safe = collision.clear();
      RCLCPP_INFO(rclcpp::get_logger("bspline_opt"),
                  "optimizer_full_curve stage=refine status=%d first_t=%.12f duration=%.12f samples=%zu control_sqnorm=%.17g",
                  static_cast<int>(collision.status), collision.first_time_s, collision.duration_s,
                  collision.samples, cps_.points.squaredNorm());

''')
    once(source, "    int restart_nums = 0, rebound_times = 0;", '''    const auto valid_constraint_count = [&]() {
      size_t count = 0;
      for (int i = 0; i < cps_.size; ++i) {
        if (!reactive_stair::validReboundSlot(cps_, i) || cps_.base_point[i].size() != cps_.direction[i].size()) continue;
        for (size_t j = 0; j < cps_.base_point[i].size(); ++j)
          if (cps_.base_point[i][j].allFinite() && cps_.direction[i][j].allFinite() &&
              std::abs(cps_.direction[i][j].norm() - 1.0) <= 1e-6) ++count;
      }
      return count;
    };
    int restart_nums = 0, rebound_times = 0;''')
    once(source, "          restart_nums++;\n          initControlPoints(cps_.points, false);", '''          restart_nums++;
          const size_t constraints_before = valid_constraint_count();
          initControlPoints(cps_.points, false);
          RCLCPP_INFO(rclcpp::get_logger("bspline_opt"),
                      "optimizer_collision_retry attempt=%d valid_constraints_before=%zu valid_constraints_after=%zu",
                      restart_nums, constraints_before, valid_constraint_count());''')
    (OUT / "optimizer_curve_contract_manifest.json").write_text(json.dumps({
        "base": BASE.name, "base_manifest_sha256": sha(BASE / "source_sha256.json"),
        "changed_sha256": {str(source.relative_to(OUT)): sha(source)}, "generator_sha256": sha(Path(__file__)),
        "change": "Rebound and refinement only report curve-clear success after existing checkFullCubicTrajectory over the entire curve. Non-collision invalid/budget statuses fail. Rebound true collisions retain existing bounded restart and early-time failure. Log actual paired finite constraint counts around restart.",
        "preserved": "Curve helper/sample budget, .8s execution heading, map/Unknown/height limits, initial-guidance behavior, objective/gradients/weights/retry bounds, manager final PVA/dynamics/full-curve gate.",
        "boundary": "Acceptance consistency repair. Existing control-polygon guidance may still fail to generate constraints for a sampled curve-pose collision; no moving-output or live-motion claim."
    }, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()

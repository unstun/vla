"""Compare curve position, footprint heading and native-derived time scaling."""
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
sys.path.insert(0, str(P2B / "reactive_stair"))
from materialize_scan_20 import once, sha


def main():
    base = P2B / "builds/scan_27"
    out = P2B / "builds/scan27_curve_pose_time_probe"
    if out.exists():
        raise FileExistsError(out)
    expected = json.loads((base / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(base / "src").as_posix(): sha(p)
              for p in (base / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((base / "build_result.json").read_text())["passed"]:
        raise ValueError("scan_27 source/build identity gate failed")
    shutil.copytree(base / "src", out / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manager = out / "src/plan_manage/src/planner_manager.cpp"
    once(manager, "    UniformBspline::parameterizeToBspline(ts, point_set, start_end_derivatives, ctrl_pts);", '''    UniformBspline::parameterizeToBspline(ts, point_set, start_end_derivatives, ctrl_pts);
    static bool curve_pose_time_probe_emitted = false;
    const bool curve_pose_time_probe_pending = !curve_pose_time_probe_emitted;
    const Eigen::MatrixXd curve_probe_initial_controls = curve_pose_time_probe_pending ? ctrl_pts : Eigen::MatrixXd();''')
    once(manager, "    if (!flag_step_1_success)\n    {", '''    if (!flag_step_1_success)
    {
      if (curve_pose_time_probe_pending) {
        curve_pose_time_probe_emitted = true;
        // Original optimizer already returned false. Every result below is
        // diagnostic only; this branch still returns false without publishing.
        const auto observe = [&](const char* label, UniformBspline curve) {
          const auto started = std::chrono::steady_clock::now();
          const auto check = reactive_stair::checkFullCubicTrajectory(
              curve, 0.0, grid_map_->getResolution(), GridMap::collision_heading_lookahead_s,
              [this](const Eigen::Vector3d& p, const Eigen::Vector3d& next, const Eigen::Vector3d& v) {
                return grid_map_->collisionTrajectoryYaw(p, next, v);
              }, [this](const Eigen::Vector3d& p, double yaw) { return grid_map_->getInflateOccupancy(p, yaw) != 0; });
          const double check_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - started).count();
          RCLCPP_WARN(node_->get_logger(), "CURVE_PROBE curve=%s status=%d first_t=%.12f duration=%.12f samples=%zu check_wall_ms=%.6f",
                      label, static_cast<int>(check.status), check.first_time_s, check.duration_s, check.samples, check_ms);
          if (check.status != reactive_stair::TrajectoryCheckStatus::Clear &&
              check.status != reactive_stair::TrajectoryCheckStatus::Collision) return;
          auto velocity = curve.getDerivative();
          auto acceleration = velocity.getDerivative();
          curve.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);
          double time_ratio = 0.0;
          const bool feasible = curve.checkFeasibility(time_ratio, false);
          const auto p0 = curve.evaluateDeBoorT(0.0), v0 = velocity.evaluateDeBoorT(0.0), a0 = acceleration.evaluateDeBoorT(0.0);
          RCLCPP_WARN(node_->get_logger(), "CURVE_PROBE dynamics=%s feasible=%d native_ratio=%.12f velocity_component_bound=%.12f acceleration_component_bound=%.12f start_position_error=%.12f start_velocity_error=%.12f start_acceleration_error=%.12f",
                      label, feasible, time_ratio, velocity.getControlPoint().cwiseAbs().maxCoeff(),
                      acceleration.getControlPoint().cwiseAbs().maxCoeff(),
                      (p0 - start_pt).norm(), (v0 - start_vel).norm(), (a0 - start_acc).norm());
          if (check.status != reactive_stair::TrajectoryCheckStatus::Collision) return;
          const auto p = curve.evaluateDeBoorT(check.first_time_s);
          const auto ahead = curve.evaluateDeBoorT(std::min(check.first_time_s + GridMap::collision_heading_lookahead_s, check.duration_s));
          const double curve_yaw = grid_map_->collisionTrajectoryYaw(p, ahead, velocity.evaluateDeBoorT(check.first_time_s));
          size_t parent = seed_path.size();
          double nearest_distance = std::numeric_limits<double>::infinity();
          Eigen::Vector3d nearest = Eigen::Vector3d::Zero();
          for (size_t i = 1; i < seed_path.size(); ++i) {
            const auto delta = seed_path[i] - seed_path[i - 1];
            if (delta.squaredNorm() <= 0.0) continue;
            const double u = std::min(1.0, std::max(0.0, (p - seed_path[i - 1]).dot(delta) / delta.squaredNorm()));
            const Eigen::Vector3d candidate = seed_path[i - 1] + u * delta;
            if ((candidate - p).norm() < nearest_distance) {
              nearest_distance = (candidate - p).norm(); nearest = candidate; parent = i;
            }
          }
          if (parent == seed_path.size()) return;
          const double parent_yaw = grid_map_->collisionSegmentYaw(seed_path[parent - 1], seed_path[parent]);
          const int same_position_parent_yaw = grid_map_->getInflateOccupancy(p, parent_yaw);
          const int projected_position_curve_yaw = grid_map_->getInflateOccupancy(nearest, curve_yaw);
          const int projected_position_parent_yaw = grid_map_->getInflateOccupancy(nearest, parent_yaw);
          RCLCPP_WARN(node_->get_logger(), "CURVE_PROBE paired=%s parent_edge=%zu distance=%.12f p=(%.12f,%.12f,%.12f) projected=(%.12f,%.12f,%.12f) curve_yaw=%.12f parent_yaw=%.12f same_position_parent_occupied=%d projected_curve_occupied=%d projected_parent_occupied=%d",
                      label, parent, nearest_distance, p.x(), p.y(), p.z(), nearest.x(), nearest.y(), nearest.z(),
                      curve_yaw, parent_yaw, same_position_parent_yaw, projected_position_curve_yaw, projected_position_parent_yaw);
          RCLCPP_WARN(node_->get_logger(), "CURVE_PROBE footprint=%s variant=curve_position_curve_heading", label);
          grid_map_->logInitialSplineCollision(p, curve_yaw);
          RCLCPP_WARN(node_->get_logger(), "CURVE_PROBE footprint=%s variant=curve_position_parent_heading", label);
          grid_map_->logInitialSplineCollision(p, parent_yaw);
        };
        UniformBspline initial(curve_probe_initial_controls, 3, ts);
        observe("initial", initial);
        observe("optimized", UniformBspline(ctrl_pts, 3, ts));
        initial.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);
        double required_ratio = 0.0;
        const bool feasible = initial.checkFeasibility(required_ratio, false);
        if (!feasible && std::isfinite(required_ratio) && required_ratio > 1.0) {
          // All knots, not the native partial-knot lengthenTime operation.
          // This preserves centerline geometry but rescales PVA and preview yaw.
          const double ratio = required_ratio * (1.0 + 1e-6);
          auto knots = initial.getKnot();
          knots *= ratio;
          initial.setKnot(knots);
          RCLCPP_WARN(node_->get_logger(), "CURVE_PROBE time_scale=%.12f source=native_derivative_bounds diagnostic_only=1", ratio);
          observe("initial_time_scaled", initial);
        }
      }''')
    (out / "curve_pose_time_probe_manifest.json").write_text(json.dumps({
        "base": "scan_27", "base_source_manifest_sha256": sha(base / "source_sha256.json"),
        "changed_sha256": {str(manager.relative_to(out)): sha(manager)},
        "generator_sha256": sha(Path(__file__)),
        "claim": "After the original first optimizer failure only: compare complete fitted/optimized curve checks; at first collision compare fixed position with parent heading and projected position with both headings; scale all initial knots by its native-required dynamic ratio plus1ppm numerical margin. No acceptance, objective, limit, map or published trajectory change.",
        "boundary": "Time-scaled variant is diagnostic only: geometry unchanged, PVA and fixed-.8s preview orientation change. Runtime control continuity and feasibility are not established; extra query overhead is not a performance control."}, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()

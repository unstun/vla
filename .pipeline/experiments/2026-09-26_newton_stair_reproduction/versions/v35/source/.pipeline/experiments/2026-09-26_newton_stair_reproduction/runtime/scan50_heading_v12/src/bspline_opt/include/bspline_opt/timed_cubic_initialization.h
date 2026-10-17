#pragma once
#include <bspline_opt/full_trajectory_collision.h>
#include <Eigen/QR>
#include <vector>

namespace reactive_stair {

inline bool validBoundaryDerivatives(const std::vector<Eigen::Vector3d>& derivatives) {
  if (derivatives.size() != 4) return false;
  for (const auto& p : derivatives) if (!p.allFinite()) return false;
  return true;
}

// Numerical agreement with the requested PVA, not a physical tracking tolerance.
inline bool matchesBoundaryPva(scan_planner::UniformBspline& curve,
    const Eigen::Vector3d& start, const Eigen::Vector3d& end,
    const std::vector<Eigen::Vector3d>& derivatives, double tolerance = 1e-6) {
  if (!start.allFinite() || !end.allFinite() || !validBoundaryDerivatives(derivatives) ||
      !std::isfinite(tolerance) || tolerance < 0.0) return false;
  const auto controls = curve.getControlPoint();
  if (controls.rows() != 3 || controls.cols() < 6 || curve.getDegree() != 3 ||
      !validSplineLayout(controls, curve.getKnot(), 3)) return false;
  auto velocity = curve.getDerivative();
  if (!validSplineLayout(velocity.getControlPoint(), velocity.getKnot(), 2)) return false;
  auto acceleration = velocity.getDerivative();
  if (!validSplineLayout(acceleration.getControlPoint(), acceleration.getKnot(), 1)) return false;
  const double duration = curve.getTimeSum();
  const auto close = [tolerance](const Eigen::VectorXd& actual, const Eigen::Vector3d& expected) {
    return actual.allFinite() && (actual - expected).norm() <= tolerance;
  };
  return close(curve.evaluateDeBoorT(0), start) && close(curve.evaluateDeBoorT(duration), end) &&
      close(velocity.evaluateDeBoorT(0), derivatives[0]) && close(velocity.evaluateDeBoorT(duration), derivatives[1]) &&
      close(acceleration.evaluateDeBoorT(0), derivatives[2]) && close(acceleration.evaluateDeBoorT(duration), derivatives[3]);
}

// Uniform cubic endpoint PVA fixes three controls per end. Fit position rows
// for the remaining controls only, keeping the original sample sequence.
inline bool fitCubicBoundaryPva(double interval,
    const std::vector<Eigen::Vector3d>& points,
    const std::vector<Eigen::Vector3d>& derivatives, Eigen::MatrixXd& controls) {
  controls.resize(0, 0);
  if (!std::isfinite(interval) || interval <= 0.0 || points.size() < 7 || points.size() > 512 ||
      !validBoundaryDerivatives(derivatives)) return false;
  for (const auto& p : points) if (!p.allFinite()) return false;
  const double h2 = interval * interval;
  if (!std::isfinite(h2) || !std::isfinite(interval * (points.size() - 1))) return false;
  const Eigen::Index count = static_cast<Eigen::Index>(points.size());
  Eigen::MatrixXd fitted = Eigen::MatrixXd::Zero(3, count + 2);
  for (int side = 0; side < 2; ++side) {
    const auto& p = side == 0 ? points.front() : points.back();
    const auto& v = derivatives[side];
    const auto& a = derivatives[side + 2];
    const Eigen::Index index = side == 0 ? 0 : count - 1;
    fitted.col(index) = p - interval * v + (h2 / 3.0) * a;
    fitted.col(index + 1) = p - (h2 / 6.0) * a;
    fitted.col(index + 2) = p + interval * v + (h2 / 3.0) * a;
  }
  if (!fitted.allFinite()) return false;
  Eigen::MatrixXd design = Eigen::MatrixXd::Zero(count, count + 2);
  Eigen::MatrixXd target(count, 3);
  for (Eigen::Index i = 0; i < count; ++i) {
    design(i, i) = 1.0 / 6.0;
    design(i, i + 1) = 4.0 / 6.0;
    design(i, i + 2) = 1.0 / 6.0;
    target.row(i) = points[i].transpose();
  }
  target -= design * fitted.transpose();
  const Eigen::MatrixXd free_design = design.middleCols(3, count - 4);
  const Eigen::ColPivHouseholderQR<Eigen::MatrixXd> solver(free_design);
  if (solver.rank() != count - 4) return false;
  const Eigen::MatrixXd free_points = solver.solve(target);
  if (!free_points.allFinite()) return false;
  fitted.middleCols(3, count - 4) = free_points.transpose();
  scan_planner::UniformBspline curve(fitted, 3, interval);
  if (!matchesBoundaryPva(curve, points.front(), points.back(), derivatives)) return false;
  controls = std::move(fitted);
  return true;
}

enum class TimedCubicStatus { Ready, InvalidInput, BoundaryLimitExceeded, FitFailed, InvalidScale, IterationLimit };
struct TimedCubicInitialization {
  TimedCubicStatus status = TimedCubicStatus::InvalidInput;
  Eigen::MatrixXd controls;
  double interval_s = 0.0;
  size_t iterations = 0;
  bool ready() const { return status == TimedCubicStatus::Ready; }
};

inline TimedCubicInitialization initializeTimedCubic(
    const std::vector<Eigen::Vector3d>& points, const std::vector<Eigen::Vector3d>& derivatives,
    double interval, double velocity_limit, double acceleration_limit, double feasibility_tolerance,
    size_t maximum_iterations = 8) {
  TimedCubicInitialization result;
  if (!std::isfinite(interval) || interval <= 0.0 || !validBoundaryDerivatives(derivatives) ||
      !std::isfinite(velocity_limit) || velocity_limit <= 0.0 ||
      !std::isfinite(acceleration_limit) || acceleration_limit <= 0.0 ||
      !std::isfinite(feasibility_tolerance) || feasibility_tolerance < 0.0 ||
      maximum_iterations == 0 || maximum_iterations > 8) return result;
  // Same limits as the existing native component-bound feasibility check.
  const double enlarged_velocity = velocity_limit * (1.0 + feasibility_tolerance) + 1e-4;
  const double enlarged_acceleration = acceleration_limit * (1.0 + feasibility_tolerance) + 1e-4;
  if (!std::isfinite(enlarged_velocity) || !std::isfinite(enlarged_acceleration)) return result;
  for (size_t i = 0; i < 4; ++i) {
    if (derivatives[i].cwiseAbs().maxCoeff() > (i < 2 ? enlarged_velocity : enlarged_acceleration)) {
      result.status = TimedCubicStatus::BoundaryLimitExceeded;
      return result;
    }
  }
  for (size_t iteration = 0; iteration < maximum_iterations; ++iteration) {
    ++result.iterations;
    Eigen::MatrixXd controls;
    if (!fitCubicBoundaryPva(interval, points, derivatives, controls)) {
      result.status = TimedCubicStatus::FitFailed;
      return result;
    }
    scan_planner::UniformBspline curve(controls, 3, interval);
    curve.setPhysicalLimits(velocity_limit, acceleration_limit, feasibility_tolerance);
    double ratio = 0.0;
    if (curve.checkFeasibility(ratio, false)) {
      result.controls = std::move(controls);
      result.interval_s = interval;
      result.status = TimedCubicStatus::Ready;
      return result;
    }
    // Refit with original boundary derivatives; do not scale measured/target PVA.
    if (!std::isfinite(ratio) || ratio <= 1.0 || !std::isfinite(interval * ratio * (1.0 + 1e-6))) {
      result.status = TimedCubicStatus::InvalidScale;
      return result;
    }
    interval *= ratio * (1.0 + 1e-6);
  }
  result.status = TimedCubicStatus::IterationLimit;
  return result;
}
}  // namespace reactive_stair

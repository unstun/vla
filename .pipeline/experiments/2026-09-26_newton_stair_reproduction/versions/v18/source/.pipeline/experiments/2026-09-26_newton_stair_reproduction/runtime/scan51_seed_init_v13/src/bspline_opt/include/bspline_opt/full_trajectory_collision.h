#ifndef VLA_FULL_TRAJECTORY_COLLISION_H
#define VLA_FULL_TRAJECTORY_COLLISION_H

#include <bspline_opt/uniform_bspline.h>
#include <cmath>
#include <cstddef>
#include <limits>

namespace reactive_stair {

enum class TrajectoryCheckStatus { Clear, Collision, InvalidCurve, InvalidTime,
                                   InvalidResolution, SampleBudgetExceeded };
struct TrajectoryCheck {
  TrajectoryCheckStatus status = TrajectoryCheckStatus::InvalidCurve;
  double first_time_s = 0.0;  // Always finite, including failure before sampling.
  double duration_s = 0.0;
  size_t samples = 0;
  bool clear() const { return status == TrajectoryCheckStatus::Clear; }
};

inline bool validSplineLayout(const Eigen::MatrixXd &points, const Eigen::VectorXd &knots,
                              int degree) {
  const auto count = points.cols();
  if (points.rows() != 3 || degree < 1 || degree > 3 || count < degree + 1 ||
      knots.size() != count + degree + 1 || !points.allFinite() || !knots.allFinite()) return false;
  for (Eigen::Index i = 1; i < knots.size(); ++i)
    if (knots[i] < knots[i - 1]) return false;
  if (!(knots[count] > knots[degree])) return false;
  // Validate every denominator reachable by this implementation's de Boor
  // evaluator, including its left-span choice at repeated knots/endpoints.
  for (Eigen::Index k = degree; k < count; ++k)
    for (int r = 1; r <= degree; ++r)
      for (int i = degree; i >= r; --i)
        if (!(knots[i + 1 + k - r] > knots[i + k - degree])) return false;
  return true;
}

// Full relative-time interval with both endpoints. This is a sampled collision
// contract, not a proof of continuous translation or rotating-footprint sweep.
template <typename Heading, typename Occupied>
TrajectoryCheck checkFullCubicTrajectory(scan_planner::UniformBspline &trajectory,
    double begin_s, double resolution_m, double lookahead_s,
    Heading heading, Occupied occupied, size_t maximum_samples = 10000) {
  TrajectoryCheck result;
  result.first_time_s = std::isfinite(begin_s) && begin_s > 0.0 ? begin_s : 0.0;
  const auto points = trajectory.getControlPoint();
  const auto knots = trajectory.getKnot();
  // Check dimensions before reading a default-constructed object's degree.
  if (points.rows() != 3 || points.cols() < 4 || trajectory.getDegree() != 3 ||
      !validSplineLayout(points, knots, 3)) return result;
  const double duration = knots[points.cols()] - knots[3];
  result.duration_s = duration;
  if (!std::isfinite(duration) || duration <= 0.0 || !std::isfinite(lookahead_s) || lookahead_s < 0.0)
    return result;
  if (!std::isfinite(begin_s) || begin_s < -1e-3) {
    result.status = TrajectoryCheckStatus::InvalidTime;
    return result;
  }
  const double begin = std::min(duration, std::max(0.0, begin_s));
  result.first_time_s = begin;
  if (!std::isfinite(resolution_m) || resolution_m <= 0.0) {
    result.status = TrajectoryCheckStatus::InvalidResolution;
    return result;
  }
  for (Eigen::Index i = 0; i < points.cols() - 1; ++i)
    if (!(knots[i + 4] > knots[i + 1])) return result;
  auto velocity = trajectory.getDerivative();
  const auto velocity_points = velocity.getControlPoint();
  if (!validSplineLayout(velocity_points, velocity.getKnot(), 2)) return result;
  double speed_bound = 0.0;
  for (Eigen::Index i = 0; i < velocity_points.cols(); ++i)
    speed_bound = std::max(speed_bound, velocity_points.col(i).norm());
  if (!std::isfinite(speed_bound)) return result;
  const double step = speed_bound > 0.0 ? std::min(0.01, 0.5 * resolution_m / speed_bound) : 0.01;
  const double divisions = begin == duration ? 0.0 : std::ceil((duration - begin) / step);
  if (!std::isfinite(divisions) || divisions < 0.0 || maximum_samples == 0 ||
      divisions >= static_cast<double>(maximum_samples)) {
    result.status = TrajectoryCheckStatus::SampleBudgetExceeded;
    return result;
  }
  const size_t count = static_cast<size_t>(divisions);
  for (size_t i = 0; i <= count; ++i) {
    // Set the final endpoint explicitly, avoiding cumulative floating drift.
    const double t = i == count ? duration : begin + (duration - begin) * (static_cast<double>(i) / count);
    const Eigen::Vector3d pos = trajectory.evaluateDeBoorT(t);
    const Eigen::Vector3d ahead = trajectory.evaluateDeBoorT(std::min(t + lookahead_s, duration));
    const Eigen::Vector3d vel = velocity.evaluateDeBoorT(t);
    result.first_time_s = t;
    if (!pos.allFinite() || !ahead.allFinite() || !vel.allFinite()) return result;
    const double yaw = heading(pos, ahead, vel);
    if (!std::isfinite(yaw)) return result;
    ++result.samples;
    if (occupied(pos, yaw)) {
      result.status = TrajectoryCheckStatus::Collision;
      return result;
    }
  }
  result.status = TrajectoryCheckStatus::Clear;
  return result;
}
}  // namespace reactive_stair
#endif

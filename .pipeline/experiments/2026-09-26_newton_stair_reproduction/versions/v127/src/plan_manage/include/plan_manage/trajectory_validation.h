#ifndef SCAN_NATIVE_TRAJECTORY_VALIDATION_H
#define SCAN_NATIVE_TRAJECTORY_VALIDATION_H

#include <bspline_opt/full_trajectory_collision.h>
#include <bspline_opt/timed_cubic_initialization.h>
#include <plan_env/grid_map.h>
#include <algorithm>
#include <vector>

namespace scan_planner {

enum class ValidationFailure { None, BoundaryPva, VelocityLimit, AccelerationLimit, PublicationEpoch };
struct ValidationResult {
  ValidationFailure failure{ValidationFailure::None};
  double time_s{0.0};
  double measured{0.0};
  double limit{0.0};
  bool valid() const { return failure == ValidationFailure::None; }
};

// Stateless native checks. Callers retain source clocks, refresh ordering,
// publication/query leases and command ownership. A verdict is not a lease.
// Candidate boundary/dynamics and executing-remainder collision have distinct
// entry points: validating a remainder must not rebase its PVA or start epoch.
class NativeTrajectoryValidator {
public:
  static ValidationResult boundary(UniformBspline &curve,
      const Eigen::Vector3d &start, const Eigen::Vector3d &end,
      const std::vector<Eigen::Vector3d> &derivatives) {
    return reactive_stair::matchesBoundaryPva(curve, start, end, derivatives)
        ? ValidationResult{} : ValidationResult{ValidationFailure::BoundaryPva};
  }

  // Preconditions and arithmetic are the original manager contract. Layout and
  // finite boundary checks remain at their original earlier admission sites.
  static ValidationResult dynamics(UniformBspline &curve,
      double velocity_limit, double acceleration_limit) {
    UniformBspline velocity = curve.getDerivative();
    UniformBspline acceleration = velocity.getDerivative();
    const double duration = curve.getTimeSum();
    const double sample_dt = std::max(0.01, std::min(0.05, duration / 50.0));
    for (double t = 0.0; t < duration + 1e-6; t += sample_dt) {
      const double tc = std::min(t, duration);
      const Eigen::Vector3d vel = velocity.evaluateDeBoorT(tc);
      if (vel.norm() > velocity_limit)
        return {ValidationFailure::VelocityLimit, tc, vel.norm(), velocity_limit};
      const Eigen::Vector3d acc = acceleration.evaluateDeBoorT(tc);
      if (acc.norm() > acceleration_limit)
        return {ValidationFailure::AccelerationLimit, tc, acc.norm(), acceleration_limit};
    }
    return {};
  }

  // The map must be the caller's existing pinned native map/query view. Keep
  // original full 3D footprint, heading, terrain-support and freshness checks.
  static reactive_stair::TrajectoryCheck collision(
      UniformBspline &curve, GridMap &map, double begin_s) {
    return reactive_stair::checkFullCubicTrajectory(
        curve, begin_s, map.getResolution(), GridMap::collision_heading_lookahead_s,
        [&map](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
          return map.collisionTrajectoryYaw(p, ahead, v);
        },
        [&map](const Eigen::Vector3d &p, double yaw) { return map.getInflateOccupancy(p, yaw) != 0; });
  }

  // Compute elapsed with the caller's original source epoch after collision
  // work. No receipt-time substitution or new timeout is introduced here.
  static ValidationResult publicationEpoch(double elapsed, double duration) {
    return elapsed < 0.0 || elapsed >= duration
        ? ValidationResult{ValidationFailure::PublicationEpoch, elapsed, elapsed, duration}
        : ValidationResult{};
  }
};
}  // namespace scan_planner
#endif

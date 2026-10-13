#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>
#include <bspline_opt/uniform_bspline.h>

namespace scan_planner
{
struct CruiseSpeedReport
{
  bool valid{false};
  bool passed{false};
  int cruise_samples{0};
  double path_length{0.0};
  double entry_distance{0.0};
  double exit_distance{0.0};
  double minimum_speed{0.0};
  double sample_dt{0.0};
};

// Boundary envelope for a symmetric acceleration transition. This uses the
// configured jerk to reserve ramp distance; it does not certify actual jerk.
inline double cruiseBoundaryDistance(double boundary_speed, double cruise_speed,
                                     double acceleration, double jerk)
{
  const double delta = std::max(0.0, cruise_speed - boundary_speed);
  if (delta == 0.0) return 0.0;
  const double ramp_time = delta >= acceleration * acceleration / jerk
      ? delta / acceleration + acceleration / jerk
      : 2.0 * std::sqrt(delta / jerk);
  return 0.5 * (boundary_speed + cruise_speed) * ramp_time;
}

// Nav2 RPP separates its minimum travel speed from approach slowing; MPPI
// scores speeds below its travel deadband. Here the same distinction is made
// on SCAN's timed curve, before the existing final PVA/dynamic/collision gates.
inline CruiseSpeedReport measureMinimumCruise(UniformBspline curve,
                                              double minimum_speed,
                                              double acceleration, double jerk)
{
  CruiseSpeedReport result;
  if (!std::isfinite(minimum_speed) || minimum_speed < 0.0) return result;
  if (minimum_speed == 0.0) {
    result.valid = result.passed = true;
    return result;
  }
  if (!std::isfinite(acceleration) || acceleration <= 0.0 ||
      !std::isfinite(jerk) || jerk <= 0.0) return result;
  const auto controls = curve.getControlPoint();
  const auto knots = curve.getKnot();
  const double duration = curve.getTimeSum();
  if (controls.rows() != 3 || controls.cols() < 6 || !controls.allFinite() ||
      !knots.allFinite() || !std::isfinite(duration) || duration <= 0.0 ||
      duration > 1000.0) return result;
  for (int i = 1; i < knots.size(); ++i)
    if (knots[i] <= knots[i - 1]) return result;

  auto velocity = curve.getDerivative();
  const double start_speed = velocity.evaluateDeBoorT(0.0).head<2>().norm();
  const double end_speed = velocity.evaluateDeBoorT(duration).head<2>().norm();
  if (!std::isfinite(start_speed) || !std::isfinite(end_speed)) return result;
  result.entry_distance = cruiseBoundaryDistance(start_speed, minimum_speed, acceleration, jerk);
  result.exit_distance = cruiseBoundaryDistance(end_speed, minimum_speed, acceleration, jerk);
  const int intervals = std::max(1, static_cast<int>(std::ceil(duration / 0.01)));
  result.sample_dt = duration / intervals;
  std::vector<double> distance(intervals + 1, 0.0), speed(intervals + 1, 0.0);
  Eigen::Vector2d previous = curve.evaluateDeBoorT(0.0).head<2>();
  for (int i = 0; i <= intervals; ++i) {
    const double t = i * result.sample_dt;
    const Eigen::Vector2d point = curve.evaluateDeBoorT(t).head<2>();
    speed[i] = velocity.evaluateDeBoorT(t).head<2>().norm();
    if (!point.allFinite() || !std::isfinite(speed[i])) return result;
    if (i) distance[i] = distance[i - 1] + (point - previous).norm();
    previous = point;
  }
  result.path_length = distance.back();
  double observed_minimum = std::numeric_limits<double>::infinity();
  for (int i = 0; i <= intervals; ++i) {
    if (distance[i] < result.entry_distance ||
        result.path_length - distance[i] < result.exit_distance) continue;
    ++result.cruise_samples;
    observed_minimum = std::min(observed_minimum, speed[i]);
  }
  result.minimum_speed = result.cruise_samples ? observed_minimum : 0.0;
  result.valid = true;
  result.passed = result.cruise_samples == 0 || observed_minimum + 1e-9 >= minimum_speed;
  return result;
}
}  // namespace scan_planner

#include <bspline_opt/uniform_bspline.h>
#define reactive_stair legacy_reactive_stair
#include V147_CHECK_HEADER
#undef reactive_stair
#undef VLA_FULL_TRAJECTORY_COLLISION_H
#include <bspline_opt/full_trajectory_collision.h>
#include <iostream>
#include <stdexcept>
#include <vector>

int main() {
  Eigen::MatrixXd points(3, 9);
  for (int i = 0; i < points.cols(); ++i)
    points.col(i) = Eigen::Vector3d(0.12 * i, 0.02 * std::sin(i), 0.35 + 0.03 * i);
  scan_planner::UniformBspline curve(points, 3, 0.15);
  auto heading = [](const Eigen::Vector3d &, const Eigen::Vector3d &, const Eigen::Vector3d &) { return 0.0; };
  size_t cases = 0;
  for (double begin : {0.0, 0.0023, 0.027, 0.08, curve.getTimeSum(), curve.getTimeSum() + 1.0, -0.0001}) {
    std::vector<Eigen::Vector3d> old_samples, new_samples;
    auto old_result = legacy_reactive_stair::checkFullCubicTrajectory(curve, begin, 0.1, 0.8,
      heading, [&](const Eigen::Vector3d &p, double) { old_samples.push_back(p); return false; });
    auto new_result = reactive_stair::checkFullCubicTrajectory(curve, begin, 0.1, 0.8,
      heading, [&](const Eigen::Vector3d &p, double) { new_samples.push_back(p); return false; });
    if (!old_result.clear() || !new_result.clear()) throw std::runtime_error("Valid free curve rejected");
    for (const auto &p : old_samples) {
      bool exact = false;
      for (const auto &q : new_samples) if ((p.array() == q.array()).all()) exact = true;
      if (!exact) throw std::runtime_error("A legacy sample was removed or moved");
    }
    if (begin >= curve.getTimeSum() && new_samples.size() != 1)
      throw std::runtime_error("Clamped endpoint handling changed");
    ++cases;
  }
  std::vector<Eigen::Vector3d> refined;
  reactive_stair::checkFullCubicTrajectory(curve, 0.0, 0.1, 0.8, heading,
    [&](const Eigen::Vector3d &p, double) { refined.push_back(p); return false; });
  const Eigen::Vector3d narrow_center = refined.at(1);
  auto narrow = [&](const Eigen::Vector3d &p, double) { return (p - narrow_center).norm() < 1e-5; };
  const auto missed = legacy_reactive_stair::checkFullCubicTrajectory(curve, 0.0, 0.1, 0.8, heading, narrow);
  const auto found = reactive_stair::checkFullCubicTrajectory(curve, 0.0, 0.1, 0.8, heading, narrow);
  if (!missed.clear() || found.status != reactive_stair::TrajectoryCheckStatus::Collision)
    throw std::runtime_error("Narrow missed-region regression failed");
  const auto exhausted = reactive_stair::checkFullCubicTrajectory(curve, 0.0, 0.1, 0.8,
    heading, [](const Eigen::Vector3d &, double) { return false; }, 100);
  if (exhausted.status != reactive_stair::TrajectoryCheckStatus::SampleBudgetExceeded)
    throw std::runtime_error("Sample budget did not reject");
  const auto invalid = reactive_stair::checkFullCubicTrajectory(curve,
    std::numeric_limits<double>::quiet_NaN(), 0.1, 0.8, heading, narrow);
  if (invalid.clear()) throw std::runtime_error("Invalid time accepted");
  std::cout << "V151_REGRESSION_PASS legacy_sample_superset_cases=" << cases
            << " narrow_region_detected=1 budget_fail_closed=1 invalid_time_rejected=1" << std::endl;
}

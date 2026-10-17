#include <bspline_opt/full_trajectory_collision.h>
#include <plan_env/motion_heading.h>
#include <cassert>
#include <iostream>
#include <vector>

using scan_planner::UniformBspline;
using namespace reactive_stair;

UniformBspline straight(double speed = 1., double interval = 1.) {
  Eigen::MatrixXd points(3, 6);
  for (int i = 0; i < 6; ++i) points.col(i) = Eigen::Vector3d((i - 1) * interval * speed, 0, 0);
  return UniformBspline(points, 3, interval);
}

auto heading = [](const Eigen::Vector3d &, const Eigen::Vector3d &, const Eigen::Vector3d &) { return 0.; };
auto free_space = [](const Eigen::Vector3d &, double) { return false; };

int main() {
  auto curve = straight();
  const auto clear = checkFullCubicTrajectory(curve, 0., .05, .8, heading, free_space);
  assert(clear.clear() && clear.samples == 301 && clear.duration_s == 3. && clear.first_time_s == 3.);
  // The old 2/3 loop never visited x>2.1, nor the exact endpoint.
  for (bool endpoint_only : {false, true}) {
    const auto blocked = checkFullCubicTrajectory(curve, 0., .05, .8, heading,
        [endpoint_only](const Eigen::Vector3d &p, double) { return endpoint_only ? p.x() >= 3. : p.x() > 2.1; });
    assert(blocked.status == TrajectoryCheckStatus::Collision);
    assert(blocked.first_time_s >= 2.1 && (!endpoint_only || blocked.first_time_s == 3.));
  }
  // Absolute knots may be shifted/nonuniform; evaluateDeBoorT remains relative.
  auto shifted = straight();
  auto knots = shifted.getKnot();
  for (int i = 0; i < knots.size(); ++i) knots[i] = 7. + i + .03 * i * i;
  shifted.setKnot(knots);
  std::vector<Eigen::Vector3d> sampled;
  const auto nonuniform = checkFullCubicTrajectory(shifted, 0., .05, .8, heading,
      [&sampled](const Eigen::Vector3d &p, double) { sampled.push_back(p); return false; });
  assert(nonuniform.clear());
  assert((sampled.front() - shifted.evaluateDeBoorT(0.)).norm() < 1e-12);
  assert((sampled.back() - shifted.evaluateDeBoorT(nonuniform.duration_s)).norm() < 1e-12);

  auto fast = straight(20.);
  sampled.clear();
  const auto dense = checkFullCubicTrajectory(fast, 0., .05, .8, heading,
      [&sampled](const Eigen::Vector3d &p, double) { sampled.push_back(p); return false; });
  assert(dense.clear() && dense.samples > 301);
  for (size_t i = 1; i < sampled.size(); ++i) assert((sampled[i] - sampled[i-1]).norm() <= .025 + 1e-9);
  assert(checkFullCubicTrajectory(fast, 0., .05, .8, heading, free_space, 10).status == TrajectoryCheckStatus::SampleBudgetExceeded);

  for (double t : {3., 4.}) {
    const auto end = checkFullCubicTrajectory(curve, t, .05, .8, heading, free_space);
    assert(end.clear() && end.samples == 1 && end.first_time_s == 3.);
    const auto end_blocked = checkFullCubicTrajectory(curve, t, .05, .8, heading,
        [](const Eigen::Vector3d &p, double) { return p.x() >= 3.; });
    assert(end_blocked.status == TrajectoryCheckStatus::Collision);
  }
  for (double t : {-1., std::numeric_limits<double>::quiet_NaN()}) {
    const auto invalid = checkFullCubicTrajectory(curve, t, .05, .8, heading, free_space);
    assert(invalid.status == TrajectoryCheckStatus::InvalidTime && std::isfinite(invalid.first_time_s));
  }
  assert(checkFullCubicTrajectory(curve, -.000001, .05, .8, heading, free_space).clear());
  assert(checkFullCubicTrajectory(curve, 0., 0., .8, heading, free_space).status == TrajectoryCheckStatus::InvalidResolution);

  auto still = straight(0.);
  auto observed_yaw = [](const Eigen::Vector3d &, const Eigen::Vector3d &, const Eigen::Vector3d &) {
    return motionHeading(0., 0., 1.2, 1., .99);
  };
  auto stale_yaw = [](const Eigen::Vector3d &, const Eigen::Vector3d &, const Eigen::Vector3d &) {
    return motionHeading(0., 0., 1.2, 1., .5);
  };
  assert(checkFullCubicTrajectory(still, 0., .05, .8, observed_yaw, free_space).clear());
  assert(!checkFullCubicTrajectory(still, 0., .05, .8, stale_yaw, free_space).clear());

  for (int kind = 0; kind < 7; ++kind) {
    auto invalid = straight();
    auto bad = invalid.getKnot();
    if (kind == 0) bad[4] = NAN;
    if (kind == 1) bad[4] = bad[3] - 1.;
    if (kind == 2) bad.setZero();
    if (kind == 3) bad.conservativeResize(3);
    if (kind < 4) invalid.setKnot(bad);
    if (kind == 4) {
      auto points = invalid.getControlPoint(); points(0, 2) = NAN;
      invalid.setUniformBspline(points, 3, 1.);
    }
    if (kind == 5) invalid.setUniformBspline(Eigen::MatrixXd::Zero(2, 6), 3, 1.);
    if (kind == 6) invalid.setUniformBspline(Eigen::MatrixXd::Zero(3, 3), 3, 1.);
    const auto result = checkFullCubicTrajectory(invalid, 0., .05, .8, heading, free_space);
    assert(result.status == TrajectoryCheckStatus::InvalidCurve && std::isfinite(result.first_time_s));
  }
  std::cout << "full interval, tail, endpoint, relative time, adaptive sampling, clock, heading and malformed curve tests PASS\n";
}

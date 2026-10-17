// Sample the existing native complete-curve checker for map-query diagnosis.
#include <bspline_opt/full_trajectory_collision.h>
#include <plan_env/motion_heading.h>
#include <fstream>
#include <iomanip>
#include <iostream>

int main(int argc, char **argv) {
  if (argc != 3) return 2;
  std::ifstream input(argv[1]);
  int count, degree, knot_count;
  input >> count >> degree >> knot_count;
  Eigen::MatrixXd controls(3, count);
  Eigen::VectorXd knots(knot_count);
  for (int i=0; i<count; ++i) input >> controls(0,i) >> controls(1,i) >> controls(2,i);
  for (int i=0; i<knot_count; ++i) input >> knots[i];
  if (!input || degree != 3) return 3;
  scan_planner::UniformBspline curve(controls, degree, knots[4]-knots[3]);
  curve.setKnot(knots);
  std::ofstream output(argv[2]);
  output << std::setprecision(17);
  size_t sample = 0;
  const auto result = reactive_stair::checkFullCubicTrajectory(curve, 0., .05, .8,
    [](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
      const Eigen::Vector3d direction = (ahead-p).head<2>().squaredNorm() < 1e-4 ? v : ahead-p;
      return reactive_stair::motionHeading(direction.x(), direction.y(), 0., 3.01, 3.);
    }, [&](const Eigen::Vector3d &point, double yaw) {
      output << point.x() << " " << point.y() << " " << point.z() << " " << yaw << " raw_" << sample << "\n";
      // Scoring-only sensitivity controls; these never enter navigation.
      output << point.x() << " " << point.y() << " 0.3 " << yaw << " exact_z_" << sample << "\n";
      output << point.x() << " " << point.y() << " " << point.z() << " 0 body_yaw_" << sample << "\n";
      ++sample;
      return false;
    });
  if (!result.clear()) return 4;
  std::cout << "{\"samples\":" << sample << ",\"duration\":" << std::setprecision(17)
            << result.duration_s << ",\"claim\":\"Native sampler only; query occupancy separately\"}\n";
}

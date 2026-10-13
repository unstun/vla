// Inspect recorded curves using the unchanged native UniformBspline class.
#include <bspline_opt/uniform_bspline.h>
#include <fstream>
#include <iomanip>
#include <stdexcept>

int main(int argc, char** argv) {
  if (argc != 3) throw std::runtime_error("input file and time scale required");
  std::ifstream input(argv[1]);
  int count, degree, knot_count;
  input >> count >> degree >> knot_count;
  Eigen::MatrixXd points(3, count);
  for (int i = 0; i < count; ++i) input >> points(0,i) >> points(1,i) >> points(2,i);
  Eigen::VectorXd knots(knot_count);
  const double scale = std::stod(argv[2]);
  for (int i = 0; i < knot_count; ++i) { input >> knots(i); knots(i) *= scale; }
  if (!input.good() || degree != 3 || count < 6 || scale <= 0) throw std::runtime_error("invalid curve");
  const double interval = knots(degree+1)-knots(degree);
  scan_planner::UniformBspline curve(points, degree, interval);
  curve.setKnot(knots);
  curve.setPhysicalLimits(.75, .5, .5);
  double ratio;
  const bool feasible = curve.checkFeasibility(ratio, false);
  auto velocity = curve.getDerivative();
  auto acceleration = velocity.getDerivative();
  const auto vc = velocity.getControlPoint();
  const auto ac = acceleration.getControlPoint();
  Eigen::Index vr, vi, ar, ai;
  const double vmax = vc.cwiseAbs().maxCoeff(&vr,&vi);
  const double amax = ac.cwiseAbs().maxCoeff(&ar,&ai);
  const double peak_time = double(ai) * interval;
  const auto peak_position = curve.evaluateDeBoorT(peak_time);
  std::cout << std::setprecision(17) << "{\"duration\":" << curve.getTimeSum()
    << ",\"interval\":" << interval << ",\"feasible\":" << (feasible ? "true" : "false")
    << ",\"native_required_ratio\":" << ratio << ",\"maximum_velocity_component\":" << vmax
    << ",\"maximum_acceleration_component\":" << amax << ",\"velocity_axis\":" << vr
    << ",\"velocity_index\":" << vi << ",\"acceleration_axis\":" << ar
    << ",\"acceleration_index\":" << ai << ",\"peak_acceleration_time\":" << peak_time
    << ",\"peak_acceleration_position\":[" << peak_position(0) << "," << peak_position(1) << "," << peak_position(2)
    << "],\"velocity_controls\":[";
  for (int i=0;i<vc.cols();++i) {
    if(i) std::cout << ",";
    std::cout << "[" << vc(0,i) << "," << vc(1,i) << "," << vc(2,i) << "]";
  }
  std::cout << "],\"acceleration_controls\":[";
  for (int i=0;i<ac.cols();++i) {
    if(i) std::cout << ",";
    std::cout << "[" << ac(0,i) << "," << ac(1,i) << "," << ac(2,i) << "]";
  }
  std::cout << "]}\n";
}

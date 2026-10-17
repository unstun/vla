#include <vector>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>
#include <plan_manage/minimum_cruise.h>

using scan_planner::UniformBspline;
using scan_planner::measureMinimumCruise;

void require(bool condition, const char *name)
{
  if (!condition) throw std::runtime_error(name);
  std::cout << "PASS " << name << "\n";
}

UniformBspline line(double speed)
{
  Eigen::MatrixXd controls = Eigen::MatrixXd::Zero(3, 13);
  for (int i = 0; i < controls.cols(); ++i) controls(0, i) = (i - 1) * speed;
  return UniformBspline(controls, 3, 1.0);
}

int main(int argc, char **argv)
{
  require(argc == 2, "recorded fixture path required");
  auto slow = line(0.2);
  auto report = measureMinimumCruise(slow, 0.6, 0.5, 4.0);
  require(report.valid && !report.passed && report.cruise_samples > 0,
          "slow long travel rejected");
  require(std::abs(report.minimum_speed - 0.2) < 1e-12, "actual native derivative measured");
  auto normal = line(0.65);
  report = measureMinimumCruise(normal, 0.6, 0.5, 4.0);
  require(report.passed && report.cruise_samples > 0, "ordinary cruise accepted");
  require(report.sample_dt <= 0.01, "bounded sampling interval");
  auto stopped = line(0.0);
  report = measureMinimumCruise(stopped, 0.6, 0.5, 4.0);
  require(report.passed && report.cruise_samples == 0, "stop remains zero and is not cruise");
  const auto before_controls = slow.getControlPoint();
  const auto before_knots = slow.getKnot();
  report = measureMinimumCruise(slow, 0.0, 0.5, 4.0);
  require(report.passed && report.cruise_samples == 0 &&
          (before_controls - slow.getControlPoint()).norm() == 0.0 &&
          (before_knots - slow.getKnot()).norm() == 0.0, "disabled mode leaves curve identical");
  require(!measureMinimumCruise(slow, -0.6, 0.5, 4.0).valid, "negative minimum rejected");
  require(!measureMinimumCruise(slow, std::numeric_limits<double>::quiet_NaN(), 0.5, 4.0).valid,
          "nonfinite minimum rejected");
  require(!measureMinimumCruise(slow, 0.6, 0.0, 4.0).valid, "invalid acceleration rejected");
  require(!measureMinimumCruise(slow, 0.6, 0.5, 0.0).valid, "invalid jerk envelope rejected");
  auto bad_controls = slow.getControlPoint();
  bad_controls(0, 5) = std::numeric_limits<double>::quiet_NaN();
  require(!measureMinimumCruise(UniformBspline(bad_controls, 3, 1.0), 0.6, 0.5, 4.0).valid,
          "nonfinite native curve rejected");
  auto too_fast = line(2.0);
  too_fast.setPhysicalLimits(1.0, 0.5, 0.5);
  double ratio = 0.0;
  require(measureMinimumCruise(too_fast, 0.6, 0.5, 4.0).passed &&
          !too_fast.checkFeasibility(ratio, false), "minimum cannot replace maximum feasibility");

  std::ifstream fixtures(argv[1]);
  require(bool(fixtures), "recorded native curves loaded");
  std::string name;
  int count = 0, building_short = 0, long_cruise = 0;
  while (fixtures >> name) {
    int columns, knot_count;
    fixtures >> columns >> knot_count;
    Eigen::MatrixXd controls(3, columns);
    Eigen::VectorXd knots(knot_count);
    for (int i = 0; i < columns; ++i)
      for (int axis = 0; axis < 3; ++axis) fixtures >> controls(axis, i);
    for (int i = 0; i < knot_count; ++i) fixtures >> knots[i];
    require(bool(fixtures), "complete recorded curve");
    UniformBspline curve(controls, 3, 0.1);
    curve.setKnot(knots);
    report = measureMinimumCruise(curve, 0.6, 0.5, 4.0);
    require(report.valid, "recorded curve is finite");
    if (name.find("building") != std::string::npos) {
      require(report.passed && report.cruise_samples == 0, "recorded short move explicitly exempt");
      ++building_short;
    } else {
      require(report.cruise_samples > 0, "recorded long move has a cruise interval");
      ++long_cruise;
    }
    std::cout << std::setprecision(17) << "RECORDED {\"name\":\"" << name
              << "\",\"passed\":" << report.passed << ",\"samples\":" << report.cruise_samples
              << ",\"minimum_speed\":" << report.minimum_speed
              << ",\"length\":" << report.path_length << "}\n";
    ++count;
  }
  require(count == 15 && building_short == 3 && long_cruise == 12, "all original moving curves covered");
  std::cout << "ALL_TESTS_PASSED\n";
}

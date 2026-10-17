// The two native optimizer methods and ControlPoints are included verbatim.
// Solver and constraint generation are doubles; actual native curve math and
// terminal check control flow run against an explicit collision oracle.
#include <bspline_opt/full_trajectory_collision.h>
#include <bspline_opt/rebound_constraint_utils.h>
#include <rclcpp/rclcpp.hpp>
#include <chrono>
#include <cstring>
#include <fstream>
#include <functional>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
using scan_planner::UniformBspline;
using Eigen::Vector3d;

namespace lbfgs {
enum { LBFGS_CONVERGENCE, LBFGSERR_MAXIMUMITERATION, LBFGS_ALREADY_MINIMIZED,
       LBFGS_STOP, LBFGSERR_CANCELED };
struct lbfgs_parameter_t { int mem_size, max_iterations; double g_epsilon; };
void lbfgs_load_default_parameters(lbfgs_parameter_t*) {}
template<class... Args>
int lbfgs_optimize(int, double*, double* cost, Args...) { *cost = 0; return LBFGS_CONVERGENCE; }
const char* lbfgs_strerror(int) { return "fixture solver"; }
}

struct GridMap {
  static constexpr double collision_heading_lookahead_s = .8;
  function<int(const Vector3d&, double)> query = [](const Vector3d&, double) { return 0; };
  double getResolution() const { return .05; }
  int getInflateOccupancy(const Vector3d& p, double yaw) { return query(p, yaw); }
  double collisionTrajectoryYaw(const Vector3d& p, const Vector3d& ahead, const Vector3d& v) {
    const Vector3d d = (ahead - p).head<2>().squaredNorm() < 1e-4 ? v : Vector3d(ahead - p);
    return d.head<2>().norm() >= .01 ? atan2(d.y(), d.x()) : 0.;
  }
  void logInitialSplineCollision(const Vector3d&, double) {}
};
#include "native_control_points.inc"
class BsplineOptimizer {
 public:
  ControlPoints cps_;
  shared_ptr<GridMap> grid_map_ = make_shared<GridMap>();
  vector<Vector3d> ref_pts_;
  int order_ = 3, variable_num_ = 0, iter_num_ = 0, init_calls = 0;
  double bspline_interval_ = 1., lambda2_ = 1., new_lambda2_ = 1., lambda4_ = 1., min_cost_ = 0.;
  enum { DONT_STOP, STOP_FOR_REBOUND, STOP_FOR_ERROR } force_stop_type_ = DONT_STOP;
  static void costFunctionRebound() {}
  static void costFunctionRefine() {}
  static void earlyExit() {}
  vector<vector<Vector3d>> initControlPoints(Eigen::MatrixXd&, bool) { ++init_calls; return {}; }
  bool rebound_optimize();
  bool refine_optimize();
};
#include "native_optimizer_methods.inc"

void require(bool ok, const char* message) { if (!ok) throw runtime_error(message); }
void prepare(BsplineOptimizer& o, const string& name, const char* recorded) {
  o.cps_.resize(8);
  for (int i = 0; i < 8; ++i) o.cps_.points.col(i) = Vector3d(i - 1, 0, 0);
  if (name == "tail") o.grid_map_->query = [](const Vector3d& p, double) { return p.x() > 4.5; };
  else if (name == "endpoint") o.grid_map_->query = [](const Vector3d& p, double) { return p.x() >= 5. - 1e-12; };
  else if (name == "thin_prefix") o.grid_map_->query = [](const Vector3d& p, double) { return p.x() > 2.021 && p.x() < 2.039 ? -1 : 0; };
  else if (name == "zero_chord") {
    const double x[] = {-1, 0, 1, 1, 1, 1, 0, -1};
    for (int i = 0; i < 8; ++i) o.cps_.points(0, i) = x[i];
    o.grid_map_->query = [](const Vector3d& p, double) { return p.x() > .4; };
  } else if (name == "budget") o.bspline_interval_ = 30.;
  else if (name == "recorded_window") {
    ifstream input(recorded);
    int count = 0;
    input >> count >> o.bspline_interval_;
    require(count == 428, "recorded control count mismatch");
    o.cps_.resize(count);
    for (int i = 0; i < count; ++i)
      for (int j = 0; j < 3; ++j) input >> o.cps_.points(j, i);
    require(bool(input), "recorded geometry read failed");
    const Vector3d hit(-5.364135930287, 3.640156996473, .661003192915);
    o.grid_map_->query = [hit](const Vector3d& p, double yaw) {
      return (p - hit).norm() < .0001 && abs(yaw + .749505002125) < .005 ? -1 : 0;
    };
  } else require(name == "clear", "unknown fixture");
}

int main(int argc, char** argv) {
  try {
    require(argc == 3, "case and recorded curve required");
    const string name(argv[1]);
    bool verdicts_match = true;
    for (bool refine : {false, true}) {
      BsplineOptimizer o; prepare(o, name, argv[2]);
      const bool accepted = refine ? o.refine_optimize() : o.rebound_optimize();
      cout << (refine ? "refine" : "rebound") << " accepted=" << accepted << '\n';
      verdicts_match = verdicts_match && (accepted == (name == "clear"));
      require(o.init_calls <= 3, "collision retry exceeded original bound");
      if (name == "budget") require(o.init_calls == 0, "invalid/budget failure entered collision repair");
      require(o.lambda4_ == 1., "refine failed to restore original weight");
    }
    require(verdicts_match, "native terminal check returned wrong curve verdict");
    cout << name << ": PASS\n";
    return 0;
  } catch (const exception& error) {
    cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}

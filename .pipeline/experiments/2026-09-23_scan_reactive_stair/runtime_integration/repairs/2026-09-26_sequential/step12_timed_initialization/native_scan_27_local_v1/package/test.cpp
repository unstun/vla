#include <bspline_opt/uniform_bspline.h>
#include <plan_manage/seed_polyline_sampling.h>
#ifdef CANDIDATE_TIMED_CUBIC
#include <bspline_opt/timed_cubic_initialization.h>
#endif
#include <fstream>
#include <sstream>
#include <stdexcept>

using scan_planner::UniformBspline;
using Eigen::Vector3d;

void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }

void boundary(UniformBspline curve, const std::vector<Vector3d>& points,
              const std::vector<Vector3d>& derivatives) {
  auto velocity = curve.getDerivative();
  auto acceleration = velocity.getDerivative();
  const double end = curve.getTimeSum();
  require((curve.evaluateDeBoorT(0) - points.front()).norm() < 1e-6, "start position drift");
  require((curve.evaluateDeBoorT(end) - points.back()).norm() < 1e-6, "end position drift");
  require((velocity.evaluateDeBoorT(0) - derivatives[0]).norm() < 1e-6, "start velocity drift");
  require((velocity.evaluateDeBoorT(end) - derivatives[1]).norm() < 1e-6, "end velocity drift");
  require((acceleration.evaluateDeBoorT(0) - derivatives[2]).norm() < 1e-6, "start acceleration drift");
  require((acceleration.evaluateDeBoorT(end) - derivatives[3]).norm() < 1e-6, "end acceleration drift");
}

bool fit(double dt, const std::vector<Vector3d>& points, const std::vector<Vector3d>& derivatives,
         Eigen::MatrixXd& controls) {
#ifdef CANDIDATE_TIMED_CUBIC
  return reactive_stair::fitCubicBoundaryPva(dt, points, derivatives, controls);
#else
  UniformBspline::parameterizeToBspline(dt, points, derivatives, controls);
  return controls.allFinite();
#endif
}

std::vector<Vector3d> readPoints(const char* path) {
  std::ifstream stream(path);
  require(stream.good(), "missing seed fixture");
  std::vector<Vector3d> points;
  std::string line;
  while (std::getline(stream, line)) {
    std::replace(line.begin(), line.end(), ',', ' ');
    std::istringstream row(line); Vector3d p;
    require(bool(row >> p.x() >> p.y() >> p.z()), "invalid seed row");
    points.push_back(p);
  }
  return points;
}

int main(int argc, char** argv) {
  try {
    require(argc == 3, "case and seed path required");
    const std::string name = argv[1];
    std::vector<Vector3d> points;
    for (int i = 0; i < 12; ++i) points.emplace_back(0.1*i, 0.02*i*i, 0.1*std::sin(i));
    std::vector<Vector3d> derivatives = {Vector3d(.13,-.07,.02), Vector3d(-.08,.04,.03),
                                        Vector3d(.09,.11,-.06), Vector3d(-.05,.02,.08)};
    Eigen::MatrixXd controls;
    if (name == "boundary_pva" || name == "interior_invariance") {
      for (double dt : {0.0123214285714286, 0.2, 0.7}) {
        require(fit(dt, points, derivatives, controls), "fit rejected valid input");
        if (name == "interior_invariance") controls.middleCols(3, controls.cols()-6).array() += 0.017;
        boundary(UniformBspline(controls, 3, dt), points, derivatives);
      }
    } else if (name == "recorded_seed") {
      const auto raw = readPoints(argv[2]);
      const auto sampled = reactive_stair::sampleSeedPolyline(raw, .025, 5.52, 512);
      require(sampled.ready() && sampled.points.size() == 449, "captured sampling changed");
      // Exact measured velocity is read from the captured odometry fixture.
      std::ifstream derivative_stream(std::string(argv[2]) + ".pva");
      require(bool(derivative_stream >> derivatives[0].x() >> derivatives[0].y() >> derivatives[0].z()), "missing actual start velocity");
      derivatives[1].setZero(); derivatives[2].setZero(); derivatives[3].setZero();
      double dt = sampled.interval_s;
#ifdef CANDIDATE_TIMED_CUBIC
      const auto initialized = reactive_stair::initializeTimedCubic(sampled.points, derivatives, dt, 1.0, .5, 0.0);
      require(initialized.ready(), "timed initialization failed");
      controls = initialized.controls; dt = initialized.interval_s;
      std::cout << "iterations=" << initialized.iterations << " duration=" << dt*(sampled.points.size()-1) << " ";
#else
      require(fit(dt, sampled.points, derivatives, controls), "old fit failed");
#endif
      UniformBspline curve(controls, 3, dt);
      curve.setPhysicalLimits(1.0, .5, 0.0); double ratio = 0.0;
      require(curve.checkFeasibility(ratio, false), "initial curve violates native limits");
      boundary(curve, sampled.points, derivatives);
    } else if (name == "straight_control") {
      points.clear();
      for (int i=0;i<12;++i) points.emplace_back(.05*i, 0, 0);
      derivatives = {Vector3d(.1,0,0),Vector3d(.1,0,0),Vector3d::Zero(),Vector3d::Zero()};
      require(fit(.5, points, derivatives, controls), "straight fit failed");
      boundary(UniformBspline(controls,3,.5),points,derivatives);
    }
#ifdef CANDIDATE_TIMED_CUBIC
    else if (name == "invalid_input") {
      for (double dt : {0.0,-.1,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()})
        require(!fit(dt,points,derivatives,controls) && controls.size()==0, "bad interval accepted or stale output");
      auto bad = points; bad[5].x() = std::numeric_limits<double>::quiet_NaN();
      require(!fit(.1,bad,derivatives,controls), "bad point accepted");
      auto bad_derivatives = derivatives; bad_derivatives[2].z() = std::numeric_limits<double>::infinity();
      require(!fit(.1,points,bad_derivatives,controls), "bad derivative accepted");
      require(!fit(.1,std::vector<Vector3d>(6,Vector3d::Zero()),derivatives,controls), "too few points accepted");
      require(!fit(.1,points,std::vector<Vector3d>(3,Vector3d::Zero()),controls), "bad PVA layout accepted");
      require(!reactive_stair::initializeTimedCubic(points,derivatives,.1,0,.5,0).ready(), "invalid limit accepted");
      require(!reactive_stair::initializeTimedCubic(points,derivatives,.1,1,.5,0,0).ready(), "zero iteration budget accepted");
    } else if (name == "impossible_boundary") {
      derivatives[0] = Vector3d(2,0,0);
      auto result = reactive_stair::initializeTimedCubic(points,derivatives,.1,1,.5,0);
      require(!result.ready() && result.controls.size()==0 && result.iterations==0, "impossible measured velocity silently shrunk");
      derivatives[0].setZero(); derivatives[2] = Vector3d(0,.8,0);
      require(!reactive_stair::initializeTimedCubic(points,derivatives,.1,1,.5,0).ready(), "impossible measured acceleration silently shrunk");
    } else if (name == "final_pva_gate") {
      require(fit(.2,points,derivatives,controls), "hard fit failed");
      UniformBspline curve(controls,3,.2);
      require(reactive_stair::matchesBoundaryPva(curve,points.front(),points.back(),derivatives), "valid hard boundary rejected");
      auto knots=curve.getKnot(); knots*=2; curve.setKnot(knots);
      require(!reactive_stair::matchesBoundaryPva(curve,points.front(),points.back(),derivatives), "time-scaled boundary drift accepted");
      UniformBspline::parameterizeToBspline(.4,points,derivatives,controls);
      curve=UniformBspline(controls,3,.4);
      require(!reactive_stair::matchesBoundaryPva(curve,points.front(),points.back(),derivatives), "later soft refit drift accepted");
      UniformBspline empty;
      require(!reactive_stair::matchesBoundaryPva(empty,points.front(),points.back(),derivatives), "uninitialized curve accepted");
    } else if (name == "iteration_budget") {
      auto result=reactive_stair::initializeTimedCubic(points,derivatives,.001,1,.5,0,1);
      require(!result.ready() && result.iterations==1 && result.controls.size()==0, "unbounded or partial timed initialization");
    }
#endif
    else throw std::runtime_error("unknown case");
    std::cout << name << " PASS\n";
    return 0;
  } catch (const std::exception& e) { std::cerr << e.what() << "\n"; return 1; }
}

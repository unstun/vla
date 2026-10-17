// Native assignment/rebound blocks are included verbatim from the chosen build.
// Only the map, search result and ROS logger are test doubles.
#include <Eigen/Eigen>
#include <rclcpp/rclcpp.hpp>
#include <functional>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#if __has_include("rebound_constraint_utils.h")
#include "rebound_constraint_utils.h"
#endif
using namespace std;
using Eigen::Vector3d;
enum ASTAR_RET { SUCCESS, INIT_ERR, SEARCH_ERR };
struct FixtureMap {
  std::function<int(const Vector3d&, double)> query = [](const Vector3d&, double) { return 0; };
  double getResolution() const { return .05; }
  int getInflateOccupancy(const Vector3d& point, double yaw) { return query(point, yaw); }
};
struct FixtureSearch {
  ASTAR_RET result = SUCCESS;
  vector<Vector3d> path;
  ASTAR_RET AstarSearch(double, Vector3d, Vector3d) { return result; }
  vector<Vector3d> getPath() { return path; }
};
#include "native_control_points.inc"
class BsplineOptimizer {
 public:
  ControlPoints cps_;
  int order_ = 3;
  enum { DONT_STOP, STOP_FOR_REBOUND, STOP_FOR_ERROR } force_stop_type_ = DONT_STOP;
  shared_ptr<FixtureMap> grid_map_ = make_shared<FixtureMap>();
  shared_ptr<FixtureSearch> a_star_ = make_shared<FixtureSearch>();
  vector<pair<int,int>> segments_, final_segments_;
  vector<vector<Vector3d>> paths_;
  double estimateControlPointYaw(const Eigen::MatrixXd& q, int i) const {
    const Vector3d d = q.col(min(i + 1, int(q.cols()) - 1)) - q.col(max(0, i - 1));
    return d.head<2>().norm() >= .01 ? atan2(d.y(), d.x()) : 0.0;
  }
  vector<vector<Vector3d>> assignTest();
  bool check_collision_and_rebound();
};
#include "native_blocks.inc"

void require(bool ok, const char* message) { if (!ok) throw runtime_error(message); }
void initialize(BsplineOptimizer& o, int size) {
  o.cps_.resize(size);
  for (int i = 0; i < size; ++i) o.cps_.points.col(i) = Vector3d(i, 0, 0);
}
void prepareCollision(BsplineOptimizer& o) {
  initialize(o, 8);
  o.grid_map_->query = [](const Vector3d& p, double) { return p.x() >= 2 && p.x() <= 3 ? 1 : 0; };
}
void empty_route() {
  BsplineOptimizer o; prepareCollision(o);
  o.a_star_->path = {{1,0,0}};
  require(!o.check_collision_and_rebound(), "single-point repair restarted optimizer");
  require(o.force_stop_type_ == BsplineOptimizer::STOP_FOR_ERROR, "unresolved new collision did not fail closed");
}
void no_intersection() {
  BsplineOptimizer o; prepareCollision(o);
  o.a_star_->path = {{0,0,0},{0,1,0}};
  require(!o.check_collision_and_rebound(), "route without any usable intersection restarted optimizer");
  require(o.force_stop_type_ == BsplineOptimizer::STOP_FOR_ERROR, "missing constraint ignored collision");
}
void stale_intersection() {
  BsplineOptimizer o; initialize(o, 4);
  o.segments_ = o.final_segments_ = {{0,3}};
  o.paths_ = {{{.5,1,0},{1.5,1,0}}};  // Crosses CP 1's plane, never CP 2's.
  for (int i = 0; i < 4; ++i) {
    o.cps_.base_point[i].push_back({99,99,99});
    o.cps_.direction[i].push_back({0,0,1});
  }
  o.assignTest();
  require(o.cps_.base_point[1].size() == 2, "positive intersection not exercised");
  require(o.cps_.base_point[2].size() == 2 && o.cps_.direction[2].size() == 2,
          "missing intersection falsely marked valid and retained an old pair");
  require((o.cps_.direction[2].back() - Vector3d(0,1,0)).norm() < 1e-9,
          "propagation used old/uninitialized constraint instead of a fresh valid pair");
}
void zero_direction() {
  BsplineOptimizer o; initialize(o, 4);
  o.segments_ = o.final_segments_ = {{0,3}};
  o.paths_ = {{{0,0,0},{3,0,0}}};  // Intersections coincide with each control point.
  for (int i = 0; i < 4; ++i) {
    o.cps_.base_point[i].push_back({99,99,99}); o.cps_.direction[i].push_back({0,0,1});
  }
  o.assignTest();
  for (int i = 0; i < 4; ++i) {
    require(!o.cps_.flag_temp[i], "zero direction falsely marked as fresh constraint");
    require(o.cps_.base_point[i].size() == 1, "zero direction caused propagation");
  }
}
void rebound_stale_intersection() {
  BsplineOptimizer o; prepareCollision(o);
  o.a_star_->path = {{1.5,1,0},{2.5,1,0}};  // CP 2 intersects; CP 3 does not.
  for (int i = 0; i < 8; ++i) {
    o.cps_.base_point[i].push_back({0,0,-1});
    o.cps_.direction[i].push_back({0,0,1});
  }
  require(o.check_collision_and_rebound(), "valid fresh seed constraint failed to propagate");
  require(o.cps_.base_point[2].size() == 2, "positive rebound intersection not exercised");
  require(o.cps_.base_point[3].size() == 2 &&
          (o.cps_.direction[3].back() - Vector3d(0,1,0)).norm() < 1e-9,
          "rebound used stale/missing intersection instead of propagating a fresh pair");
}
void rebound_zero_direction() {
  BsplineOptimizer o; prepareCollision(o);
  o.a_star_->path = {{1,0,0},{4,0,0}};
  for (int i = 0; i < 8; ++i) {
    o.cps_.base_point[i].push_back({0,0,-1});
    o.cps_.direction[i].push_back({0,0,1});
  }
  require(!o.check_collision_and_rebound() && o.force_stop_type_ == BsplineOptimizer::STOP_FOR_ERROR,
          "zero-length rebound direction restarted optimizer");
  for (int i = 0; i < 8; ++i)
    require(o.cps_.base_point[i].size() == 1 && o.cps_.direction[i].size() == 1, "zero-length rebound committed a pair");
}
void valid_constraints() {
  BsplineOptimizer o; prepareCollision(o);
  o.a_star_->path = {{1,0,0},{1,1,0},{4,1,0},{4,0,0}};
  require(o.check_collision_and_rebound(), "valid new constraints did not request rebound");
  require(o.force_stop_type_ == BsplineOptimizer::STOP_FOR_REBOUND, "wrong successful stop state");
  for (int i = 1; i <= 4; ++i) {
    require(!o.cps_.base_point[i].empty() && o.cps_.base_point[i].size() == o.cps_.direction[i].size(), "paired constraint missing");
    require(o.cps_.base_point[i].back().allFinite() && o.cps_.direction[i].back().allFinite(), "nonfinite constraint");
    require(abs(o.cps_.direction[i].back().norm() - 1) < 1e-9, "direction is not normalized");
  }
}
void no_collision() {
  BsplineOptimizer o; initialize(o, 8);
  require(!o.check_collision_and_rebound(), "no-collision map restarted optimizer");
  require(o.force_stop_type_ == BsplineOptimizer::DONT_STOP, "no-collision map forced error");
}
void short_segment() {
  BsplineOptimizer o; initialize(o, 2);
  o.segments_ = o.final_segments_ = {{0,1}};
  o.paths_ = {{{0,.2,0},{1,.2,0}}};
  o.assignTest();
  for (int i = 0; i < 2; ++i) {
    require(o.cps_.base_point[i].size() == 1 && o.cps_.direction[i].size() == 1, "short-segment positive constraint lost");
    require((o.cps_.direction[i].back() - Vector3d(0,1,0)).norm() < 1e-9, "short-segment direction changed");
  }
}
int main(int argc, char** argv) {
  try {
    require(argc == 2, "one case required");
    string name(argv[1]);
    if (name == "empty_route") empty_route();
    else if (name == "no_intersection") no_intersection();
    else if (name == "stale_intersection") stale_intersection();
    else if (name == "zero_direction") zero_direction();
    else if (name == "rebound_stale_intersection") rebound_stale_intersection();
    else if (name == "rebound_zero_direction") rebound_zero_direction();
    else if (name == "valid_constraints") valid_constraints();
    else if (name == "no_collision") no_collision();
    else if (name == "short_segment") short_segment();
    else throw runtime_error("unknown test");
    cout << "PASS " << name << '\n'; return 0;
  } catch (const exception& e) { cerr << "FAIL " << e.what() << '\n'; return 1; }
}

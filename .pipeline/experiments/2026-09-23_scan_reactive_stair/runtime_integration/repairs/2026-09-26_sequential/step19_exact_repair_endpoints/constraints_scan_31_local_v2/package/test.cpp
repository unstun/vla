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
  struct Call { Vector3d from, to; bool exact; };
  vector<Call> calls;
  ASTAR_RET result = SUCCESS;
  vector<ASTAR_RET> result_sequence;
  bool automatic_path = false;
  vector<Vector3d> path;
  ASTAR_RET AstarSearch(double, Vector3d from, Vector3d to, bool exact = false) {
    calls.push_back({from, to, exact});
    return calls.size() <= result_sequence.size() ? result_sequence[calls.size()-1] : result;
  }
  vector<Vector3d> getPath() {
    if (!automatic_path) return path;
    const auto& c = calls.back();
    return {c.from, c.from + Vector3d(0,1,0), c.to + Vector3d(0,1,0), c.to};
  }
};
#include "native_control_points.inc"
class BsplineOptimizer {
 public:
  ControlPoints cps_;
  int order_ = 3;
  double dist0_ = .1;
  enum { DONT_STOP, STOP_FOR_REBOUND, STOP_FOR_ERROR } force_stop_type_ = DONT_STOP;
  shared_ptr<FixtureMap> grid_map_ = make_shared<FixtureMap>();
  shared_ptr<FixtureSearch> a_star_ = make_shared<FixtureSearch>();
  vector<pair<int,int>> segments_, final_segments_;
  vector<vector<Vector3d>> paths_;
  double estimateControlPointYaw(const Eigen::MatrixXd& q, int i) const {
    const Vector3d d = q.col(min(i + 1, int(q.cols()) - 1)) - q.col(max(0, i - 1));
    return d.head<2>().norm() >= .01 ? atan2(d.y(), d.x()) : 0.0;
  }
  double estimateSegmentYaw(const Vector3d& from, const Vector3d& to) const {
    const Vector3d d = to - from;
    return d.head<2>().norm() >= .01 ? atan2(d.y(), d.x()) : 0.;
  }
  vector<vector<Vector3d>> initControlPoints(Eigen::MatrixXd&, bool);
  vector<vector<Vector3d>> assignTest();
  bool check_collision_and_rebound();
};
#include "native_blocks.inc"
#if __has_include("native_init.inc")
#include "native_init.inc"
#endif

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
void valid_then_zero() {
  BsplineOptimizer o; prepareCollision(o);
  // CP 2 has a valid +Y intersection; CP 3 lies exactly on the returned route.
  o.a_star_->path = {{1,1,0},{2,1,0},{3,0,0},{4,0,0}};
  for (int i = 0; i < 8; ++i) {
    o.cps_.base_point[i].push_back({0,0,-1});
    o.cps_.direction[i].push_back({0,0,1});
  }
  require(o.check_collision_and_rebound(), "later zero direction erased the valid segment seed");
  require(o.cps_.base_point[2].size() == 2 && o.cps_.base_point[3].size() == 2,
          "valid seed did not propagate after a zero-length intersection");
  require((o.cps_.direction[3].back() - Vector3d(0,1,0)).norm() < 1e-9, "propagated an old direction");
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
#if __has_include("native_init.inc")
void prepareMode(BsplineOptimizer& o) {
  initialize(o, 12);
  o.a_star_->automatic_path = true;
  o.grid_map_->query = [](const Vector3d& p, double) {
    return p.x() >= 3. && p.x() <= 4. && abs(p.y()) < .25 ? 1 : 0;
  };
}
void checkModes(BsplineOptimizer& o, bool expected, const Eigen::MatrixXd& original) {
  require(!o.a_star_->calls.empty(), "fixture did not reach native guidance search");
  for (const auto& c : o.a_star_->calls) {
    require(c.exact == expected, "wrong exact-endpoint mode at native caller");
    bool from_column = false, to_column = false;
    for (int i = 0; i < original.cols(); ++i) {
      from_column = from_column || (original.col(i) - c.from).norm() < 1e-12;
      to_column = to_column || (original.col(i) - c.to).norm() < 1e-12;
    }
    require(from_column && to_column, "guidance search endpoints differ from original control columns");
  }
  require((original - o.cps_.points).norm() == 0., "search or assignment rewrote control points");
}
size_t pairs(const BsplineOptimizer& o) {
  size_t count = 0;
  for (int i = 0; i < o.cps_.size; ++i) {
    require(o.cps_.base_point[i].size() == o.cps_.direction[i].size(), "unpaired constraint");
    for (size_t j = 0; j < o.cps_.direction[i].size(); ++j) {
      require(o.cps_.base_point[i][j].allFinite() && o.cps_.direction[i][j].allFinite() &&
              abs(o.cps_.direction[i][j].norm() - 1.) < 1e-6, "invalid committed constraint");
      ++count;
    }
  }
  return count;
}
void init_mode(bool first) {
  BsplineOptimizer o; prepareMode(o);
  Eigen::MatrixXd input = o.cps_.points, original = input;
  const auto route = o.initControlPoints(input, first);
  checkModes(o, !first, original);
  require(!route.empty() && pairs(o) > 0, "positive guidance failed to generate paired constraints");
}
void callback_mode(bool merged) {
  BsplineOptimizer o; prepareCollision(o);
  o.a_star_->automatic_path = true;
  if (merged) {
    initialize(o, 16);
    o.grid_map_->query = [](const Vector3d& p, double) {
      return ((p.x() >= 2 && p.x() <= 3) || (p.x() >= 6 && p.x() <= 7)) && abs(p.y()) < .25 ? 1 : 0;
    };
    o.a_star_->result_sequence = {SEARCH_ERR};
  }
  const auto original = o.cps_.points;
  require(o.check_collision_and_rebound(), "checked guidance did not produce rebound constraints");
  checkModes(o, true, original);
  require(pairs(o) > 0, "rebound marked successful without paired constraints");
  if (merged) {
    require(o.a_star_->calls.size() == 2, "merged-segment retry count changed");
    const auto& first = o.a_star_->calls[0];
    const auto& retry = o.a_star_->calls[1];
    require((first.from - original.col(1)).norm() == 0. && (first.to - original.col(4)).norm() == 0. &&
            (retry.from - original.col(1)).norm() == 0. && (retry.to - original.col(8)).norm() == 0.,
            "retry dropped a segment instead of merging its endpoints");
  }
}
void failure_modes() {
  for (bool short_path : {false, true}) {
    BsplineOptimizer o; prepareMode(o);
    o.a_star_->automatic_path = false;
    o.a_star_->result = short_path ? SUCCESS : SEARCH_ERR;
    o.a_star_->path = {{2,0,0}};
    Eigen::MatrixXd input = o.cps_.points, original = input;
    o.initControlPoints(input, false);
    checkModes(o, true, original);
    require(pairs(o) == 0, "failed/short guidance created initial constraints");
    prepareCollision(o);
    o.a_star_->calls.clear();
    const auto rebound_original = o.cps_.points;
    require(!o.check_collision_and_rebound() && o.force_stop_type_ == BsplineOptimizer::STOP_FOR_ERROR,
            "failed/short guidance falsely requested rebound");
    checkModes(o, true, rebound_original);
    require(pairs(o) == 0, "failed/short guidance created rebound constraints");
  }
}
void reuse_modes() {
  BsplineOptimizer o; prepareMode(o);
  const Eigen::MatrixXd original = o.cps_.points;
  for (bool first : {true, false, true}) {
    Eigen::MatrixXd input = original;
    o.a_star_->calls.clear();
    o.initControlPoints(input, first);
    checkModes(o, !first, original);
    require(pairs(o) > 0, "reuse lost valid constraint generation");
  }
}
#endif

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
    else if (name == "valid_then_zero") valid_then_zero();
    else if (name == "valid_constraints") valid_constraints();
    else if (name == "no_collision") no_collision();
    else if (name == "short_segment") short_segment();
#if __has_include("native_init.inc")
    else if (name == "initial_mode") init_mode(true);
    else if (name == "retry_mode") init_mode(false);
    else if (name == "callback_mode") callback_mode(false);
    else if (name == "merge_mode") callback_mode(true);
    else if (name == "failure_modes") failure_modes();
    else if (name == "reuse_modes") reuse_modes();
#endif
    else throw runtime_error("unknown test");
    cout << "PASS " << name << '\n'; return 0;
  } catch (const exception& e) { cerr << "FAIL " << e.what() << '\n'; return 1; }
}

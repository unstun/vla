#include <path_searching/dyn_a_star.h>
#include <cmath>
#include <chrono>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <thread>

using Eigen::Vector3d;

void require(bool value, const char* message) {
  if (!value) throw std::runtime_error(message);
}

ASTAR_RET exactSearch(AStar& search, const Vector3d& start, const Vector3d& goal) {
#ifdef STRICT_ENDPOINT_TEST
  return search.AstarSearch(1.0, start, goal, true);
#else
  return search.AstarSearch(1.0, start, goal);
#endif
}

bool outside(const Vector3d& p) {
  return std::abs(p.z()) > 1e-9 || p.x() < -1e-9 || p.x() > 4.000001 ||
         p.y() < -1e-9 || p.y() > 1.000001;
}

void checkPath(AStar& search, const GridMap::Ptr& map, const Vector3d& start,
               const Vector3d& goal) {
  const auto path = search.getPath();
  require(!path.empty(), "successful search has no path");
  require((path.front() - start).norm() < 1e-6, "measured start moved");
  require((path.back() - goal).norm() < 1e-6, "exact goal moved");
  for (size_t i = 1; i < path.size(); ++i)
    require(map->collisionFreeSegment(path[i - 1], path[i]), "returned edge rejected by seed predicate");
}

void changed_heading() {
  auto map = std::make_shared<GridMap>();
  bool snapped_connector_rejected = false;
  map->query = [&](const Vector3d& p, double yaw) {
    if (outside(p)) return 1;
    if (p.x() >= 2 - 1e-9 && std::abs(p.y()) < 1e-9 && yaw > .1) {
      if ((p - Vector3d(3, 0, 0)).norm() < 1e-6 && std::abs(yaw - std::atan2(.2, .2)) < 1e-6)
        snapped_connector_rejected = true;
      return 1;
    }
    return 0;
  };
  const Vector3d start(0, 0, 0), goal(3.2, .2, 0);
  AStar search; search.initGridMap(map, Eigen::Vector3i(16, 16, 16));
  // Reproduce the existing manager mutation with the unchanged default mode.
  require(search.AstarSearch(1.0, start, goal) == SUCCESS, "old lattice path not reproduced");
  auto lattice = search.getPath();
  require(lattice.size() >= 2, "missing lattice path");
  for (size_t i = 1; i < lattice.size(); ++i)
    require(map->collisionFreeSegment(lattice[i - 1], lattice[i]), "original lattice edge was blocked");
  lattice.back() = goal;
  int sample = -1;
  require(!map->collisionFreeSegment(lattice[lattice.size() - 2], lattice.back(), &sample) && sample == 0,
          "endpoint replacement did not reproduce sample-zero rejection");
  snapped_connector_rejected = false;
  require(exactSearch(search, start, goal) == SUCCESS, "safe alternative connector was missed");
  checkPath(search, map, start, goal);
  require(snapped_connector_rejected, "fixture did not reject and continue after popped goal-grid connector");
}

void unknown_midpoint() {
  auto map = std::make_shared<GridMap>();
  map->resolution = .1;
  int unknown_queries = 0;
  map->query = [&](const Vector3d& p, double) {
    if (outside(p) || p.x() > 3.400001) return 1;
    if (p.x() > 3.05 && p.x() < 3.15) { ++unknown_queries; return -1; }
    return 0;
  };
  AStar search; search.initGridMap(map, Eigen::Vector3i(16, 16, 16));
  require(exactSearch(search, {0, 0, 0}, {3.4, 0, 0}) != SUCCESS,
          "unknown connector interior was bypassed by snapped-goal success");
  require(search.getPath().empty() && unknown_queries > 0, "failure retained path or missed unknown");
}

void blocked_endpoint() {
  auto map = std::make_shared<GridMap>();
  const Vector3d goal(3.2, .2, 0);
  AStar search; search.initGridMap(map, Eigen::Vector3i(16, 16, 16));
  for (int verdict : {-1, 1}) {
    int endpoint_queries = 0;
    map->query = [&](const Vector3d& p, double) {
      if (outside(p)) return 1;
      if ((p - goal).norm() < 1e-8) { ++endpoint_queries; return verdict; }
      return 0;
    };
    require(exactSearch(search, {0, 0, 0}, goal) != SUCCESS, "blocked exact endpoint accepted");
    require(search.getPath().empty() && endpoint_queries > 0, "failure retained path or did not check endpoint");
  }
}

void reuse_modes() {
  auto map = std::make_shared<GridMap>();
  map->query = [](const Vector3d& p, double) { return outside(p) ? 1 : 0; };
  AStar search; search.initGridMap(map, Eigen::Vector3i(16, 16, 16));
  require(exactSearch(search, {0, 0, 0}, {3.2, .2, 0}) == SUCCESS, "initial exact search failed");
  checkPath(search, map, {0, 0, 0}, {3.2, .2, 0});
  map->query = [](const Vector3d&, double) { return -1; };
  require(exactSearch(search, {0, 0, 0}, {3.2, .2, 0}) != SUCCESS, "fully unknown map accepted");
  require(search.getPath().empty(), "failed round exposed old exact path");
  map->query = [](const Vector3d& p, double) { return outside(p) ? 1 : 0; };
  require(search.AstarSearch(1.0, {0, 0, 0}, {2, 0, 0}) == SUCCESS, "default round failed after strict failure");
  checkPath(search, map, {0, 0, 0}, {2, 0, 0});
}

void lattice_and_short_goal() {
  auto map = std::make_shared<GridMap>();
  map->query = [](const Vector3d& p, double) { return outside(p) ? 1 : 0; };
  AStar search; search.initGridMap(map, Eigen::Vector3i(16, 16, 16));
  for (const auto& goal : {Vector3d(3, 0, 0), Vector3d(.2, .2, 0), Vector3d(0, 0, 0)}) {
    require(exactSearch(search, {0, 0, 0}, goal) == SUCCESS, "exact lattice/near/zero-distance goal failed");
    checkPath(search, map, {0, 0, 0}, goal);
  }
}

void invalid_input() {
#ifdef STRICT_ENDPOINT_TEST
  auto map = std::make_shared<GridMap>();
  int queries = 0;
  map->query = [&](const Vector3d&, double) { ++queries; return 0; };
  AStar search; search.initGridMap(map, Eigen::Vector3i(16, 16, 16));
  require(exactSearch(search, {0, 0, 0}, {1.2, .2, 0}) == SUCCESS, "reuse setup did not create exact result");
  queries = 0;
  for (double step : {0.0, -1.0, std::numeric_limits<double>::quiet_NaN()}) {
    require(search.AstarSearch(step, {0, 0, 0}, {2, 0, 0}, true) == INIT_ERR, "invalid step accepted");
    require(search.getPath().empty(), "initialization failure exposed old exact result");
  }
  require(search.AstarSearch(1.0, {0, 0, 0}, {std::numeric_limits<double>::infinity(), 0, 0}, true) == INIT_ERR,
          "nonfinite endpoint accepted");
  require(queries == 0 && search.getPath().empty(), "invalid input reached query or retained path");
#endif
}

void connector_radius() {
#ifdef STRICT_ENDPOINT_TEST
  auto map = std::make_shared<GridMap>();
  map->query = [](const Vector3d& p, double) {
    return std::abs(p.x()) > 1e-9 || std::abs(p.y()) > 1e-9 || p.z() < -1e-9 || p.z() > 3.000001 ? 1 : 0;
  };
  AStar search; search.initGridMap(map, Eigen::Vector3i(16, 16, 16));
  require(exactSearch(search, {0, 0, 0}, {0, 0, 3}) == SUCCESS, "free vertical path failed");
  checkPath(search, map, {0, 0, 0}, {0, 0, 3});
  const auto path = search.getPath();
  require(path.size() >= 3, "3D terminal radius was replaced by XY or unbounded direct connection");
  require((path.back() - path[path.size() - 2]).norm() <= 2.0 + 1e-9, "terminal connector exceeds two cells in 3D");
#endif
}

void connector_budget() {
#ifdef STRICT_ENDPOINT_TEST
  auto map = std::make_shared<GridMap>();
  const Vector3d goal(1.2, .2, 0);
  bool endpoint_checked = false;
  map->query = [&](const Vector3d& p, double) {
    if ((p - goal).norm() < 1e-8) {
      endpoint_checked = true;
      std::this_thread::sleep_for(std::chrono::milliseconds(210));
    }
    return 0;
  };
  AStar search; search.initGridMap(map, Eigen::Vector3i(16, 16, 16));
  require(exactSearch(search, {0, 0, 0}, goal) == SEARCH_ERR, "connector exceeded budget but returned success");
  require(endpoint_checked && search.getPath().empty(), "budget test did not query endpoint or retained path");
#endif
}

int main(int argc, char** argv) {
  try {
    require(argc == 2, "one case required");
    const std::string name(argv[1]);
    if (name == "changed_heading") changed_heading();
    else if (name == "unknown_midpoint") unknown_midpoint();
    else if (name == "blocked_endpoint") blocked_endpoint();
    else if (name == "reuse_modes") reuse_modes();
    else if (name == "lattice_and_short_goal") lattice_and_short_goal();
    else if (name == "invalid_input") invalid_input();
    else if (name == "connector_budget") connector_budget();
    else if (name == "connector_radius") connector_radius();
    else throw std::runtime_error("unknown case");
    std::cout << name << ": PASS\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}

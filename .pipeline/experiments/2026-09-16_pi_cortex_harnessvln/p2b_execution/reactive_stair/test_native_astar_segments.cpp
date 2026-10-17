#include <path_searching/dyn_a_star.h>
#include <plan_env/collision_segment.h>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

void require(bool value, const char* message) {
  if (!value) throw std::runtime_error(message);
}

void thin_between_nodes() {
  auto map = std::make_shared<GridMap>();
  int midpoint_rejections = 0;
  map->query = [&](const Eigen::Vector3d& p, double) {
    if (std::abs(p.z()) > 1e-9 || p.x() < 0 || p.x() > 2 || p.y() < 0 || p.y() > 1) return 1;
    if (p.x() > 0.4 && p.x() < 0.6 && p.y() < 0.2) { ++midpoint_rejections; return 1; }
    return 0;
  };
  AStar search; search.initGridMap(map, Eigen::Vector3i(12, 12, 12));
  require(search.AstarSearch(1.0, {0, 0, 0}, {2, 0, 0}) == SUCCESS, "detour exists but search failed");
  const auto path = search.getPath();
  require(path.size() >= 3, "path missing");
  bool detour = false;
  for (size_t i = 1; i < path.size(); ++i) {
    if (path[i].y() > 0.2) detour = true;
    int blocked = -1;
    if (!map->collisionFreeSegment(path[i - 1], path[i], &blocked)) {
      std::cerr << "edge=" << i << " blocked_sample=" << blocked << '\n';
      throw std::runtime_error("search accepted an edge rejected by seed validation");
    }
  }
  require(detour && midpoint_rejections > 0, "fixture did not use the verified detour");
}

void segment_contract() {
  const Eigen::Vector3d from(0, 0, 0), to(1, 0, 0);
  int calls = 0, blocked = -1;
  auto query = [&](const Eigen::Vector3d& p, double yaw) {
    ++calls;
    require(yaw == 0.25, "heading changed within segment");
    return std::abs(p.x() - 0.5) < 1e-8 ? -1 : 0;  // Unknown remains blocked.
  };
  require(!reactive_stair::collisionFreeSegment(from, to, 1.0, 0.25, query, &blocked), "unknown midpoint accepted");
  require(calls == 2 && blocked == 1, "half-cell sample location changed");
  calls = 0;
  require(!reactive_stair::collisionFreeSegment(from, to, 0.0, 0.25, query), "invalid resolution accepted");
  require(!reactive_stair::collisionFreeSegment(from, to, 1.0, std::numeric_limits<double>::quiet_NaN(), query), "invalid yaw accepted");
  require(calls == 0, "invalid segment reached occupancy query");
}

int main(int argc, char** argv) {
  try {
    require(argc == 2, "one case required");
    if (std::string(argv[1]) == "thin_between_nodes") thin_between_nodes();
    else if (std::string(argv[1]) == "segment_contract") segment_contract();
    else throw std::runtime_error("unknown case");
    std::cout << argv[1] << ": PASS\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}

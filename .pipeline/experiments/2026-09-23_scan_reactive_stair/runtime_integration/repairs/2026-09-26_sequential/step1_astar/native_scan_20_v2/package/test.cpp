// Compile the actual native AStar source; mock only its occupancy and logger.
#include <path_searching/dyn_a_star.h>
#include <cmath>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>
#include <array>
#include <limits>
#include <cstdint>

using Eigen::Vector3d;
using Eigen::Vector3i;
using Cell = std::tuple<int, int, int>;

void require(bool condition, const char* message) {
  if (!condition) throw std::runtime_error(message);
}

Cell key(const Vector3d& p) {
  return {std::lround(p.x()), std::lround(p.y()), std::lround(p.z())};
}

void validate(AStar& search, GridMap::Ptr map, const Vector3d& start,
              const Vector3d& goal) {
  const auto path = search.getPath();
  require(path.size() >= 2, "successful search has no path");
  require((path.front() - start).norm() < 1e-10, "start moved");
  require((path.back() - goal).norm() < 1e-10, "goal moved");
  for (size_t i = 1; i < path.size(); ++i) {
    const auto delta = path[i] - path[i - 1];
    const double yaw = delta.head<2>().norm() < 1e-10
        ? std::atan2(goal.y() - start.y(), goal.x() - start.x())
        : std::atan2(delta.y(), delta.x());
    require(!map->getInflateOccupancy(path[i], yaw), "path uses rejected node");
  }
}

void blocked_first(bool reuse) {
  const std::set<Cell> allowed{{0, 0, 0}, {0, 1, 0}, {1, 1, 0}, {2, 1, 0}};
  int rejected_gateway = 0, accepted_gateway = 0;
  bool directional = !reuse;
  auto map = std::make_shared<GridMap>();
  map->query = [&](const Vector3d& point, double yaw) {
    const auto cell = key(point);
    if (!allowed.count(cell)) return 1;
    if (cell == Cell(1, 1, 0) && directional) {
      if (std::abs(std::sin(yaw)) > 1e-7) { ++rejected_gateway; return 1; }
      ++accepted_gateway;
    }
    return 0;
  };
  AStar search;
  search.initGridMap(map, Vector3i(12, 12, 12));
  const Vector3d start(0, 0, 0), goal(2, 1, 0);
  if (reuse) {
    require(search.AstarSearch(1.0, start, goal) == SUCCESS, "first search failed");
    validate(search, map, start, goal);
    directional = true;
  }
  const auto status = search.AstarSearch(1.0, start, goal);
  std::cout << "status=" << status << " rejected_gateway=" << rejected_gateway
            << " accepted_gateway=" << accepted_gateway << '\n';
  require(rejected_gateway > 0, "fixture did not exercise blocked first approach");
  require(status == SUCCESS, "reachable gateway was lost");
  require(accepted_gateway > 0, "fixture did not exercise accepted approach");
  validate(search, map, start, goal);
}

void queue_order() {
  GridNode a, b, c;
  for (auto* node : {&a, &b, &c}) {
    node->rounds = 1;
    node->state = GridNode::OPENSET;
  }
  a.fScore = a.gScore = 10; b.fScore = b.gScore = 20; c.fScore = c.gScore = 30;
#ifdef FIXED_QUEUE_TEST
  for (auto* node : {&a, &b, &c}) node->queue_revision = 1;
  std::priority_queue<OpenSetEntry, std::vector<OpenSetEntry>, NodeComparator> queue;
  queue.emplace(&a); queue.emplace(&b); queue.emplace(&c);
  const OpenSetEntry original_c(&c);
  c.fScore = c.gScore = 1;
  c.cameFrom = &b;
  ++c.queue_revision;
  require(!original_c.current(1), "old revision still valid while node is OPEN");
  queue.emplace(&c);
  std::vector<GridNodePtr> order;
  int stale = 0;
  while (!queue.empty()) {
    const auto entry = queue.top(); queue.pop();
    if (!entry.current(1)) { ++stale; continue; }
    order.push_back(entry.node);
    entry.node->state = GridNode::CLOSEDSET;
  }
  require(order == std::vector<GridNodePtr>({&c, &a, &b}), "decreased key pop order incorrect");
  require(stale == 1, "obsolete entry was not discarded exactly once");
  require(c.cameFrom == &b, "improved parent was lost");
  c.state = GridNode::OPENSET;
  OpenSetEntry previous(&c);
  ++c.rounds;
  require(!previous.current(2), "old search round entry accepted");
#else
  std::priority_queue<GridNodePtr, std::vector<GridNodePtr>, NodeComparator> queue;
  queue.push(&a); queue.push(&b); queue.push(&c);
  c.fScore = c.gScore = 1;  // The original native decrease-key branch.
  require(queue.top() == &c, "mutable pointer score did not repair heap order");
#endif
}

void no_path() {
  auto map = std::make_shared<GridMap>();
  map->query = [](const Vector3d& p, double) {
    return key(p) == Cell(0, 0, 0) || key(p) == Cell(3, 0, 0) ? 0 : 1;
  };
  AStar search; search.initGridMap(map, Vector3i(12, 12, 12));
  require(search.AstarSearch(1.0, Vector3d(0, 0, 0), Vector3d(3, 0, 0)) == SEARCH_ERR,
          "blocked graph must remain rejected");
}

void vertical_route() {
  auto map = std::make_shared<GridMap>();
  map->query = [](const Vector3d& p, double) {
    return p.x() < 0 || p.x() > 3 || p.y() < 0 || p.y() > 3 || p.z() < 0 || p.z() > 3;
  };
  AStar search; search.initGridMap(map, Vector3i(12, 12, 12));
  const Vector3d start(0, 0, 0), goal(2, 1, 2);
  require(search.AstarSearch(1.0, start, goal) == SUCCESS, "3D free route failed");
  validate(search, map, start, goal);
}

void improved_cost() {
  // Independent Dijkstra oracle on small fixed-seed occupancy maps. This
  // reaches the real native improved-OPEN-node branch, unlike a heap-only test.
  constexpr int side = 8;
  for (std::uint32_t fixture = 0; fixture < 256; ++fixture) {
    std::uint32_t rng = 0xA57A0000u + fixture;
    std::array<bool, side * side> free{};
    for (auto& cell : free) {
      rng = 1664525u * rng + 1013904223u;
      cell = ((rng >> 24) % 100) >= 32;
    }
    free[0] = free.back() = true;
    std::array<double, side * side> distance;
    distance.fill(std::numeric_limits<double>::infinity());
    distance[0] = 0;
    using Entry = std::pair<double, int>;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> frontier;
    frontier.emplace(0, 0);
    while (!frontier.empty()) {
      const auto item = frontier.top(); frontier.pop();
      if (item.first != distance[item.second]) continue;
      const int x = item.second / side, y = item.second % side;
      for (int dx = -1; dx <= 1; ++dx) for (int dy = -1; dy <= 1; ++dy) {
        const int nx = x + dx, ny = y + dy;
        if ((dx == 0 && dy == 0) || nx < 0 || nx >= side || ny < 0 || ny >= side) continue;
        const int next = nx * side + ny;
        const double candidate = item.first + std::hypot(dx, dy);
        if (free[next] && candidate < distance[next]) {
          distance[next] = candidate;
          frontier.emplace(candidate, next);
        }
      }
    }
    auto map = std::make_shared<GridMap>();
    map->query = [&](const Vector3d& p, double) {
      const int x = std::lround(p.x()), y = std::lround(p.y());
      if (std::abs(p.z()) > 1e-9 || x < 0 || x >= side || y < 0 || y >= side) return 1;
      return free[x * side + y] ? 0 : 1;
    };
    AStar search; search.initGridMap(map, Vector3i(24, 24, 8));
    const Vector3d start(0, 0, 0), goal(side - 1, side - 1, 0);
    const auto status = search.AstarSearch(1.0, start, goal);
    if (!std::isfinite(distance.back())) {
      require(status == SEARCH_ERR, "native accepted disconnected graph");
      continue;
    }
    if (status != SUCCESS) {
      std::cerr << "reachable fixture=" << fixture << " native_status=" << status << '\n';
      throw std::runtime_error("native queue lost a reachable fixture");
    }
    validate(search, map, start, goal);
    const auto path = search.getPath();
    double cost = 0;
    for (size_t i = 1; i < path.size(); ++i) cost += (path[i] - path[i - 1]).norm();
    // Retain room for the upstream 1.0001 weighted heuristic; this is not
    // silently imposing exact optimality on the planner.
    if (cost > distance.back() * 1.0002 + 1e-9) {
      std::cerr << "fixture=" << fixture << " oracle_cost=" << distance.back()
                << " native_cost=" << cost << '\n';
      throw std::runtime_error("improved-node queue integration lost the better path");
    }
  }
}

int main(int argc, char** argv) {
  try {
    require(argc == 2, "one case name required");
    const std::string name(argv[1]);
    if (name == "blocked_first") blocked_first(false);
    else if (name == "queue_order") queue_order();
    else if (name == "round_reuse") blocked_first(true);
    else if (name == "no_path") no_path();
    else if (name == "vertical_route") vertical_route();
    else if (name == "improved_cost") improved_cost();
    else throw std::runtime_error("unknown case");
    std::cout << name << ": PASS\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}

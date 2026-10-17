#ifndef VLA_SEARCH_FRONTIER_TRACE_H
#define VLA_SEARCH_FRONTIER_TRACE_H
// Diagnostic-only observer. No additional map query or search decision.
#include <array>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <vector>

namespace stair_trace {
struct Scope;
inline Scope *active = nullptr;
struct Scope {
  struct Query { int edge, verdict, occupancy; double x, y, z; };
  bool enabled;
  const char *reason = "exhausted";
  size_t dropped = 0;
  int edge = 0;
  std::vector<std::array<double, 7>> edges;
  std::vector<std::array<double, 4>> nodes;
  std::vector<Query> queries;
  std::array<double, 6> endpoints{}, adjusted{};
  std::chrono::steady_clock::time_point start;
  Scope(bool value) : enabled(value), start(std::chrono::steady_clock::now()) {
    if (enabled) { active = this; queries.reserve(100000); }
  }
  void nextEdge(double ax, double ay, double az, double bx, double by, double bz) {
    if (!enabled) return;
    edges.push_back({ax, ay, az, bx, by, bz, -1.});
    edge = static_cast<int>(edges.size());
  }
  void endEdge(bool clear) {
    if (enabled) edges.back()[6] = clear ? 1. : 0.;
  }
  ~Scope() {
    if (!enabled) return;
    active = nullptr;
    const double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    const auto emit_start = std::chrono::steady_clock::now();
    std::ostringstream output;
    output << std::setprecision(12) << "STF_SUMMARY," << reason << ',' << nodes.size()
              << ',' << edges.size() << ',' << queries.size() << ',' << dropped << ',' << elapsed << '\n';
    output << "STF_INPUT"; for (double v : endpoints) output << ',' << v; output << '\n';
    output << "STF_ADJUSTED"; for (double v : adjusted) output << ',' << v; output << '\n';
    for (const auto &v : nodes) { output << "STF_NODE"; for (double x : v) output << ',' << x; output << '\n'; }
    for (size_t i = 0; i < edges.size(); ++i) { output << "STF_EDGE," << i + 1; for (double x : edges[i]) output << ',' << x; output << '\n'; }
    for (const auto &v : queries) output << "STF_QUERY," << v.edge << ',' << v.verdict << ',' << v.occupancy
      << ',' << v.x << ',' << v.y << ',' << v.z << '\n';
    std::cerr << output.str();
    std::cerr << "STF_EMIT_WALL_S," << std::chrono::duration<double>(std::chrono::steady_clock::now() - emit_start).count() << '\n';
  }
};
inline void query(double x, double y, double z, int verdict, int occupancy) {
  if (!active) return;
  if (active->queries.size() < 500000)
    active->queries.push_back({active->edge, verdict, occupancy, x, y, z});
  else ++active->dropped;
}
}  // namespace stair_trace
#endif

#pragma once
#include <Eigen/Core>
#include <rclcpp/rclcpp.hpp>
#include <sstream>
#include <string>
#include <vector>

namespace reactive_stair {
struct OptimizerTraceState {
  bool active = false;
  int replan_calls = 0;
  int search_calls = 0;
  size_t dropped = 0;
  std::vector<std::string> lines;
};
inline OptimizerTraceState& optimizerTraceState() {
  static OptimizerTraceState state;
  return state;
}
template <typename... Args>
void optimizerTrace(Args&&... args) {
  auto& state = optimizerTraceState();
  if (!state.active) return;
  if (state.lines.size() >= 20000) { ++state.dropped; return; }
  std::ostringstream out;
  out.precision(17);
  (out << ... << args);
  state.lines.push_back(out.str());
}
inline std::string tracePoint(const Eigen::Vector3d& p) {
  std::ostringstream out;
  out.precision(17);
  out << '(' << p.x() << ',' << p.y() << ',' << p.z() << ')';
  return out.str();
}
inline void traceMatrix(const char* stage, const Eigen::MatrixXd& points) {
  if (!optimizerTraceState().active) return;
  optimizerTrace("OPT_TRACE matrix=", stage, " rows=", points.rows(), " columns=", points.cols());
  for (int i = 0; i < points.cols(); ++i)
    optimizerTrace("OPT_TRACE point stage=", stage, " index=", i, " p=", tracePoint(points.col(i)));
}
inline void tracePoints(const char* stage, const std::vector<Eigen::Vector3d>& points) {
  if (!optimizerTraceState().active) return;
  optimizerTrace("OPT_TRACE vector=", stage, " count=", points.size());
  for (size_t i = 0; i < points.size(); ++i)
    optimizerTrace("OPT_TRACE point stage=", stage, " index=", i, " p=", tracePoint(points[i]));
}
// Shared inline state spans manager/optimizer/search translation units. Log
// emission is deferred until the first planning call has already returned.
struct OptimizerTraceScope {
  bool owned = false;
  OptimizerTraceScope() {
    auto& state = optimizerTraceState();
    owned = state.replan_calls++ == 0;
    state.active = owned;
    if (owned) optimizerTrace("OPT_TRACE begin replan=0");
  }
  ~OptimizerTraceScope() {
    auto& state = optimizerTraceState();
    if (!owned) return;
    state.active = false;
    for (const auto& line : state.lines)
      RCLCPP_WARN(rclcpp::get_logger("optimizer_trace"), "%s", line.c_str());
    RCLCPP_WARN(rclcpp::get_logger("optimizer_trace"),
                "OPT_TRACE end records=%zu dropped=%zu searches=%d", state.lines.size(), state.dropped, state.search_calls);
  }
};
}  // namespace reactive_stair

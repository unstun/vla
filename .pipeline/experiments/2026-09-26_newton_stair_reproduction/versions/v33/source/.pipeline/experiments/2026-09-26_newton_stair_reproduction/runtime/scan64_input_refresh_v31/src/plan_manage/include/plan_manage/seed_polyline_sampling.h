#pragma once
#include <Eigen/Core>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <numeric>
#include <vector>

namespace reactive_stair {
enum class SeedSamplingStatus { Ready, InvalidInput, DegeneratePath, BudgetExceeded };
struct SeedSamplingResult {
  SeedSamplingStatus status = SeedSamplingStatus::InvalidInput;
  std::vector<Eigen::Vector3d> points;
  std::vector<size_t> parent_edges;
  // Indices of distinct input vertices in output points and original raw path.
  std::vector<size_t> vertex_indices;
  std::vector<size_t> source_vertex_indices;
  std::vector<size_t> intervals_per_edge;
  double interval_s = 0.0;
  double max_vertex_time_error_s = 0.0;
  bool temporal_budget_capped = false;
  size_t exact_duplicates_removed = 0;
  bool ready() const { return status == SeedSamplingStatus::Ready; }
};

inline double inverseQuinticProgress(double progress) {
  if (progress <= 0.0) return 0.0;
  if (progress >= 1.0) return 1.0;
  double low = 0.0, high = 1.0;
  for (int i = 0; i < 64; ++i) {
    const double u = 0.5 * (low + high);
    const double value = u * u * u * (10.0 - 15.0 * u + 6.0 * u * u);
    if (value < progress) low = u;
    else high = u;
  }
  return 0.5 * (low + high);
}

// Geometry is hard: every nonzero input edge and vertex is retained. The old
// quintic progress is a time-allocation target, not a geometric shortcut.
// Callers must recheck each output edge with the actual heading predicate;
// a short subedge can use a different fallback yaw than its parent edge.
inline SeedSamplingResult sampleSeedPolyline(const std::vector<Eigen::Vector3d>& raw,
                                              double max_spacing_m, double duration_s,
                                              size_t max_points = 512) {
  SeedSamplingResult result;
  if (raw.size() < 2 || !std::isfinite(max_spacing_m) || max_spacing_m <= 0.0 ||
      !std::isfinite(duration_s) || duration_s <= 0.0 || max_points < 2 || max_points > 4096)
    return result;
  std::vector<Eigen::Vector3d> vertices;
  std::vector<size_t> source_edges;
  for (size_t raw_index = 0; raw_index < raw.size(); ++raw_index) {
    const auto& p = raw[raw_index];
    if (!p.allFinite()) return result;
    if (!vertices.empty() && (p.array() == vertices.back().array()).all()) {
      ++result.exact_duplicates_removed;
      continue;
    }
    if (!vertices.empty()) source_edges.push_back(raw_index - 1);
    vertices.push_back(p);
    result.source_vertex_indices.push_back(raw_index);
  }
  if (vertices.size() < 2) { result.status = SeedSamplingStatus::DegeneratePath; return result; }
  const size_t edge_count = vertices.size() - 1, budget = max_points - 1;
  std::vector<double> lengths, cumulative(1, 0.0), times(1, 0.0), weights;
  std::vector<size_t> minimum;
  size_t minimum_total = 0;
  for (size_t i = 0; i < edge_count; ++i) {
    const double length = (vertices[i + 1] - vertices[i]).norm();
    if (!std::isfinite(length) || length <= 0.0) return result;
    const double required = std::ceil(length / max_spacing_m);
    if (!std::isfinite(required) || required > static_cast<double>(budget - minimum_total)) {
      result.status = SeedSamplingStatus::BudgetExceeded;
      return result;
    }
    const size_t count = std::max<size_t>(1, static_cast<size_t>(required));
    if (count > budget - minimum_total) { result.status = SeedSamplingStatus::BudgetExceeded; return result; }
    minimum.push_back(count);
    minimum_total += count;
    lengths.push_back(length);
    cumulative.push_back(cumulative.back() + length);
    if (!std::isfinite(cumulative.back())) return result;
  }
  double ideal_intervals = static_cast<double>(minimum_total);
  for (size_t i = 0; i < edge_count; ++i) {
    const double target = i + 1 == edge_count ? 1.0 : inverseQuinticProgress(cumulative[i + 1] / cumulative.back());
    const double weight = target - times.back();
    if (!std::isfinite(weight) || weight < 0.0) return result;
    weights.push_back(weight);
    times.push_back(target);
    const double need = weight > 0.0 ? std::ceil(minimum[i] / weight) : std::numeric_limits<double>::infinity();
    ideal_intervals = std::max(ideal_intervals, need);
  }
  result.temporal_budget_capped = ideal_intervals > static_cast<double>(budget);
  const size_t total = result.temporal_budget_capped ? budget : static_cast<size_t>(ideal_intervals);

  // Lower-bounded proportional quotas, then deterministic largest remainders.
  // Capping temporal fidelity never removes a vertex or violates spacing.
  double low = 0.0, high = static_cast<double>(total);
  for (int iteration = 0; iteration < 80; ++iteration) {
    const double scale = 0.5 * (low + high);
    double sum = 0.0;
    for (size_t i = 0; i < edge_count; ++i) sum += std::max(static_cast<double>(minimum[i]), scale * weights[i]);
    if (sum <= static_cast<double>(total)) low = scale;
    else high = scale;
  }
  std::vector<double> remainders;
  std::vector<size_t> order(edge_count);
  size_t assigned = 0;
  for (size_t i = 0; i < edge_count; ++i) {
    const double quota = std::max(static_cast<double>(minimum[i]), low * weights[i]);
    const size_t count = static_cast<size_t>(std::floor(quota));
    result.intervals_per_edge.push_back(count);
    assigned += count;
    remainders.push_back(quota - count);
    order[i] = i;
  }
  if (assigned > total || total - assigned > edge_count) return result;
  std::sort(order.begin(), order.end(), [&](size_t a, size_t b) {
    return remainders[a] == remainders[b] ? a < b : remainders[a] > remainders[b];
  });
  for (size_t i = 0; i < total - assigned; ++i) ++result.intervals_per_edge[order[i]];
  result.interval_s = duration_s / static_cast<double>(total);
  if (!std::isfinite(result.interval_s) || result.interval_s <= 0.0) return result;
  result.points.reserve(total + 1);
  result.parent_edges.reserve(total);
  result.points.push_back(vertices.front());
  result.vertex_indices.push_back(0);
  for (size_t i = 0; i < edge_count; ++i) {
    const size_t count = result.intervals_per_edge[i];
    const Eigen::Vector3d delta = vertices[i + 1] - vertices[i];
    for (size_t j = 1; j <= count; ++j) {
      result.points.push_back(j == count ? vertices[i + 1] : vertices[i] + delta * (static_cast<double>(j) / count));
      result.parent_edges.push_back(source_edges[i]);
    }
    result.vertex_indices.push_back(result.points.size() - 1);
    const double actual_time = (result.points.size() - 1) * result.interval_s;
    result.max_vertex_time_error_s = std::max(result.max_vertex_time_error_s, std::abs(actual_time - duration_s * times[i + 1]));
  }
  result.status = SeedSamplingStatus::Ready;
  return result;
}
}  // namespace reactive_stair

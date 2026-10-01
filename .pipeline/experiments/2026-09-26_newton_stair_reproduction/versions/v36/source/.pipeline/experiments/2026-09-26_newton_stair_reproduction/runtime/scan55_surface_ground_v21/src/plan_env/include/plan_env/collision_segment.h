#ifndef VLA_COLLISION_SEGMENT_H
#define VLA_COLLISION_SEGMENT_H
#include <Eigen/Core>
#include <algorithm>
#include <cmath>
#include <limits>

namespace reactive_stair {
// The existing seed validator samples both ends and at most half a map cell
// between samples. Search and seed acceptance must use this same predicate.
template <typename OccupancyQuery>
bool collisionFreeSegment(const Eigen::Vector3d& from, const Eigen::Vector3d& to,
                          double resolution, double yaw, OccupancyQuery occupied,
                          int* blocked_sample = nullptr) {
  if (blocked_sample) *blocked_sample = -1;
  if (!from.allFinite() || !to.allFinite() || !std::isfinite(resolution) ||
      resolution <= 0.0 || !std::isfinite(yaw)) return false;
  const Eigen::Vector3d delta = to - from;
  const double intervals = std::ceil(delta.norm() / (0.5 * resolution));
  if (!std::isfinite(intervals) || intervals > std::numeric_limits<int>::max() - 1)
    return false;
  const int count = std::max(1, static_cast<int>(intervals));
  for (int j = 0; j <= count; ++j) {
    const Eigen::Vector3d sample = from + delta * (static_cast<double>(j) / count);
    if (occupied(sample, yaw)) {
      if (blocked_sample) *blocked_sample = j;
      return false;
    }
  }
  return true;
}
}  // namespace reactive_stair
#endif

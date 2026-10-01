#pragma once
#include <Eigen/Core>
#include <cmath>
#include <cstddef>
#include <algorithm>
#include <limits>
#include <vector>

namespace reactive_stair {
// A control-specific geometric candidate, never an occupancy verdict. Callers
// must check it with that control's heading before using the original base ray.
inline bool nearestPointOnMatchingRoute(const std::vector<Eigen::Vector3d>& route,
    const Eigen::Vector3d& start, const Eigen::Vector3d& end,
    const Eigen::Vector3d& query, Eigen::Vector3d& nearest) {
  nearest.setZero();
  if (route.size() < 2 || !start.allFinite() || !end.allFinite() || !query.allFinite()) return false;
  for (const auto& p : route) if (!p.allFinite()) return false;
  if ((route.front() - start).norm() > 1e-6 || (route.back() - end).norm() > 1e-6) return false;
  double best_squared_distance = std::numeric_limits<double>::infinity();
  Eigen::Vector3d candidate = Eigen::Vector3d::Zero();
  for (size_t i = 1; i < route.size(); ++i) {
    const Eigen::Vector3d delta = route[i] - route[i - 1];
    const double squared_length = delta.squaredNorm();
    if (!std::isfinite(squared_length)) return false;
    if (squared_length == 0.0) continue;
    const double raw_u = (query - route[i - 1]).dot(delta) / squared_length;
    if (!std::isfinite(raw_u)) return false;
    const double u = std::max(0.0, std::min(1.0, raw_u));
    const Eigen::Vector3d projected = u == 0.0 ? route[i - 1] :
        (u == 1.0 ? route[i] : Eigen::Vector3d(route[i - 1] + u * delta));
    const double squared_distance = (projected - query).squaredNorm();
    if (!projected.allFinite() || !std::isfinite(squared_distance)) return false;
    // Strict comparison keeps the first edge in an equal-distance tie.
    if (squared_distance < best_squared_distance) {
      best_squared_distance = squared_distance;
      candidate = projected;
    }
  }
  if (!std::isfinite(best_squared_distance) || std::sqrt(best_squared_distance) <= 1e-5) return false;
  nearest = candidate;
  return true;
}

template <typename ControlPoints>
bool validReboundSlot(const ControlPoints& controls, int index) {
  return index >= 0 && index < controls.size &&
         static_cast<size_t>(index) < controls.base_point.size() &&
         static_cast<size_t>(index) < controls.direction.size() &&
         static_cast<size_t>(index) < controls.flag_temp.size();
}

// A temporary success flag always denotes a paired, finite write in this pass.
// Reserve both arrays before changing either logical size.
template <typename ControlPoints>
bool appendReboundConstraint(ControlPoints& controls, int index,
                             const Eigen::Vector3d& base,
                             const Eigen::Vector3d& direction) {
  if (!validReboundSlot(controls, index) || !base.allFinite() || !direction.allFinite()) return false;
  const double norm = direction.norm();
  if (!std::isfinite(norm) || std::abs(norm - 1.0) > 1e-6) return false;
  auto& bases = controls.base_point[index];
  auto& directions = controls.direction[index];
  if (bases.size() != directions.size()) return false;
  // Copy arguments before reserve; callers can supply existing vector entries.
  const Eigen::Vector3d saved_base = base, saved_direction = direction;
  bases.reserve(bases.size() + 1);
  directions.reserve(directions.size() + 1);
  bases.push_back(saved_base);
  directions.push_back(saved_direction);
  controls.flag_temp[index] = true;
  return true;
}

template <typename ControlPoints>
bool copyReboundConstraint(ControlPoints& controls, int target, int source) {
  if (target == source || !validReboundSlot(controls, source) || !controls.flag_temp[source] ||
      controls.base_point[source].empty() ||
      controls.base_point[source].size() != controls.direction[source].size()) return false;
  return appendReboundConstraint(controls, target, controls.base_point[source].back(),
                                 controls.direction[source].back());
}
}  // namespace reactive_stair

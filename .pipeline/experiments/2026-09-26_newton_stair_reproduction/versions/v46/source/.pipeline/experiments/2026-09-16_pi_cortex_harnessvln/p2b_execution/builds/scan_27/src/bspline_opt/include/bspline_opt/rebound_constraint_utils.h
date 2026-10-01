#pragma once
#include <Eigen/Core>
#include <cmath>
#include <cstddef>

namespace reactive_stair {
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

#pragma once
#include <Eigen/Eigen>
#include <functional>
#include <memory>
#if __has_include(<plan_env/collision_segment.h>)
#include <plan_env/collision_segment.h>
#endif

// Collision boundary only. The search implementation and header under test
// are compiled unmodified from each captured native source tree.
class GridMap {
 public:
  using Ptr = std::shared_ptr<GridMap>;
  std::function<int(const Eigen::Vector3d&, double)> query;
  int getInflateOccupancy(const Eigen::Vector3d& position, double yaw) {
    return query(position, yaw);
  }
#if __has_include(<plan_env/collision_segment.h>)
  double resolution = 1.0;
  bool collisionFreeSegment(const Eigen::Vector3d& from, const Eigen::Vector3d& to,
                            int* blocked_sample = nullptr) {
    const auto delta = to - from;
    const double yaw = delta.head<2>().norm() >= 0.01 ? std::atan2(delta.y(), delta.x()) : 0.0;
    return reactive_stair::collisionFreeSegment(from, to, resolution, yaw,
        [this](const Eigen::Vector3d& p, double heading) { return getInflateOccupancy(p, heading); },
        blocked_sample);
  }
#endif
};

#pragma once
#include <Eigen/Eigen>
#include <functional>
#include <memory>

// Collision boundary only. The search implementation and header under test
// are compiled unmodified from each captured native source tree.
class GridMap {
 public:
  using Ptr = std::shared_ptr<GridMap>;
  std::function<int(const Eigen::Vector3d&, double)> query;
  int getInflateOccupancy(const Eigen::Vector3d& position, double yaw) {
    return query(position, yaw);
  }
};

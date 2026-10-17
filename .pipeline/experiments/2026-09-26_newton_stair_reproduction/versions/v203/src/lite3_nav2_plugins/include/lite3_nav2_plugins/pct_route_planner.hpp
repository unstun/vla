#pragma once

#include <Eigen/Core>
#include <ele_planner/offline_ele_planner.h>
#include <cstdint>
#include <string>
#include <vector>

namespace lite3_nav2
{
class PCTRoutePlanner
{
public:
  PCTRoutePlanner(const std::string &bundle, double reference_height,
                  bool quintic=true, double max_heading_rate=10.0);
  Eigen::Vector3i poseToIndex(const Eigen::Vector3d &pose) const;
  std::vector<Eigen::Vector3d> plan(const Eigen::Vector3d &start, const Eigen::Vector3d &goal);
private:
  int layers_{0}, nx_{0}, ny_{0};
  double resolution_{0}, cx_{0}, cy_{0}, h0_{0}, dh_{0};
  bool quintic_;
  Eigen::MatrixXd ground_;
  std::vector<uint8_t> ground_valid_;
  OfflineElePlanner planner_;
};
}  // namespace lite3_nav2

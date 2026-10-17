#pragma once

#include <Eigen/Core>
#include <plan_env/environmental_field.h>
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
  struct RejectedPose {Eigen::Vector3d position; double yaw; bool all_headings{false};};
  void setEnvironmentalField(std::shared_ptr<const reactive_stair::EnvironmentalField> field) { environment_=std::move(field);rebuildMap(); }
  double environmentalCost(const Eigen::Vector3d &p,double yaw) const { return environment_ ? environment_->cost(p,yaw) : 0.; }
  void clearRepairConstraints();
  void setFeedbackConstraints(const std::vector<RejectedPose> &poses);
  bool rejectedAt(const Eigen::Vector3d &position,double yaw,bool feedback_only=false) const;
  void addRepairConstraints(const std::vector<RejectedPose> &poses);
  Eigen::Vector3i poseToIndex(const Eigen::Vector3d &pose) const;
  std::vector<Eigen::Vector3d> plan(const Eigen::Vector3d &start, const Eigen::Vector3d &goal,bool smooth=true);
private:
  int layers_{0}, nx_{0}, ny_{0};
  double resolution_{0}, cx_{0}, cy_{0}, h0_{0}, dh_{0};
  bool quintic_;
  std::shared_ptr<const reactive_stair::EnvironmentalField> environment_;
  void rebuildMap();
  void projectSupportHeights(std::vector<Eigen::Vector3d> &points,const Eigen::VectorXd &layers,
      const Eigen::Vector3d &start,const Eigen::Vector3d &goal) const;
  bool transitionAllowed(const Node &from,const Node &to) const;
  double reference_height_{0};
  Eigen::MatrixXd costs_,ground_,ceiling_,gateway_,grad_x_,grad_y_;
  std::vector<RejectedPose> rejected_,feedback_;
  std::vector<uint8_t> ground_valid_;
  OfflineElePlanner planner_;
};
}  // namespace lite3_nav2

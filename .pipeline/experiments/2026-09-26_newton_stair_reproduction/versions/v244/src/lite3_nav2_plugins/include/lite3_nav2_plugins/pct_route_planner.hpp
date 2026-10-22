#pragma once

#include <Eigen/Core>
#include <plan_env/environmental_field.h>
#include <ele_planner/offline_ele_planner.h>
#include <cstdint>
#include <string>
#include <vector>
#include <functional>
#include <lite3_nav2_plugins/static_body_geometry.hpp>
#include <plan_env/support_gap_mask.h>

namespace lite3_nav2
{
class PCTRoutePlanner
{
public:
  PCTRoutePlanner(const std::string &bundle, double reference_height,
                  bool quintic=true, double max_heading_rate=10.0);
  struct RejectedPose {Eigen::Vector3d position; double yaw; bool all_headings{false};};
  using EndpointCheck=std::function<bool(const std::vector<RejectedPose>&)>;
  void enableEndpointRecovery(std::shared_ptr<const StaticBodyGeometry> body,
    std::shared_ptr<const reactive_stair::SupportGapMask> gaps,EndpointCheck check) {
    if(!body||!gaps||!check)throw std::runtime_error("pct_recovery_requires_geometry_and_native_check");
    body_geometry_=std::move(body);support_gaps_=std::move(gaps);endpoint_check_=std::move(check);
  }
  void setEnvironmentalField(std::shared_ptr<const reactive_stair::EnvironmentalField> field) { environment_=std::move(field);rebuildMap(); }
  double environmentalCost(const Eigen::Vector3d &p,double yaw) const { return environment_ ? environment_->cost(p,yaw) : 0.; }
  void clearRepairConstraints();
  void setFeedbackConstraints(const std::vector<RejectedPose> &poses);
  bool rejectedAt(const Eigen::Vector3d &position,double yaw,bool feedback_only=false) const;
  void addRepairConstraints(const std::vector<RejectedPose> &poses);
  Eigen::Vector3i poseToIndex(const Eigen::Vector3d &pose) const;
  std::vector<Eigen::Vector3d> plan(const Eigen::Vector3d &start, const Eigen::Vector3d &goal,bool smooth=true,
    double start_yaw=0.);
private:
  int layers_{0}, nx_{0}, ny_{0};
  double resolution_{0}, cx_{0}, cy_{0}, h0_{0}, dh_{0};
  bool quintic_;
  std::shared_ptr<const reactive_stair::EnvironmentalField> environment_;
  void rebuildMap();
  bool geometryClear(const Eigen::Vector3d &p,double yaw) const;
  std::vector<Eigen::Vector3d> graphPlan(const Eigen::Vector3d &start,const Eigen::Vector3d &goal,bool smooth);
  std::vector<Eigen::Vector3d> endpointAnchors(const Eigen::Vector3d &p,bool start,double yaw) const;
  bool connectorClear(const Eigen::Vector3d &a,const Eigen::Vector3d &b,double first_yaw,double last_yaw,
    bool native) const;
  bool recovery_map_{false};
  std::shared_ptr<const StaticBodyGeometry> body_geometry_;
  std::shared_ptr<const reactive_stair::SupportGapMask> support_gaps_;
  EndpointCheck endpoint_check_;
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

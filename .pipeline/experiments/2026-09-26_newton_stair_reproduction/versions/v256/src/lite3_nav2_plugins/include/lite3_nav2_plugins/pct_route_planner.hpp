#pragma once

#include <Eigen/Core>
#include <plan_env/environmental_field.h>
#include <plan_env/static_support.h>
#include <plan_env/static_solid.h>
#include <ele_planner/offline_ele_planner.h>
#include <cstdint>
#include <string>
#include <stdexcept>
#include <vector>

namespace lite3_nav2
{
class PCTOptimizationFailure : public std::runtime_error { public: using std::runtime_error::runtime_error; };
class PCTRoutePlanner
{
public:
  PCTRoutePlanner(const std::string &bundle, double reference_height,
                  bool quintic=true, double max_heading_rate=10.0);
  struct RejectedPose {Eigen::Vector3d position; double yaw; bool all_headings{false};};
  void setEnvironmentalField(std::shared_ptr<const reactive_stair::EnvironmentalField> field) { checkGeometry(support_,field);checkSolidGeometry(solid_,support_,field);environment_=std::move(field);rebuildMap(); }
  double environmentalCost(const Eigen::Vector3d &p,double yaw) const { return environment_ ? environment_->cost(p,yaw,support_?support_->gapMask():nullptr) : 0.; }
  void setStaticSupport(std::shared_ptr<const reactive_stair::StaticSupportField> support) { checkGeometry(support,environment_);checkSolidGeometry(solid_,support,environment_);support_=std::move(support);rebuildMap(); }
  void setStaticSolid(std::shared_ptr<const reactive_stair::StaticSolidField> solid) {
    checkSolidGeometry(solid,support_,environment_);
    solid_=std::move(solid);rebuildMap();
  }
  void clearRepairConstraints();
  void setFeedbackConstraints(const std::vector<RejectedPose> &poses);
  bool rejectedAt(const Eigen::Vector3d &position,double yaw,bool feedback_only=false) const;
  void addRepairConstraints(const std::vector<RejectedPose> &poses);
  Eigen::Vector3i poseToIndex(const Eigen::Vector3d &pose) const;
  std::vector<Eigen::Vector3d> plan(const Eigen::Vector3d &start, const Eigen::Vector3d &goal,bool smooth=true);
private:
  static void checkGeometry(const std::shared_ptr<const reactive_stair::StaticSupportField> &support,
      const std::shared_ptr<const reactive_stair::EnvironmentalField> &field) {
    if(support&&field&&(support->radius()!=field->radius()||support->offset()!=field->offset()||support->bodyClearance()!=field->bodyClearance()))
      throw std::runtime_error("Physical support and ENV225 shape mismatch");
  }
  static void checkSolidGeometry(const std::shared_ptr<const reactive_stair::StaticSolidField> &solid,
      const std::shared_ptr<const reactive_stair::StaticSupportField> &support,
      const std::shared_ptr<const reactive_stair::EnvironmentalField> &field) {
    if(solid&&((field&&(solid->radius()!=field->radius()||solid->offset()!=field->offset()||
        solid->up()!=field->up()||solid->down()!=field->down()||solid->bodyClearance()!=field->bodyClearance()))||
        (support&&(solid->radius()!=support->radius()||solid->offset()!=support->offset()||solid->bodyClearance()!=support->bodyClearance()))))
      throw std::runtime_error("Static solid and native envelope mismatch");
  }
  std::shared_ptr<const reactive_stair::StaticSupportField> support_;
  std::shared_ptr<const reactive_stair::StaticSolidField> solid_;
  void validateSolidPath(const std::vector<Eigen::Vector3d> &points,bool smooth) const;
  int layers_{0}, nx_{0}, ny_{0};
  double resolution_{0}, cx_{0}, cy_{0}, h0_{0}, dh_{0};
  bool quintic_;
  std::shared_ptr<const reactive_stair::EnvironmentalField> environment_;
  void rebuildMap();
  void projectSupportHeights(std::vector<Eigen::Vector3d> &points,const Eigen::VectorXd &layers,
      const Eigen::Vector3d &start,const Eigen::Vector3d &goal) const;
  Node continuousEndpoint(const Eigen::Vector3d &pose) const;
  Eigen::Vector3d nodePosition(const Node &node) const;
  bool transitionAllowed(const Node &from,const Node &to) const;
  double reference_height_{0};
  Eigen::MatrixXd planning_ground_,planning_ceiling_;
  Eigen::MatrixXd costs_,ground_,ceiling_,gateway_,grad_x_,grad_y_;
  std::vector<RejectedPose> rejected_,feedback_;
  std::vector<uint8_t> ground_valid_;
  OfflineElePlanner planner_;
};
}  // namespace lite3_nav2

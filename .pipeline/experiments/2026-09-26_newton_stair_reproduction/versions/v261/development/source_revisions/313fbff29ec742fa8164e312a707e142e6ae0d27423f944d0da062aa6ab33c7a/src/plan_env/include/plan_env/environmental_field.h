#pragma once
#include <Eigen/Core>
#include <memory>
#include <string>

namespace reactive_stair {
class SupportGapMask;
struct EnvironmentalAssessment {
  double edge_margin=0, solid_margin=0, terrain=0;
  double edge_penalty=0, solid_penalty=0;
  bool floor_known=false;
  Eigen::Vector4d gradient=Eigen::Vector4d::Zero(); // World XYZ, then yaw.
  double cost() const { return edge_penalty*edge_penalty+solid_penalty*solid_penalty+.25*terrain*terrain; }
};
// Shared static evidence and geometry; this class cannot authorize motion.
class EnvironmentalField {
 public:
  EnvironmentalField(const std::string &path,const std::string &fnv);
  ~EnvironmentalField();
  EnvironmentalAssessment assess(const Eigen::Vector3d &body,double yaw,const SupportGapMask *gap=nullptr) const;
  double cost(const Eigen::Vector3d &body,double yaw,const SupportGapMask *gap=nullptr) const { return assess(body,yaw,gap).cost(); }
  double costGradient(const Eigen::Vector3d &body,double yaw,Eigen::Vector4d &gradient,const SupportGapMask *gap=nullptr) const {
    const auto result=assess(body,yaw,gap);gradient=result.gradient;return result.cost();
  }
  double radius() const; double offset() const; double up() const; double down() const;
  double bodyClearance() const; double target() const;
  // Original source surface elevation, not an admission or contact verdict.
  bool surfaceHeight(double x,double y,double hint,double &height) const;
 private:
  struct Data;
  std::unique_ptr<Data> data_;
};
} // namespace reactive_stair

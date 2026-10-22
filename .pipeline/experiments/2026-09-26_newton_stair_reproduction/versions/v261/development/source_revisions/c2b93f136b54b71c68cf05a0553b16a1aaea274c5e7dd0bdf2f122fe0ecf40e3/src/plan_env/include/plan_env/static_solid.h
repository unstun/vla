#pragma once
#include <Eigen/Core>
#include <memory>
#include <string>
#include <vector>

namespace reactive_stair {
struct SolidAssessment {
  double margin=0.;
  Eigen::Vector4d gradient=Eigen::Vector4d::Zero(); // world X,Y,Z,yaw
  Eigen::Vector3d witness=Eigen::Vector3d::Zero();
  bool collision() const { return margin<=0.; }
};
// Exact v224 point/voxel finite-cylinder geometry, independent of the soft atlas.
// Same-floor associated terrain material is excluded; mixed/other-floor material
// remains solid. Immutable after construction and safe for concurrent readers.
class StaticSolidField {
 public:
  StaticSolidField(const std::string &path,const std::string &fnv);
  ~StaticSolidField();
  SolidAssessment assess(const Eigen::Vector3d &body,double yaw) const;
  bool collides(const Eigen::Vector3d &body,double yaw) const;
  // Proves the supplied sampled poses free; uncertain batches use exact queries.
  bool certifiesFreeSamples(const std::vector<Eigen::Vector4d> &poses) const;
  bool certifiesFreeRotation(const Eigen::Vector3d &body) const;
  bool impossibleAt(const Eigen::Vector3d &body) const;
  // Sufficient all-heading collision proof from the body's unavoidable core.
  bool coreCollision(const Eigen::Vector3d &body) const;
  double radius() const; double offset() const; double up() const; double down() const;
  double bodyClearance() const;
 private:
  SolidAssessment query(const Eigen::Vector3d &body,double yaw,bool hard_only) const;
  struct Data;
  std::unique_ptr<Data> data_;
};
} // namespace reactive_stair

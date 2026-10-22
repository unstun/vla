#pragma once
#include <Eigen/Core>
#include <memory>
#include <string>
#include <vector>
#include <array>
#include <cstdint>
#include <unordered_map>

namespace reactive_stair {
// Caller-owned per-request memo. No mutable cache is shared by field readers.
class StaticSolidQueryCache {
 public:
  void clear(){entries_.clear();owner_.reset();queries_=hits_=0;}
  size_t queries() const{return queries_;}
  size_t hits() const{return hits_;}
 private:
  friend class StaticSolidField;
  struct Key {int x,y;uint64_t z;bool operator==(const Key &b)const{return x==b.x&&y==b.y&&z==b.z;}};
  struct Hash {size_t operator()(const Key &k)const {size_t h=std::hash<uint64_t>{}(k.z);for(int v:{k.x,k.y})h^=std::hash<int>{}(v)+0x9e3779b9+(h<<6)+(h>>2);return h;}};
  struct Entry {double x=0.,y=0.,z=0.,ground=0.,margin=0.,height_slack=0.;const void *groups=nullptr;};
  struct Bucket {std::array<Entry,4> values;unsigned count=0,next=0;};
  std::unordered_map<Key,Bucket,Hash> entries_;
  std::shared_ptr<const void> owner_; // Keeps an old immutable field alive until reset.
  size_t queries_=0,hits_=0;
};
struct SolidAssessment {
  double margin=0.;
  Eigen::Vector4d gradient=Eigen::Vector4d::Zero(); // world X,Y,Z,yaw
  Eigen::Vector3d witness=Eigen::Vector3d::Zero();
  bool collision() const { return margin<=0.; }
};
// Immutable finite-cylinder hard field: legacy voxel records or pinned source surfaces.
// Source-surface margins are radial clearances conditioned on the vertical interval.
// Same-floor associated terrain material is excluded; mixed/other-floor material
// remains solid. Immutable after construction and safe for concurrent readers.
class StaticSolidField {
 public:
  StaticSolidField(const std::string &path,const std::string &fnv);
  ~StaticSolidField();
  SolidAssessment assess(const Eigen::Vector3d &body,double yaw) const;
  // Squared hinge over the extra 0.07 m beyond the unchanged hard radius.
  // Shared by GPMP and SCAN; source-wall gradient is XY/yaw at the
  // selected actual height, with zero Z component. Never an admission predicate.
  double repulsionCost(const Eigen::Vector3d &body,double yaw,Eigen::Vector4d *gradient=nullptr,const StaticSolidQueryCache *cache=nullptr) const;
  bool collides(const Eigen::Vector3d &body,double yaw) const;
  bool collides(const Eigen::Vector3d &body,double yaw,StaticSolidQueryCache &cache) const;
  bool certifiesFreeRotation(const Eigen::Vector3d &body) const;
  bool impossibleAt(const Eigen::Vector3d &body) const;
  // Sufficient all-heading collision proof from the body's unavoidable core.
  bool coreCollision(const Eigen::Vector3d &body) const;
  double radius() const; double offset() const; double up() const; double down() const;
  double bodyClearance() const;
 private:
  SolidAssessment query(const Eigen::Vector3d &body,double yaw,bool hard_only) const;
  struct Data;
  std::shared_ptr<Data> data_;
};
} // namespace reactive_stair

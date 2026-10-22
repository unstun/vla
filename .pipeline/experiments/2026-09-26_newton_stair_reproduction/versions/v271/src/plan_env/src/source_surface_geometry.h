#pragma once
#include <array>
#include <memory>
#include <string>
namespace reactive_stair { namespace source_surface {
using V=std::array<double,3>;
// Keep Boost geometry and source clipping out of the legacy arithmetic unit.
class Field {
 public:
  Field(const std::string &path,const std::string &metadata,const std::string &geometry_fnv,const std::string &metadata_fnv);
  ~Field();
  double assess(double x,double y,double ground,double yaw,V *witness=nullptr)const;
  // Exact positive clearance; a nonpositive value is an early collision witness.
  double circleMargin(double x,double y,double ground,double radius)const;
 private:
  struct Data;std::unique_ptr<Data> data_;
};
}}

#pragma once
#include <Eigen/Core>
#include <cmath>

namespace scan_planner {
// A warm start represents the physical robot only within the map's existing
// spatial sampling precision. Check both cylinder centers, including yaw.
inline bool measuredSeedAgrees(const Eigen::Vector3d &planned,double planned_yaw,
    const Eigen::Vector3d &measured,double measured_yaw,double resolution,double offset) {
  if(!planned.allFinite()||!measured.allFinite()||!std::isfinite(planned_yaw)||
      !std::isfinite(measured_yaw)||!std::isfinite(resolution)||resolution<=0||
      !std::isfinite(offset)||offset<0)return false;
  const Eigen::Vector3d a(std::cos(planned_yaw),std::sin(planned_yaw),0.);
  Eigen::Vector3d b(std::cos(measured_yaw),std::sin(measured_yaw),0.);
  if(a.dot(b)<0)b=-b; // The two-cylinder envelope is unchanged by a half turn.
  for(double sign:{-1.,1.})
    if((planned+sign*offset*a-measured-sign*offset*b).norm()>.5*resolution)return false;
  return true;
}
}

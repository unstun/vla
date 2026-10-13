#pragma once
#include <Eigen/Eigen>
#include <cmath>
#include <algorithm>
namespace reactive_stair {
// False is a geometric impossibility certificate, never a safety verdict.
// The box is a necessary condition for BOTH symmetric cylinder footprints.
template <class EndpointMayFit>
inline bool goalRegionMayFitWithEvidence(const Eigen::Vector3d &goal, double tolerance,
    const Eigen::Vector3d &lower, const Eigen::Vector3d &upper,
    const Eigen::Vector3d &center, double step,
    const Eigen::Vector3i &pool, const Eigen::Vector3i &center_index,
    const Eigen::Vector3i &start_index, const Eigen::Vector3i &end_index,
    bool search_plane, EndpointMayFit &&endpoint_may_fit) {
  if (!goal.allFinite() || !lower.allFinite() || !upper.allFinite() || !center.allFinite() ||
      !std::isfinite(tolerance) || tolerance <= 0 || !std::isfinite(step) || step <= 0 ||
      (pool.array() <= 0).any() || (pool.array() > 10000).any()) return true;
  if (goal.cwiseAbs().maxCoeff()>1e6 || center.cwiseAbs().maxCoeff()>1e6 ||
      lower.cwiseAbs().maxCoeff()>1e6 || upper.cwiseAbs().maxCoeff()>1e6 ||
      static_cast<long long>(pool.x())*pool.y()>1000000) return true;
  // Expand outward for floating-point operations in the original footprint test.
  const double slack=1e-6;
  const Eigen::Vector3d lo=lower-Eigen::Vector3d::Constant(slack);
  const Eigen::Vector3d hi=upper+Eigen::Vector3d::Constant(slack);
  if ((lo.array()>hi.array()).any()) return false;
  auto inside=[&](const Eigen::Vector3d &p) {
    return (p.array()>=lo.array()).all() && (p.array()<=hi.array()).all();
  };
  // Exact terminal connectors may return the exact goal from any reached node.
  if (inside(goal) && endpoint_may_fit(goal)) return true;
  const Eigen::Vector3d nearest=goal.cwiseMax(lo).cwiseMin(hi);
  if ((nearest-goal).norm()>tolerance+slack) return false;
  if (!search_plane) return true; // Uncertain 3D lattice: retain native search.
  auto point=[&](const Eigen::Vector3i &i) -> Eigen::Vector3d {
    return (i-center_index).cast<double>()*step+center;
  };
  const Eigen::Vector3d start=point(start_index), end=point(end_index);
  if (inside(start) && (start-goal).norm()<=tolerance+slack && endpoint_may_fit(start)) return true;
  const Eigen::Vector2d delta=end.head<2>()-start.head<2>();
  const double length2=delta.squaredNorm();
  // Enumerate a superset of every native neighbor endpoint; boundary indices
  // are included conservatively even though native neighbors exclude them.
  for(int x=0;x<pool.x();++x) for(int y=0;y<pool.y();++y) {
    Eigen::Vector3i i(x,y,start_index.z());
    const Eigen::Vector3d xy=point(i);
    if (std::abs(xy.x()-goal.x())>tolerance+slack ||
        std::abs(xy.y()-goal.y())>tolerance+slack ||
        xy.x()<lo.x() || xy.x()>hi.x() || xy.y()<lo.y() || xy.y()>hi.y()) continue;
    if (length2>=1e-8) {
      double ratio=(xy.head<2>()-start.head<2>()).dot(delta)/length2;
      ratio=std::max(0.0,std::min(1.0,ratio));
      const double z=start.z()+ratio*(end.z()-start.z());
      const double z_index=(z-center.z())*(1.0/step)+0.5;
      if (!std::isfinite(z_index) || std::abs(z_index)>1e8) return true;
      i.z()=static_cast<int>(z_index)+center_index.z();
    }
    if(i.z()<0 || i.z()>=pool.z()) continue;
    const Eigen::Vector3d p=point(i);
    if(inside(p) && (p-goal).norm()<=tolerance+slack && endpoint_may_fit(p)) return true;
  }
  return false;
}
// Original bounds-only contract is the all-possible special case.
inline bool goalRegionMayFit(const Eigen::Vector3d &goal, double tolerance,
    const Eigen::Vector3d &lower, const Eigen::Vector3d &upper,
    const Eigen::Vector3d &center, double step,
    const Eigen::Vector3i &pool, const Eigen::Vector3i &center_index,
    const Eigen::Vector3i &start_index, const Eigen::Vector3i &end_index,
    bool search_plane) {
  return goalRegionMayFitWithEvidence(goal, tolerance, lower, upper, center, step,
      pool, center_index, start_index, end_index, search_plane,
      [](const Eigen::Vector3d &) { return true; });
}
} // namespace reactive_stair

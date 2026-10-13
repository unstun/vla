#pragma once
#include <bspline_opt/full_trajectory_collision.h>
#include <bspline_opt/rebound_constraint_utils.h>
#include <array>

namespace reactive_stair {
// A bounded optimization hint for a sampled collision. It never certifies a
// curve. The ordinary full-curve, dynamics and publication checks remain due.
template <typename Controls, typename Heading, typename Occupied>
size_t appendSampledCurveRebound(Controls& controls,
    scan_planner::UniformBspline& curve, double time, double interval,
    double resolution, double lookahead, Heading heading, Occupied occupied) {
  const int count=controls.points.cols();
  if (count<7 || !std::isfinite(time) || time<0 ||
      !std::isfinite(interval) || interval<=0 ||
      !std::isfinite(resolution) || resolution<=0) return 0;
  const double duration=curve.getTimeSum();
  if (time>duration) return 0;
  const Eigen::Vector3d position=curve.evaluateDeBoorT(time);
  auto velocity=curve.getDerivative();
  const Eigen::Vector3d v=velocity.evaluateDeBoorT(time);
  const Eigen::Vector3d ahead=curve.evaluateDeBoorT(std::min(time+lookahead,duration));
  const double yaw=heading(position,ahead,v);
  if (!position.allFinite() || !std::isfinite(yaw) || !occupied(position,yaw)) return 0;

  // Same-height finite neighborhood; no scene coordinates or new map values.
  // Prefer a lateral displacement when equally near free witnesses exist.
  Eigen::Vector3d target=position;
  bool found=false;
  for(int ring=1;ring<=8 && !found;++ring) {
    double best=std::numeric_limits<double>::infinity();
    for(int sector=0;sector<16;++sector) {
      const double angle=sector*(2.0*std::acos(-1.0)/16.0);
      const Eigen::Vector3d shift(ring*resolution*std::cos(angle),
                                  ring*resolution*std::sin(angle),0);
      const Eigen::Vector3d witness=position+shift;
      if(occupied(witness,yaw)) continue;
      const double cost=std::abs(shift.x()*std::cos(yaw)+shift.y()*std::sin(yaw));
      if(cost<best) {best=cost;target=witness;found=true;}
    }
  }
  if(!found) return 0;
  const Eigen::Vector3d shift=target-position;
  const Eigen::Vector3d direction=shift.normalized();

  const double coordinate=time/interval;
  const int span=std::min(count-4,static_cast<int>(std::floor(coordinate)));
  const double u=std::clamp(coordinate-span,0.0,1.0);
  const std::array<double,4> weight={
      std::pow(1-u,3)/6.0,(3*u*u*u-6*u*u+4)/6.0,
      (-3*u*u*u+3*u*u+3*u+1)/6.0,u*u*u/6.0};
  double denominator=0;
  for(int j=0;j<4;++j) {
    const int index=span+j;
    if(index>=3 && index<count-3) denominator+=weight[j]*weight[j];
  }
  if(!std::isfinite(denominator) || denominator<1e-8) return 0;
  size_t added=0;
  for(int j=0;j<4;++j) {
    const int index=span+j;
    if(index<3 || index>=count-3 || weight[j]<1e-8) continue;
    // Minimum-norm control displacement for the sampled cubic point. Its
    // directional target uses the existing clearance/cost convention.
    const Eigen::Vector3d base=controls.points.col(index)+
        (weight[j]/denominator)*shift;
    if(appendReboundConstraint(controls,index,base,direction)) ++added;
  }
  return added;
}
}  // namespace reactive_stair

#include <bspline_opt/bspline_optimizer.h>
#include <bspline_opt/sampled_curve_rebound.h>
#include <stdexcept>
#include <iostream>
int main(){
  scan_planner::ControlPoints c; c.resize(7); c.clearance=.2;
  for(int i=0;i<7;++i)c.points.col(i)=Eigen::Vector3d(.2*i,0,0);
  scan_planner::UniformBspline curve(c.points,3,1.0);
  const auto heading=[](auto,auto,auto){return 0.;};
  const auto blocked=[](const Eigen::Vector3d&p,double){return std::abs(p.y())<.15;};
  const auto n=reactive_stair::appendSampledCurveRebound(c,curve,1.5,1.,.1,.8,heading,blocked);
  if(!n)throw std::runtime_error("No repair hint for movable middle point");
  for(int i=0;i<7;++i)if(i!=3 && !c.direction[i].empty())throw std::runtime_error("Boundary control changed");
  if((curve.getControlPoint()-c.points).norm()!=0)throw std::runtime_error("Hint changed curve without reoptimization");
  const auto size=c.direction[3].size();
  const auto never=[](auto,double){return false;};const auto always=[](auto,double){return true;};
  if(reactive_stair::appendSampledCurveRebound(c,curve,1.5,1.,.1,.8,heading,never))throw std::runtime_error("Clear curve got repair");
  if(reactive_stair::appendSampledCurveRebound(c,curve,1.5,1.,.1,.8,heading,always))throw std::runtime_error("No free witness invented");
  if(reactive_stair::appendSampledCurveRebound(c,curve,0.,1.,.1,.8,heading,blocked))throw std::runtime_error("Fixed boundary changed");
  if(reactive_stair::appendSampledCurveRebound(c,curve,-1.,1.,.1,.8,heading,blocked))throw std::runtime_error("Invalid time accepted");
  if(reactive_stair::appendSampledCurveRebound(c,curve,1.,0.,.1,.8,heading,blocked))throw std::runtime_error("Invalid interval accepted");
  if(c.direction[3].size()!=size)throw std::runtime_error("Rejected hint mutated constraints");
  std::cout<<"SAMPLED_REBOUND_HINT_CHECKS 7 passed"<<std::endl;
}

#pragma once
#include <Eigen/Dense>
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace scan_planner {
// Cubic B-spline samples, including tangent/lookahead heading. Gradients flow
// through the same pose query into every contributing control point.
template<class Cost,class Heading>
double environmentalCurveCost(const Eigen::MatrixXd &q,double interval,double lookahead,
    Cost score,Heading heading,Eigen::MatrixXd &gradient,
    double measured_yaw=std::numeric_limits<double>::quiet_NaN(),
    double spatial_step=.025,int minimum_samples=10) {
  gradient=Eigen::MatrixXd::Zero(3,q.cols());
  if(q.rows()!=3 || !q.allFinite() || !std::isfinite(interval) || interval<=0 ||
      !std::isfinite(lookahead) || lookahead<0 || !std::isfinite(spatial_step) || spatial_step<=0 || minimum_samples<1)
    throw std::invalid_argument("Invalid environmental curve geometry");
  if(q.cols()<4)return 0.;
  const double duration=(q.cols()-3)*interval;
  if(!std::isfinite(duration))throw std::invalid_argument("Nonfinite environmental curve duration");
  struct Basis {int index;Eigen::Vector4d value,derivative;};
  const auto basis=[&](double time) {
    const int i=std::min(int(time/interval),int(q.cols())-4);
    const double u=(time-i*interval)/interval,u2=u*u,u3=u2*u;
    Basis b;b.index=i;
    b.value<<std::pow(1-u,3)/6.,(3*u3-6*u2+4)/6.,(-3*u3+3*u2+3*u+1)/6.,u3/6.;
    b.derivative<<-.5*(1-u)*(1-u),(1.5*u2-2*u),(-1.5*u2+u+.5),.5*u2;
    b.derivative/=interval;return b;
  };
  double total=0.;
  for(int span=0;span<q.cols()-3;++span) {
    double length=0.;for(int k=0;k<3;++k)length+=(q.col(span+k+1)-q.col(span+k)).norm();
    // Default quadrature retains ten samples; costly source-wall soft terms
    // may use caller-selected spatial quadrature without altering hard checks.
    const auto left=basis(span*interval),right=basis((span+1)*interval);
    const Eigen::Vector3d lv=q.middleCols(left.index,4)*left.derivative,rv=q.middleCols(right.index,4)*right.derivative;
    if(!lv.allFinite() || !rv.allFinite() || !std::isfinite(length) ||
        length/spatial_step>std::numeric_limits<int>::max()-1)
      throw std::invalid_argument("Nonfinite environmental sample geometry");
    const double turn=std::abs(std::remainder(std::atan2(rv.y(),rv.x())-std::atan2(lv.y(),lv.x()),2*M_PI));
    const int samples=std::max({minimum_samples,int(std::ceil(length/spatial_step)),int(std::ceil(turn/(2*spatial_step)))});
    const double weight=interval/samples;
    for(int sample=0;sample<samples;++sample) {
      const double t=(span+(sample+.5)/samples)*interval;
      const auto b=basis(t),a=basis(std::min(duration,t+lookahead));
      const Eigen::Vector3d p=q.middleCols(b.index,4)*b.value;
      const Eigen::Vector3d v=q.middleCols(b.index,4)*b.derivative;
      const Eigen::Vector3d ahead=q.middleCols(a.index,4)*a.value;
      if(!p.allFinite() || !v.allFinite() || !ahead.allFinite())
        throw std::invalid_argument("Nonfinite environmental sample pose");
      double yaw=heading(p,ahead,v);
      const Eigen::Vector3d delta=ahead-p;
      enum Direction {Lookahead,Velocity,Neighbor,Measured};
      Direction selected=delta.head<2>().squaredNorm()>=1e-4 ? Lookahead :
        (v.head<2>().squaredNorm()>=1e-4 ? Velocity : Measured);
      int neighbor=-1;
      Eigen::Vector3d direction=selected==Lookahead ? delta : v;
      if(!std::isfinite(yaw)) {
        // Soft preference alone may use smaller geometric tangents. Native
        // collision headings keep their original freshness and 1e-4 rule.
        if(delta.head<2>().squaredNorm()>1e-12){direction=delta;selected=Lookahead;}
        else if(v.head<2>().squaredNorm()>1e-12){direction=v;selected=Velocity;}
        else {
          selected=Measured;
          for(int distance=0;distance<q.cols()-1 && neighbor<0;++distance)
            for(int index:{b.index-distance,b.index+distance}) {
              if(index<0 || index>=q.cols()-1)continue;
              const Eigen::Vector3d candidate=q.col(index+1)-q.col(index);
              if(candidate.head<2>().squaredNorm()>1e-12) {
                neighbor=index;direction=candidate;selected=Neighbor;break;
              }
            }
        }
        yaw=selected==Measured ? measured_yaw : std::atan2(direction.y(),direction.x());
      }
      if(!std::isfinite(yaw))throw std::invalid_argument("No finite environmental soft heading");
      Eigen::Vector4d pose=Eigen::Vector4d::Zero();
      const double value=score(p,yaw,pose);total+=weight*value;
      if(!std::isfinite(value) || !pose.allFinite())
        throw std::runtime_error("Nonfinite environmental score or gradient");
      if(value==0.)continue;
      Eigen::Vector3d dp=pose.head<3>(),da=Eigen::Vector3d::Zero(),dv=da;
      // Exact branches of GridMap::collisionTrajectoryYaw / motionHeading.
      const double norm2=direction.head<2>().squaredNorm();
      if(selected!=Measured && norm2>1e-12) {
        const Eigen::Vector3d angle_gradient=pose(3)/norm2*Eigen::Vector3d(-direction.y(),direction.x(),0.);
        if(selected==Velocity)dv=angle_gradient;
        else if(selected==Lookahead){dp-=angle_gradient;da=angle_gradient;}
        else {
          gradient.col(neighbor)-=weight*angle_gradient;
          gradient.col(neighbor+1)+=weight*angle_gradient;
        }
      }
      for(int k=0;k<4;++k) {
        gradient.col(b.index+k)+=weight*(b.value(k)*dp+b.derivative(k)*dv);
        gradient.col(a.index+k)+=weight*a.value(k)*da;
      }
    }
  }
  return total;
}
} // namespace scan_planner

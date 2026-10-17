#pragma once
#include <Eigen/Dense>
#include <algorithm>
#include <cmath>

namespace scan_planner {
// Cubic B-spline samples, including tangent/lookahead heading. Gradients flow
// through the same pose query into every contributing control point.
template<class Cost,class Heading>
double environmentalCurveCost(const Eigen::MatrixXd &q,double interval,double lookahead,
    Cost score,Heading heading,Eigen::MatrixXd &gradient) {
  gradient=Eigen::MatrixXd::Zero(3,q.cols());
  if(q.cols()<4||interval<=0)return 0.;
  const double duration=(q.cols()-3)*interval;
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
    // At least ten samples per span; more for long spans or sharp rotation.
    const auto left=basis(span*interval),right=basis((span+1)*interval);
    const Eigen::Vector3d lv=q.middleCols(left.index,4)*left.derivative,rv=q.middleCols(right.index,4)*right.derivative;
    const double turn=std::abs(std::remainder(std::atan2(rv.y(),rv.x())-std::atan2(lv.y(),lv.x()),2*M_PI));
    const int samples=std::max({10,int(std::ceil(length/.025)),int(std::ceil(turn/.05))});
    const double weight=interval/samples;
    for(int sample=0;sample<samples;++sample) {
      const double t=(span+(sample+.5)/samples)*interval;
      const auto b=basis(t),a=basis(std::min(duration,t+lookahead));
      const Eigen::Vector3d p=q.middleCols(b.index,4)*b.value;
      const Eigen::Vector3d v=q.middleCols(b.index,4)*b.derivative;
      const Eigen::Vector3d ahead=q.middleCols(a.index,4)*a.value;
      const double yaw=heading(p,ahead,v);Eigen::Vector4d pose;
      const double value=score(p,yaw,pose);total+=weight*value;
      if(value==0.)continue;
      Eigen::Vector3d dp=pose.head<3>(),da=Eigen::Vector3d::Zero(),dv=da;
      // Exact branches of GridMap::collisionTrajectoryYaw / motionHeading.
      const Eigen::Vector3d delta=ahead-p;const bool use_velocity=delta.head<2>().squaredNorm()<1e-4;
      const Eigen::Vector3d direction=use_velocity?v:delta;
      const double norm2=direction.head<2>().squaredNorm();
      if(norm2>=1e-4) {
        const Eigen::Vector3d angle_gradient=pose(3)/norm2*Eigen::Vector3d(-direction.y(),direction.x(),0.);
        if(use_velocity)dv=angle_gradient;
        else {dp-=angle_gradient;da=angle_gradient;}
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

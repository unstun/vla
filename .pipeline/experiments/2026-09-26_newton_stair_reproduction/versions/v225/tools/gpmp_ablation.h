#pragma once
#include <cstdlib>

inline bool diagnosticFrozenHeading() {
  const char *v=std::getenv("GPMP_DIAG_FROZEN_HEADING");return v&&std::string(v)=="1";
}
inline gtsam::Vector6 diagnosticState(const PathPoint &p) {
  const double v=std::max(p.ref_v,1.);gtsam::Vector6 x;
  x<<p.x,std::cos(p.heading)*v,0.,p.y,std::sin(p.heading)*v,0.;return x;
}
inline double diagnosticYaw(const gtsam::Vector6 &x) {return std::atan2(x(1),x(4));}
inline double diagnosticResidual(const DenseElevationMap &map,const gtsam::Vector6 &x,
    double height,double yaw,Eigen::Matrix<double,1,6> &gradient) {
  gradient.setZero();if(!map.environmental_cost_)return 0.;Eigen::Vector4d g;
  const double residual=std::sqrt(2.*map.environmental_cost_(x(0),x(3),height,yaw,&g));
  if(residual>0.){gradient(0)=g(0)/residual;gradient(3)=g(1)/residual;}return residual;
}
class DiagnosticNodeFactor:public GPObstacleFactor {
  double yaw_;
public:
  DiagnosticNodeFactor(const GPObstacleFactor &base,double yaw):GPObstacleFactor(base),yaw_(yaw){}
  gtsam::Vector evaluateError(const gtsam::Vector6 &x,boost::optional<gtsam::Matrix&> H=boost::none) const override {
    auto result=GPObstacleFactor::evaluateError(x,H);
    if(diagnosticFrozenHeading()) {
      Eigen::Matrix<double,1,6> g;result(1)=diagnosticResidual(*map_,x,height_hint_,yaw_,g);if(H)H->row(1)=g;
    }
    return result;
  }
};
class DiagnosticInterFactor:public GPInterpolateObstacleFactor {
  double yaw_;
public:
  DiagnosticInterFactor(const GPInterpolateObstacleFactor &base,const PathPoint &p,const PathPoint &q,
      double qc,double dt,double tau):GPInterpolateObstacleFactor(base),
      yaw_(diagnosticYaw(GPInterpolator::Interpolate(diagnosticState(p),diagnosticState(q),qc,dt,tau))){}
  gtsam::Vector evaluateError(const gtsam::Vector6 &x,const gtsam::Vector6 &y,
      boost::optional<gtsam::Matrix&> H1=boost::none,boost::optional<gtsam::Matrix&> H2=boost::none) const override {
    auto result=GPInterpolateObstacleFactor::evaluateError(x,y,H1,H2);
    if(diagnosticFrozenHeading()) {
      gtsam::Matrix66 J1,J2;const auto state=gp_interpolator_.Interpolate(x,y,&J1,&J2);
      Eigen::Matrix<double,1,6> g;result(1)=diagnosticResidual(*map_,state,height_hint_,yaw_,g);
      if(H1)H1->row(1)=g*J1;if(H2)H2->row(1)=g*J2;
    }
    return result;
  }
};

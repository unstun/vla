#pragma once
#include <Eigen/Core>
#include <algorithm>
#include <cmath>
#include <functional>
#include <stdexcept>
#include <vector>
namespace lite3_nav2 {
struct PoseSample {Eigen::Vector3d position;double yaw;};
inline std::vector<PoseSample> samplePoseLine(const PoseSample &a,const PoseSample &b) {
  if(!a.position.allFinite()||!b.position.allFinite()||!std::isfinite(a.yaw)||!std::isfinite(b.yaw))
    throw std::runtime_error("pct_nonfinite_pose_connection");
  const double angle=std::remainder(b.yaw-a.yaw,2*M_PI);
  const double needed=std::max((b.position-a.position).norm()/.025,std::abs(angle)/.05);
  if(needed>10000)throw std::runtime_error("pct_pose_connection_budget");
  const int n=std::max(1,int(std::ceil(needed)));std::vector<PoseSample> out;
  for(int i=0;i<=n;++i){const double u=double(i)/n;out.push_back({a.position+u*(b.position-a.position),a.yaw+u*angle});}
  return out;
}
// A geometric connection to the actual endpoint. It changes neither endpoint
// nor the ordinary lattice neighbourhood. Its tangent agrees with each pose.
inline std::vector<PoseSample> samplePoseHermite(const PoseSample &a,const PoseSample &b) {
  if(!a.position.allFinite()||!b.position.allFinite()||!std::isfinite(a.yaw)||!std::isfinite(b.yaw))
    throw std::runtime_error("pct_nonfinite_pose_connection");
  const Eigen::Vector3d delta=b.position-a.position;
  const double length=delta.head<2>().norm();
  if(length<1e-10)return samplePoseLine(a,b);
  const Eigen::Vector2d u(length*std::cos(a.yaw),length*std::sin(a.yaw)),v(length*std::cos(b.yaw),length*std::sin(b.yaw));
  // A quadratic Bezier derivative lies in the convex hull of these three
  // derivative controls; this bounds arc length per parameter interval.
  const double speed_bound=std::max(length,(3.*delta.head<2>()-u-v).norm());
  const double needed=speed_bound/.025;
  if(!std::isfinite(needed)||needed>10000)throw std::runtime_error("pct_pose_connection_budget");
  const int n=std::max(8,int(std::ceil(needed)));
  std::vector<PoseSample> out;PoseSample previous=a;
  for(int i=0;i<=n;++i) {
    const double t=double(i)/n,t2=t*t,t3=t2*t;
    PoseSample p;p.position=a.position+t*delta;
    p.position.head<2>()=(2*t3-3*t2+1)*a.position.head<2>()+(t3-2*t2+t)*u+(-2*t3+3*t2)*b.position.head<2>()+(t3-t2)*v;
    const Eigen::Vector2d tangent=(6*t2-6*t)*a.position.head<2>()+(3*t2-4*t+1)*u+(-6*t2+6*t)*b.position.head<2>()+(3*t2-2*t)*v;
    p.yaw=tangent.norm()>1e-10?std::atan2(tangent.y(),tangent.x()):a.yaw+t*std::remainder(b.yaw-a.yaw,2*M_PI);
    if(i==0){p=a;out.push_back(a);}else {
      auto part=samplePoseLine(previous,p);out.insert(out.end(),part.begin()+1,part.end());
    }
    previous=p;
  }
  out.front()=a;out.back()=b;return out;
}
} // namespace lite3_nav2

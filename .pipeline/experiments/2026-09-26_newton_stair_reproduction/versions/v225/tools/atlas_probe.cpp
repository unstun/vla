#include "raw_reference.h"
#include <plan_env/environmental_field.h>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <vector>

int main() {
  reactive_stair::EnvironmentalField field(std::getenv("ENVIRONMENT_INPUT"),std::getenv("ENVIRONMENT_FNV"));
  void *raw=makePointField(std::getenv("RAW_FIELD"),std::getenv("RAW_FNV"),false);
  struct Pose{int group;Eigen::Vector3d p;double yaw;};std::vector<Pose> poses;
  std::ifstream input(std::getenv("ORACLE_POSES"));Pose q;
  while(input>>q.group>>q.p.x()>>q.p.y()>>q.p.z()>>q.yaw)poses.push_back(q);
  std::ofstream csv(std::getenv("ORACLE_OUTPUT"));csv<<std::setprecision(17)<<"group,x,y,z,yaw,floor_known,switch_band,old_edge,new_edge,old_solid,new_solid,old_cost,new_cost,gradient_error,smooth_axes,nonsmooth_axes\n";
  for(const auto &pose:poses) {
    const auto a=field.assess(pose.p,pose.yaw);double old[4];pointAssessment(raw,pose.p.x(),pose.p.y(),pose.p.z(),pose.yaw,old);
    double gradient_error=0.;int smooth=0,nonsmooth=0;constexpr double epsilon=1e-6;
    for(int axis=0;axis<4;++axis) {
      auto plus=pose.p,minus=pose.p;double yp=pose.yaw,ym=pose.yaw;
      if(axis<3){plus(axis)+=epsilon;minus(axis)-=epsilon;}else{yp+=epsilon;ym-=epsilon;}
      const double cp=field.cost(plus,yp),cm=field.cost(minus,ym);
      const double left=(a.cost()-cm)/epsilon,right=(cp-a.cost())/epsilon;
      if(std::abs(left-right)>1e-3*(1+std::abs(left)+std::abs(right))){++nonsmooth;continue;}
      ++smooth;gradient_error=std::max(gradient_error,std::abs(a.gradient(axis)-.5*(left+right))/(1+std::abs(.5*(left+right))));
    }
    const bool band=pointSwitchBand(raw,pose.p.x(),pose.p.y(),pose.p.z(),pose.yaw,.05,.05,std::stod(std::getenv("ATLAS_AZ")));
    csv<<pose.group<<','<<pose.p.x()<<','<<pose.p.y()<<','<<pose.p.z()<<','<<pose.yaw<<','<<a.floor_known<<','<<band<<','<<old[0]<<','<<a.edge_margin<<','<<std::clamp(old[1],-field.target(),field.target())<<','<<a.solid_margin<<','<<old[3]<<','<<a.cost()<<','<<gradient_error<<','<<smooth<<','<<nonsmooth<<'\n';
  }
  freePointField(raw);double checksum=0.;const auto began=std::chrono::steady_clock::now();
  for(int repetition=0;repetition<20;++repetition)for(const auto &pose:poses)checksum+=field.cost(pose.p,pose.yaw);
  std::cout<<std::setprecision(17)<<"ATLAS_ORACLE poses="<<poses.size()<<" query_us="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count()*1e6/(20*poses.size())<<" checksum="<<checksum<<'\n';
}

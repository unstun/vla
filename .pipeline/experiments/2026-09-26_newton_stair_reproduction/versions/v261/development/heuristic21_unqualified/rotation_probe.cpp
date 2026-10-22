#include <plan_env/static_support.h>
#include <plan_env/static_solid.h>
#include <plan_env/environmental_field.h>
#include <lite3_nav2_plugins/pose_connection.hpp>
#include <iostream>
#include <random>
#include <iomanip>
int main(){
 reactive_stair::StaticSupportField support("/work/fixtures/building/native.support","15212154834549674106");
 reactive_stair::StaticSolidField solid("/work/fixtures/building/static_solids.env","17629216882668158307");
 std::mt19937 random(261);std::uniform_real_distribution<double> jitter(-.049,.049),height(-.04,.04);
 reactive_stair::EnvironmentalField env("/work/fixtures/building/environment225.env","10040917858432847476");
 size_t bound_edges=0,bound_samples=0,bound_bad=0;double bound_max_error=0.;
 size_t samples=0,certified=0,queries=0,bad=0,core=0,core_queries=0,core_bad=0,support_core=0,support_core_bad=0;
 for(const auto &entry:support.raw_.cells){
  if(random()%7)continue;
  for(const auto &surface:entry.second){
   const double x=support.raw_.origin_x_m+(entry.first.x+.5)*support.raw_.resolution_m+jitter(random);
   const double y=support.raw_.origin_y_m+(entry.first.y+.5)*support.raw_.resolution_m+jitter(random);
   const Eigen::Vector3d p(x,y,surface.elevation_m+.3+height(random));++samples;
   if(samples<=2048){
    const double yaw=(random()%62832)*.0001;
    const Eigen::Vector3d q=p+Eigen::Vector3d(jitter(random)*8,jitter(random)*8,height(random)*4);
    const double lower=env.connectionCostLowerBound(p,q);
    const auto curve=lite3_nav2::samplePoseHermite({p,yaw},{q,yaw+jitter(random)*24});++bound_edges;
    for(const auto &pose:curve){++bound_samples;const double actual=env.cost(pose.position,pose.yaw,support.gapMask());
     bound_max_error=std::max(bound_max_error,lower-actual);if(lower>actual+1e-12)++bound_bad;
    }
   }
   if(solid.coreCollision(p)){++core;
    for(int i=0;i<256;++i){++core_queries;if(!solid.collides(p,i*M_PI/128.))++core_bad;}
   }
   if(!support.coreSupported(p.x(),p.y(),p.z())){++support_core;
    for(int i=0;i<256;++i)if(support.assess(p.x(),p.y(),p.z(),i*M_PI/128.)==reactive_stair::Verdict::Free)++support_core_bad;
   }
   if(support.certifiesFreeRotation(p.x(),p.y(),p.z())&&solid.certifiesFreeRotation(p)){
    ++certified;
    for(int i=0;i<256;++i){const double yaw=i*M_PI/128.;++queries;
     if(support.assess(p.x(),p.y(),p.z(),yaw)!=reactive_stair::Verdict::Free||solid.collides(p,yaw)){++bad;std::cerr<<std::setprecision(17)<<"BAD "<<p.transpose()<<" yaw="<<yaw<<'\n';}
    }
   }
   if(samples>=4096)break;
  }
  if(samples>=4096)break;
 }
 std::cout<<"samples="<<samples<<"\ncertified="<<certified<<"\nyaw_queries="<<queries<<"\nfalse_free_certificates="<<bad<<"\ncore_blocked="<<core<<"\ncore_yaw_queries="<<core_queries<<"\nfalse_core_collision="<<core_bad<<"\nsupport_core_blocked="<<support_core<<"\nfalse_support_core_collision="<<support_core_bad<<std::endl;
 std::cout<<"cost_bound_edges="<<bound_edges<<"\ncost_bound_samples="<<bound_samples<<"\ninvalid_cost_lower_bounds="<<bound_bad<<"\nmax_cost_lower_bound_error="<<bound_max_error<<std::endl;
 return bound_bad||bad||core_bad||support_core_bad||certified==0||core==0||support_core==0?1:0;
}

#include <plan_env/static_support.h>
#include <plan_env/static_solid.h>
#include <iostream>
#include <random>
#include <iomanip>
int main(){
 reactive_stair::StaticSupportField support("/work/fixtures/building/native.support","15212154834549674106");
 reactive_stair::StaticSolidField solid("/work/fixtures/building/static_solids.env","17629216882668158307");
 std::mt19937 random(261);std::uniform_real_distribution<double> jitter(-.049,.049),height(-.04,.04);
 size_t samples=0,certified=0,queries=0,bad=0,core=0,core_queries=0,core_bad=0,support_core=0,support_core_bad=0;
 for(const auto &entry:support.raw_.cells){
  if(random()%7)continue;
  for(const auto &surface:entry.second){
   const double x=support.raw_.origin_x_m+(entry.first.x+.5)*support.raw_.resolution_m+jitter(random);
   const double y=support.raw_.origin_y_m+(entry.first.y+.5)*support.raw_.resolution_m+jitter(random);
   const Eigen::Vector3d p(x,y,surface.elevation_m+.3+height(random));++samples;
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
 return bad||core_bad||support_core_bad||certified==0||core==0||support_core==0?1:0;
}

#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <fstream>
#include <iostream>
#include <iomanip>
int main(int argc,char **argv){
 for(int j=1;j<argc;++j){
  lite3_nav2::PCTRoutePlanner p("/work/fixtures/building/native_original.pct",.3);
  p.setEnvironmentalField(std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476"));
  p.setStaticSupport(std::make_shared<reactive_stair::StaticSupportField>("/work/fixtures/building/native.support","15212154834549674106"));
  p.setStaticSolid(std::make_shared<reactive_stair::StaticSolidField>("/work/fixtures/building/static_solids.env","17629216882668158307"));
  Eigen::Vector3d a,b;double sy,gy;std::ifstream f(argv[j]);f>>a.x()>>a.y()>>a.z()>>b.x()>>b.y()>>b.z()>>sy>>gy;
  try{p.plan(a,b,false,sy,gy);}catch(const std::exception&e){std::cout<<e.what()<<std::endl;}
  int k=0;
  for(const auto &path:{p.planner_.get_path_finder().GetPathPoints(),p.planner_.get_prepared_path()}){
   std::ofstream out("/evaluation/endpoint_"+std::to_string(j)+"_"+std::to_string(k++)+".csv");out<<std::setprecision(17)<<"x,y,z,yaw,margin\n";
   for(const auto &pt:path){Eigen::Vector3d xyz((pt.y-p.nx_/2)*p.resolution_+p.cx_,(pt.x-p.ny_/2)*p.resolution_+p.cy_,pt.height+.3);const double yaw=M_PI/2-pt.heading;
    out<<xyz.x()<<','<<xyz.y()<<','<<xyz.z()<<','<<yaw<<','<<p.solid_->assess(xyz,yaw).margin<<'\n';}
  }
 }
}

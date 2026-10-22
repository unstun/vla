// Behavioral regressions on unchanged recorded poses, through installed PCT.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <chrono>
#include <stdexcept>
int main(){
 size_t total=0,passed=0;
 for(bool quintic:{true,false})for(const std::string cid:{"CU08","CU13","CE04"}){
  lite3_nav2::PCTRoutePlanner p("/work/fixtures/building/native_original.pct",.3,quintic);
  p.setEnvironmentalField(std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476"));
  p.setStaticSupport(std::make_shared<reactive_stair::StaticSupportField>("/work/fixtures/building/native.support","15212154834549674106"));
  p.setStaticSolid(std::make_shared<reactive_stair::StaticSolidField>(std::getenv("RAW_FIELD"),std::getenv("RAW_FNV")));
  Eigen::Vector3d start,goal;double sy,gy;std::ifstream input("/task/mesh_benchmark_v262/cases/"+cid+"/endpoints.txt");
  input>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z()>>sy>>gy;if(!input)throw std::runtime_error("Missing fixed endpoint fixture");
  ++total;bool ok=false;std::string error;const auto began=std::chrono::steady_clock::now();
  try{
   const auto route=p.plan(start,goal,true,sy,gy);
   ok=route.size()>1&&(route.front()-start).cwiseAbs().maxCoeff()<1e-9&&(route.back()-goal).cwiseAbs().maxCoeff()<1e-9&&std::abs(std::remainder(p.plannedYaws().back()-gy,2*M_PI))<1e-9;
   if(!ok)error="Endpoint identity mismatch";
  }catch(const std::exception &e){error=e.what();}
  const Eigen::MatrixXd states=quintic?p.planner_.get_trajectory_optimizer_wnoj().GetResultMatrix():p.planner_.get_trajectory_optimizer().GetResultMatrix();
  if(states.rows())std::cout<<std::setprecision(17)<<"BOUNDARY first_state="<<states.row(0)<<" last_state="<<states.row(states.rows()-1)<<'\n';
  passed+=ok;
  std::cout<<"ENDPOINT_CASE id="<<cid<<" order="<<(quintic?5:3)<<" first_pass="<<ok<<" seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count()<<" error="<<error<<std::endl;
 }
 std::cout<<"endpoint_cases="<<total<<"\nendpoint_first_passed="<<passed<<std::endl;
 return passed==total?0:1;
}

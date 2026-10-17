#include "raw_reference.h"
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>

int main() {
  auto field=std::make_shared<reactive_stair::EnvironmentalField>(std::getenv("ENVIRONMENT_INPUT"),std::getenv("ENVIRONMENT_FNV"));
  lite3_nav2::PCTRoutePlanner pct(std::getenv("PCT_INPUT"),.35);pct.setEnvironmentalField(field);
  void *reference=makePointField(std::getenv("RAW_FIELD"),std::getenv("RAW_FNV"),false);
  // Freeze the original v224 scored search seed once, then bypass A* in all
  // ablations. This changes neither seed, state units, N, dt nor endpoint PVA.
  pct.planner_.path_finder_.SetEnvironmentalCost([&](const Node &a,const Node &b) {
    const auto world=[&](const Node &n){return Eigen::Vector3d((n.idx[1]-pct.nx_/2)*pct.resolution_+pct.cx_,(n.idx[2]-pct.ny_/2)*pct.resolution_+pct.cy_,n.height+.35);};
    const Eigen::Vector3d from=world(a),to=world(b),delta=to-from;const double yaw=std::atan2(delta.y(),delta.x());
    const int steps=std::max(1,int(std::ceil(delta.norm()/.025)));double total=0.;
    for(int i=1;i<=steps;++i){const Eigen::Vector3d p=from+delta*(double(i)/steps);double value[4];pointAssessment(reference,p.x(),p.y(),p.z(),yaw,value);total+=value[3];}
    return 2.*total/steps*delta.norm()/pct.resolution_;
  });
  std::ifstream endpoints(std::getenv("ROUTE_ENDPOINTS"));Eigen::Vector3d start,goal;endpoints>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z();
  pct.plan(start,goal,false);auto seed=pct.planner_.get_path_finder().GetPathPoints();seed.front().ref_v=seed.back().ref_v=1.;freePointField(reference);
  auto map=pct.planner_.map_;const auto actual=map->environmental_cost_;
  const std::filesystem::path output=std::getenv("PROBE_OUTPUT");std::filesystem::create_directories(output);
  {std::ofstream csv(output/"seed.csv");csv<<std::setprecision(17)<<"layer,x,y,height,heading,ref_v\n";
    for(const auto &p:seed)csv<<p.layer<<','<<p.x<<','<<p.y<<','<<p.height<<','<<p.heading<<','<<p.ref_v<<'\n';}
  struct Case {std::string tag;bool absolute;int mode;bool continuous;bool frozen;double weight;};std::vector<Case> cases;
  if(std::getenv("GPMP_DIAG_SWEEP")) {
    cases.push_back({"legacy-original",false,0,false,false,1.});
    cases.push_back({"legacy-continuous",false,0,true,false,1.});
    for(bool continuous:{false,true})for(bool frozen:{false,true})for(double weight:{1.,20.,1e3,1e5,1e7})
      cases.push_back({std::string(continuous?"I":"O")+(frozen?"F":"V")+std::to_string(int(weight)),false,2,continuous,frozen,weight});
  } else for(bool absolute:{false,true})for(int mode:{0,1,2})
    cases.push_back({std::string(mode==0?"L":mode==1?"Z":"C")+(absolute?"-A":"-D"),absolute,mode,false,false,1.});
  for(const auto &test:cases) {
    const auto &tag=test.tag;const bool absolute=test.absolute;const int mode=test.mode;
    setenv("GPMP_DIAG_MODE",tag.c_str(),1);setenv("GPMP_DIAG_ABSOLUTE_ONLY",absolute?"1":"0",1);
    setenv("GPMP_DIAG_CONTINUOUS",test.continuous?"1":"0",1);setenv("GPMP_DIAG_FROZEN_HEADING",test.frozen?"1":"0",1);
    if(mode==0)map->SetEnvironmentalCost({});
    else if(mode==1)map->SetEnvironmentalCost([](double,double,double,double,Eigen::Vector4d *g){if(g)g->setZero();return 0.;});
    else map->SetEnvironmentalCost([&,weight=test.weight](double x,double y,double z,double yaw,Eigen::Vector4d *g){
      const double result=actual(x,y,z,yaw,g);if(g)*g*=weight;return result*weight;});
    GPMPOptimizer optimizer(15.,10.,map);optimizer.SetReferenceHeight(.35);
    const auto began=std::chrono::steady_clock::now();optimizer.GenerateTrajectory(seed,200.);
    const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count();
    const auto trajectory=optimizer.GetResultMatrix();const auto heights=optimizer.GetResultHeight();const auto states=optimizer.opt_results_;
    std::ofstream nodes(output/(tag+"_nodes.csv"));nodes<<std::setprecision(17)<<"grid_y,vy,ay,grid_x,vx,ax\n";
    for(int i=0;i<states.rows();++i){for(int j=0;j<6;++j)nodes<<(j?",":"")<<states(i,j);nodes<<'\n';}
    std::ofstream csv(output/(tag+".csv"));csv<<std::setprecision(17)<<"x,y,z,velocity_yaw,segment_yaw,velocity_cost,segment_cost,edge,solid\n";
    double total=0.,edge=1e100,solid=1e100;Eigen::Vector3d previous;
    for(int i=0;i<trajectory.rows();++i) {
      const Eigen::Vector3d p((trajectory(i,3)-pct.nx_/2)*pct.resolution_+pct.cx_,(trajectory(i,0)-pct.ny_/2)*pct.resolution_+pct.cy_,heights(i));
      const int a=i+1<trajectory.rows()?i:i-1,b=i+1<trajectory.rows()?i+1:i;
      const double yaw=std::atan2(trajectory(b,0)-trajectory(a,0),trajectory(b,3)-trajectory(a,3));
      const double vyaw=std::atan2(trajectory(i,1),trajectory(i,4));const auto assessed=field->assess(p,yaw);
      if(i)total+=(p-previous).norm()*assessed.cost();previous=p;
      edge=std::min(edge,assessed.edge_margin);solid=std::min(solid,assessed.solid_margin);
      csv<<p.x()<<','<<p.y()<<','<<p.z()<<','<<vyaw<<','<<yaw<<','<<field->cost(p,vyaw)<<','<<assessed.cost()<<','<<assessed.edge_margin<<','<<assessed.solid_margin<<'\n';
    }
    std::cout<<std::setprecision(17)<<"GPMP_RESULT mode="<<tag<<" seconds="<<seconds<<" seed_points="<<seed.size()<<" output_points="<<trajectory.rows()<<" integrated_cost="<<total<<" edge_min="<<edge<<" solid_min="<<solid<<'\n';
  }
}

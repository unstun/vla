// Read-only attribution of frozen requests through the actual installed mapper.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <iostream>
#include <fstream>
#include <iomanip>
int main(int argc,char**argv) {
  std::cout<<"ENDPOINT_HEADER case,endpoint,x,y,z,layer,index_y,index_x,node_cost,node_ground,ground_valid,decided_layer,ground_input_layer\n";
  for(int arg=1;arg<argc;++arg) {
    lite3_nav2::PCTRoutePlanner pct("/work/fixtures/building/route.pct",.3);
    pct.setEnvironmentalField(std::make_shared<reactive_stair::EnvironmentalField>(
      "/work/fixtures/building/environment225.env","10040917858432847476"));
    std::ifstream input(argv[arg]);Eigen::Vector3d start,goal;
    input>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z();
    if(!input)throw std::runtime_error("Missing frozen endpoints");
    for(int side=0;side<2;++side) {
      const auto p=side?goal:start;const auto idx=pct.poseToIndex(p);
      auto &finder=const_cast<Astar&>(pct.planner_.get_path_finder());
      auto *node=&finder.grid_map_[idx[0]][idx[2]][idx[1]];
      const auto ground_idx=pct.poseToIndex(p-Eigen::Vector3d(0,0,.3));
      std::cout<<std::setprecision(17)<<"ENDPOINT "<<argv[arg]<<','<<(side?"goal":"start")<<','
        <<p.x()<<','<<p.y()<<','<<p.z()<<','<<idx[0]<<','<<idx[1]<<','<<idx[2]<<','<<node->cost<<','<<node->height<<','
        <<unsigned(pct.ground_valid_[(idx[0]*pct.nx_+idx[2])*pct.ny_+idx[1]])<<','
        <<finder.DecideLayer(node)<<','<<ground_idx[0]<<'\n';
    }
    auto &finder=const_cast<Astar&>(pct.planner_.get_path_finder());finder.Debug();
    const auto a=pct.poseToIndex(start),b=pct.poseToIndex(goal);
    const bool reached=finder.Search(a,b);
    std::cout<<"REACHABILITY "<<argv[arg]<<",reached="<<reached
      <<",visited_rows="<<finder.GetVisitedSet().rows()<<",path_points="<<finder.GetPathPoints().size()<<'\n';
  }
}

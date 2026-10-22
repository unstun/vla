// Read-only observer of installed v240. Private access is diagnostic only.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <map>
#include <set>
int main(int argc,char **argv) {
  lite3_nav2::PCTRoutePlanner pct("/work/fixtures/building/route.pct",.3);
  auto &a=const_cast<Astar&>(pct.planner_.get_path_finder());a.Debug();
  std::ofstream meta("/evaluation/graph_meta.txt");
  meta<<std::setprecision(17)<<pct.layers_<<' '<<pct.nx_<<' '<<pct.ny_<<' '
    <<pct.resolution_<<' '<<pct.cx_<<' '<<pct.cy_<<'\n';
  std::ofstream data("/evaluation/graph_states.f64",std::ios::binary);
  for(int l=0;l<pct.layers_;++l)for(int x=0;x<pct.nx_;++x)for(int y=0;y<pct.ny_;++y) {
    auto &n=a.grid_map_[l][x][y];
    double row[]={n.cost,n.height,n.ele,double(a.DecideLayer(&n)),double(n.idx[0]),
      double(pct.ground_valid_[(l*pct.nx_+x)*pct.ny_+y])};
    data.write(reinterpret_cast<const char*>(row),sizeof(row));
  }
  for(int arg=1;arg<argc;++arg) {
    std::ifstream file(argv[arg]);Eigen::Vector3d p,q;
    file>>p.x()>>p.y()>>p.z()>>q.x()>>q.y()>>q.z();
    if(!file)throw std::runtime_error("missing endpoints");
    for(int reverse=0;reverse<2;++reverse) {
      auto s=pct.poseToIndex(reverse?q:p),g=pct.poseToIndex(reverse?p:q);
      bool ok=a.Search(s,g);auto visited=a.GetVisitedSet();
      // GetVisitedSet is stale on the goal-cost early return; mark that case.
      bool early=a.grid_map_[g[0]][g[2]][g[1]].cost>20;
      if(early)visited.resize(0,3);
      std::string casepath=argv[arg];auto end=casepath.rfind('/');
      std::string id=casepath.substr(0,end);id=id.substr(id.rfind('/')+1);
      std::ofstream v("/evaluation/visited_"+id+(reverse?"_reverse":"")+".csv");
      for(int i=0;i<visited.rows();++i)v<<visited(i,0)<<','<<visited(i,1)<<','<<visited(i,2)<<'\n';
      std::cout<<"QUERY "<<id<<" reverse="<<reverse<<" reached="<<ok<<" visited="<<visited.rows()
        <<" start="<<s.transpose()<<" goal="<<g.transpose()<<'\n';
    }
  }
}

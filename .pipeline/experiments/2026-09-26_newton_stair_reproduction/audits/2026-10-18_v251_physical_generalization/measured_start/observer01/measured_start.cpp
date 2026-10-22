// New independent C++ queries on unchanged recorded requests; no runtime patch.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <fstream>
#include <iomanip>
#include <iostream>
int main(int argc,char **argv) {
 if(argc!=3)throw std::runtime_error("Input/output required");
 auto field=std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476");
 auto support=std::make_shared<reactive_stair::StaticSupportField>("/work/fixtures/building/native.support","1404261889151999461");
 std::ifstream input(argv[1]);std::ofstream summary(std::string(argv[2])+"/summary.csv"),edges(std::string(argv[2])+"/edges.csv");
 summary<<std::setprecision(17)<<"label,x,y,z,yaw,actual_verdict,grid_x,grid_y,grid_z,grid_verdict,allowed_edges,plan,error\n";
 edges<<std::setprecision(17)<<"label,layer,dx,dy,yaw,allowed,first_refused_sample,x,y,z,verdict\n";
 std::string label;Eigen::Vector3d start,goal;double yaw;
 while(input>>label>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z()>>yaw) {
  lite3_nav2::PCTRoutePlanner pct("/work/fixtures/building/native_original.pct",.3);pct.setEnvironmentalField(field);pct.setStaticSupport(support);
  const auto idx=pct.poseToIndex(start);const auto &graph=pct.planner_.get_path_finder();const auto &node=graph.grid_map_[idx(0)][idx(2)][idx(1)];
  const auto world=[&](const Node &n){return Eigen::Vector3d((n.idx(1)-pct.nx_/2)*.1+pct.cx_,(n.idx(2)-pct.ny_/2)*.1+pct.cy_,n.height+.3);};
  const auto from=world(node);int admitted=0;
  for(int dx=-1;dx<=1;++dx)for(int dy=-1;dy<=1;++dy)if(dx||dy) {
   const int x=node.idx(1)+dx,y=node.idx(2)+dy;
   if(x<0||y<0||x>=graph.max_y_||y>=graph.max_x_)continue;
   for(int layer=0;layer<graph.max_layers_;++layer) {
    const auto &next=graph.grid_map_[layer][x][y];if(next.height<=-50.||std::abs(next.height-node.height)>=.26)continue;
    const auto to=world(next);const double angle=std::atan2(to.y()-from.y(),to.x()-from.x());const bool valid=pct.transitionAllowed(node,next);admitted+=valid;
    int first=-1,verdict=0;Eigen::Vector3d refused=from;const int n=std::max(1,int(std::ceil((to-from).norm()/.025)));
    for(int j=0;j<=n;++j){const auto p=from+(to-from)*(double(j)/n);auto v=support->assess(p.x(),p.y(),p.z(),angle);if(v!=reactive_stair::Verdict::Free){first=j;verdict=int(v);refused=p;break;}}
    edges<<label<<','<<layer<<','<<dx<<','<<dy<<','<<angle<<','<<valid<<','<<first<<','<<refused.x()<<','<<refused.y()<<','<<refused.z()<<','<<verdict<<'\n';
   }
  }
  bool planned=false;std::string error;try{planned=!pct.plan(start,goal,true).empty();}catch(const std::exception&e){error=e.what();}
  summary<<label<<','<<start.x()<<','<<start.y()<<','<<start.z()<<','<<yaw<<','<<int(support->assess(start.x(),start.y(),start.z(),yaw))<<','<<from.x()<<','<<from.y()<<','<<from.z()<<','<<int(support->assess(from.x(),from.y(),from.z(),yaw))<<','<<admitted<<','<<planned<<','<<error<<'\n';
 }
}

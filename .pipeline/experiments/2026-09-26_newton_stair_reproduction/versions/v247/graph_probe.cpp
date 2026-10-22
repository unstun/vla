// Diagnostic observer of the actual installed candidate graph.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <map>
int main(int argc,char **argv) {
  lite3_nav2::PCTRoutePlanner pct("/work/fixtures/building/native_original.pct",.3);
  auto support=std::make_shared<reactive_stair::StaticSupportField>("/evaluation/support/native.support","1404261889151999461");
  pct.setEnvironmentalField(std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476"));
  pct.setStaticSupport(support);
  auto &a=const_cast<Astar&>(pct.planner_.get_path_finder());a.Debug();
  const auto native=a.transition_validator_;
  for(int arg=1;arg<argc;++arg) {
    std::ifstream file(argv[arg]);Eigen::Vector3d start,goal;double yaw;
    file>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z()>>yaw;
    int goal_clear=0;
    for(int k=0;k<72;++k)goal_clear+=support->assess(goal.x(),goal.y(),goal.z(),k*M_PI/36.)==reactive_stair::Verdict::Free;
    std::cout<<"ENDPOINT "<<argv[arg]<<" start_verdict="<<int(support->assess(start.x(),start.y(),start.z(),yaw))<<" goal_clear_headings="<<goal_clear<<"/72\n";
    std::map<std::string,int> counts;size_t witnesses=0;
    a.SetTransitionValidator([&](const Node &from,const Node &to) {
      const bool ok=native(from,to);if(ok){++counts["allowed"];return true;}
      const auto valid=[&](const Node &n){return pct.ground_valid_[(n.layer*pct.nx_+n.idx[1])*pct.ny_+n.idx[2]]!=0;};
      const double ca=pct.ceiling_(from.layer*pct.nx_+from.idx[1],from.idx[2])-from.height;
      const double cb=pct.ceiling_(to.layer*pct.nx_+to.idx[1],to.idx[2])-to.height;
      std::string why=!valid(from)||!valid(to)?"invalid_ground":"support";
      const auto world=[&](const Node &n){return Eigen::Vector3d((n.idx[1]-pct.nx_/2)*.1+pct.cx_,(n.idx[2]-pct.ny_/2)*.1+pct.cy_,n.height+.3);};
      const auto p=world(from),q=world(to);const double angle=std::atan2(q.y()-p.y(),q.x()-p.x());
      if(witnesses++<8)std::cout<<std::setprecision(17)<<"REJECT "<<why<<" from="<<p.transpose()<<" to="<<q.transpose()<<" ceiling="<<ca<<','<<cb<<" field="<<int(support->assess(p.x(),p.y(),p.z(),angle))<<','<<int(support->assess(q.x(),q.y(),q.z(),angle))<<'\n';
      ++counts[why];return false;
    });
    for(int reverse=0;reverse<2;++reverse) {
    const bool ok=a.Search(pct.poseToIndex(reverse?goal:start),pct.poseToIndex(reverse?start:goal));
    auto v=a.GetVisitedSet();
    std::cout<<"GRAPH "<<argv[arg]<<" reverse="<<reverse<<" pass="<<ok<<" visited="<<v.rows()<<" start="<<pct.poseToIndex(start).transpose()<<" goal="<<pct.poseToIndex(goal).transpose()<<'\n';
    for(const auto &entry:counts)std::cout<<entry.first<<'='<<entry.second<<' ';std::cout<<'\n';
    std::ofstream output(std::string("/evaluation/")+std::to_string(arg)+"_"+std::to_string(reverse)+"_visited.csv");
    for(int i=0;i<v.rows();++i)output<<v(i,0)<<','<<v(i,1)<<','<<v(i,2)<<'\n';
    }
  }
}

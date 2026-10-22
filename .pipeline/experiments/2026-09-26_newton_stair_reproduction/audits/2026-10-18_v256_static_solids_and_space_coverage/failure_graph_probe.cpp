// Post-score observer only. Links the immutable installed v256 libraries.
// Diagnostic ablations never replace a scored result or admission policy.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <map>
#include <chrono>
int main(int argc,char **argv) {
  lite3_nav2::PCTRoutePlanner pct("/work/fixtures/building/native_original.pct",.3);
  auto support=std::make_shared<reactive_stair::StaticSupportField>("/work/fixtures/building/native.support","1404261889151999461");
  auto solid=std::make_shared<reactive_stair::StaticSolidField>("/work/fixtures/building/static_solids.env","17629216882668158307");
  pct.setEnvironmentalField(std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476"));
  pct.setStaticSupport(support);
  for(int arg=1;arg<argc;++arg) {
    const std::string cid=argv[arg];
    std::ifstream file("/evaluation/cases/"+cid+"/endpoints.txt");
    Eigen::Vector3d start,goal;double sy,gy;
    file>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z()>>sy>>gy;
    if(!file)throw std::runtime_error("missing endpoint fixture");
    for(int full=0;full<2;++full) {
      pct.setStaticSolid(full?solid:nullptr);
      auto &a=const_cast<Astar&>(pct.planner_.get_path_finder());a.Debug();
      const auto native=a.transition_validator_;
      std::map<std::string,int> counts;
      std::ofstream rejects("/evaluation/diagnosis/"+cid+"_"+std::to_string(full)+"_rejects.csv");
      rejects<<"ax,ay,az,bx,by,bz,yaw,why,sample,x,y,z,verdict,margin\n"<<std::setprecision(17);
      a.SetTransitionValidator([&](const Node &from,const Node &to) {
        if(native(from,to)){++counts["allowed"];return true;}
        const auto p=pct.nodePosition(from),q=pct.nodePosition(to);const Eigen::Vector3d d=q-p;
        const double yaw=std::atan2(d.y(),d.x());
        const int n=std::max(1,int(std::ceil(d.norm()/.025)));
        bool found=false;
        for(int i=0;i<=n;++i) {
          const Eigen::Vector3d v=p+d*(double(i)/n);
          const auto verdict=support->assess(v.x(),v.y(),v.z(),yaw);
          const bool collision=full&&solid->collides(v,yaw);
          if(verdict!=reactive_stair::Verdict::Free||collision) {
            const std::string why=verdict!=reactive_stair::Verdict::Free?"support":"solid";
            ++counts[why+"_"+std::to_string(int(verdict))];
            // Store the complete rejected frontier, not a chosen witness.
            rejects<<p.x()<<','<<p.y()<<','<<p.z()<<','<<q.x()<<','<<q.y()<<','<<q.z()<<','<<yaw<<','<<why<<','<<i<<','<<v.x()<<','<<v.y()<<','<<v.z()<<','<<int(verdict)<<','<<(collision?solid->assess(v,yaw).margin:0.)<<'\n';
            found=true;break;
          }
        }
        if(!found)++counts["topology_or_height"];
        return false;
      });
      const auto began=std::chrono::steady_clock::now();bool pass=false;std::string why;
      try {pass=pct.plan(start,goal,false).size()>=2;}catch(const std::exception &e){why=e.what();}
      const auto visited=a.GetVisitedSet();
      std::ofstream output("/evaluation/diagnosis/"+cid+"_"+std::to_string(full)+"_visited.csv");
      output<<"z_index,x_index,y_index\n";
      for(int i=0;i<visited.rows();++i)output<<visited(i,0)<<','<<visited(i,1)<<','<<visited(i,2)<<'\n';
      std::cout<<"DIAG "<<cid<<" solids="<<full<<" pass="<<pass<<" reason="<<why<<" visited="<<visited.rows()<<" wall_s="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count();
      for(const auto &entry:counts)std::cout<<' '<<entry.first<<'='<<entry.second;
      std::cout<<std::endl;
    }
  }
}

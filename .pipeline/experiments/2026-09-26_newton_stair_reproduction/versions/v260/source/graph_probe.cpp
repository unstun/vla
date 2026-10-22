// Read-only observer. Ablations are diagnostic and never admitted/published.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <map>
#include <chrono>
int main(int argc,char **argv) {
 for(int arg=1;arg<argc;++arg)for(int full=0;full<2;++full) {
  lite3_nav2::PCTRoutePlanner pct("/work/fixtures/building/native_original.pct",.3);
  auto support=std::make_shared<reactive_stair::StaticSupportField>("/work/fixtures/building/native.support","15212154834549674106");
  auto solid=std::make_shared<reactive_stair::StaticSolidField>("/work/fixtures/building/static_solids.env","17629216882668158307");
  pct.setEnvironmentalField(std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476"));
  pct.setStaticSupport(support);if(full)pct.setStaticSolid(solid);
  if(arg==1&&full)for(double x:{6.,7.,8.,8.5,9.})for(double y:{4.5,4.8,5.,5.25,5.5,5.75,6.,6.5}) {
    const Eigen::Vector3d body(x,y,.35803004);const auto v=solid->assess(body,M_PI/2);
    std::cout<<std::setprecision(17)<<"SOLID x="<<x<<" y="<<y<<" margin="<<v.margin<<" witness="<<v.witness.transpose()<<std::endl;
  }
  auto &a=const_cast<Astar&>(pct.planner_.get_path_finder());a.Debug();
  const auto native=a.transition_validator_;
  std::ifstream file(argv[arg]);Eigen::Vector3d start,goal;double yaw;
  file>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z()>>yaw;
  std::map<int,size_t> counts;
  const auto stem=std::string("/evaluation/diagnosis/")+std::to_string(arg)+"_"+std::to_string(full);
  std::ofstream rejected(stem+"_rejected.csv");rejected<<std::setprecision(17)<<"ax,ay,az,bx,by,bz,x,y,z,yaw,verdict,solid\n";
  a.SetTransitionValidator([&](const Node &from,const Node &to) {
   const bool ok=native(from,to);if(ok){++counts[-1];return true;}
   const Eigen::Vector3d p=pct.nodePosition(from),q=pct.nodePosition(to),d=q-p;
   const double angle=std::atan2(d.y(),d.x());const int n=std::max(1,int(std::ceil(d.norm()/.025)));
   int why=99;Eigen::Vector3d bad=p;bool collision=false;
   for(int i=0;i<=n;++i) {
    const Eigen::Vector3d at=p+d*(double(i)/n);const int v=int(support->assess(at.x(),at.y(),at.z(),angle));
    const bool c=full&&solid->collides(at,angle);
    if(v!=0||c){why=v;bad=at;collision=c;break;}
   }
   ++counts[collision?100:why];rejected<<p.x()<<','<<p.y()<<','<<p.z()<<','<<q.x()<<','<<q.y()<<','<<q.z()<<','<<bad.x()<<','<<bad.y()<<','<<bad.z()<<','<<angle<<','<<why<<','<<collision<<'\n';
   return false;
  });
  const auto begin=std::chrono::steady_clock::now();bool ok=false;std::string error;
  try{ok=pct.plan(start,goal,false).size()>1;}catch(const std::exception &e){error=e.what();}
  const auto v=a.GetVisitedSet();std::ofstream visited(stem+"_visited.csv");visited<<std::setprecision(17)<<"x,y,z,layer\n";
  for(int i=0;i<v.rows();++i){const int l=v(i,0),x=v(i,1),y=v(i,2);visited<<(x-pct.nx_/2)*.1+pct.cx_<<','<<(y-pct.ny_/2)*.1+pct.cy_<<','<<pct.planning_ground_(l*pct.nx_+x,y)+.3<<','<<l<<'\n';}
  std::cout<<"GRAPH case="<<argv[arg]<<" solids="<<full<<" pass="<<ok<<" error="<<error<<" visited="<<v.rows()<<" time="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<'\n';
  for(const auto &e:counts)std::cout<<e.first<<'='<<e.second<<' ';std::cout<<std::endl;
 }
}

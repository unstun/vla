// Read-only offline phase observer. No ablated path is admitted or published.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <fstream>
#include <iostream>
#include <chrono>
int main(int argc,char **argv) {
  lite3_nav2::PCTRoutePlanner pct("/work/fixtures/building/native_original.pct",.3);
  pct.setEnvironmentalField(std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476"));
  pct.setStaticSupport(std::make_shared<reactive_stair::StaticSupportField>("/work/fixtures/building/native.support","1404261889151999461"));
  auto solid=std::make_shared<reactive_stair::StaticSolidField>("/work/fixtures/building/static_solids.env","17629216882668158307");
  for(int j=1;j<argc;++j)for(int full=0;full<2;++full) {
    pct.setStaticSolid(full?solid:nullptr);
    Eigen::Vector3d from,to;std::ifstream f(argv[j]);f>>from.x()>>from.y()>>from.z()>>to.x()>>to.y()>>to.z();
    auto &a=const_cast<Astar&>(pct.planner_.get_path_finder());
    const auto hard=a.transition_validator_;const auto soft=a.environmental_cost_;
    size_t hard_n=0,soft_n=0;double hard_s=0,soft_s=0;
    using Clock=std::chrono::steady_clock;
    a.SetTransitionValidator([&](const Node &p,const Node &q){const auto t=Clock::now();const bool ok=hard(p,q);hard_s+=std::chrono::duration<double>(Clock::now()-t).count();++hard_n;return ok;});
    a.SetEnvironmentalCost([&](const Node &p,const Node &q){const auto t=Clock::now();const auto c=soft(p,q);soft_s+=std::chrono::duration<double>(Clock::now()-t).count();++soft_n;return c;});
    const auto began=Clock::now();bool ok=false;
    try {ok=pct.plan(from,to,false).size()>1;}catch(const std::exception &e){std::cout<<"WHY "<<e.what()<<'\n';}
    std::cout<<"PHASE solids="<<full<<" pass="<<ok<<" hard_calls="<<hard_n<<" hard_s="<<hard_s<<" soft_calls="<<soft_n<<" soft_s="<<soft_s<<" total_s="<<std::chrono::duration<double>(Clock::now()-began).count()<<std::endl;
  }
}

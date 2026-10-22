// Development observer of actual installed native callbacks; no model replacement.
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <chrono>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <map>
#include <set>
#include <cstring>
struct Counter {size_t calls=0;double seconds=0;};
int main(int argc,char **argv){
 for(int j=1;j<argc;++j){
  lite3_nav2::PCTRoutePlanner p("/work/fixtures/building/native_original.pct",.3);
  p.setEnvironmentalField(std::make_shared<reactive_stair::EnvironmentalField>("/work/fixtures/building/environment225.env","10040917858432847476"));
  p.setStaticSupport(std::make_shared<reactive_stair::StaticSupportField>("/work/fixtures/building/native.support","15212154834549674106"));
  p.setStaticSolid(std::make_shared<reactive_stair::StaticSolidField>(std::getenv("RAW_FIELD"),std::getenv("RAW_FNV")));
  auto &a=const_cast<Astar&>(p.planner_.get_path_finder());std::map<std::string,Counter> counts;
  const auto wrap=[&](auto original,std::string name){return [&,original,name](auto &&...args){
    const auto begin=std::chrono::steady_clock::now();const auto result=original(std::forward<decltype(args)>(args)...);
    auto &count=counts[name];++count.calls;count.seconds+=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();return result;
  };};
  a.pose_validator_=wrap(a.pose_validator_,"pose_edge");a.pose_cost_=wrap(a.pose_cost_,"pose_cost");
  a.pose_validity_=wrap(a.pose_validity_,"pose_validity");a.free_rotation_=wrap(a.free_rotation_,"rotation");
  Eigen::Vector3d start,goal;double sy,gy;std::ifstream f(argv[j]);f>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z()>>sy>>gy;
  const auto begin=std::chrono::steady_clock::now();auto path=p.plan(start,goal,true,sy,gy);
  std::cout<<std::setprecision(17)<<"PROFILE total="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<" samples="<<path.size()<<" cache_queries="<<p.solid_query_cache_.queries()<<" cache_hits="<<p.solid_query_cache_.hits()<<'\n';
  std::set<uint64_t> heights;std::set<long long> intervals;
  for(const auto &e:p.solid_query_cache_.entries_){heights.insert(e.first.z);double z;const auto bits=e.first.z;std::memcpy(&z,&bits,sizeof(z));intervals.insert(std::llround(std::floor(z/.05)));}
  std::cout<<"PROFILE buckets="<<p.solid_query_cache_.entries_.size()<<" exact_heights="<<heights.size()<<" height_intervals="<<intervals.size()<<'\n';
  for(const auto &e:counts)std::cout<<"PROFILE "<<e.first<<" calls="<<e.second.calls<<" seconds="<<e.second.seconds<<'\n';
 }
}

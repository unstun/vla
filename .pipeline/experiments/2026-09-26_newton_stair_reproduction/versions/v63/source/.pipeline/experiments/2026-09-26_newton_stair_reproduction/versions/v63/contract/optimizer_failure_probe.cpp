// Actual optimizer/LBFGS flow; occupancy and graph results are scripted.
// This tests error propagation, not native collision, dynamics or tail latency.
#include <bspline_opt/bspline_optimizer.h>
#include <fstream>
#include <iomanip>
#include <cstdlib>
#include <stdexcept>
namespace fixture {
enum class Scene { Clear, SearchFailure, ShortPath, UsefulRepair };
Scene scene=Scene::Clear;
int searches=0,checks=0;
bool repaired=false;
Eigen::Vector3d first,last;
void check(bool ok,const char *name) {
  if(!ok)throw std::runtime_error(name);
  ++checks;std::cout<<"V63_OPTIMIZER_CHECK "<<name<<" PASS\n";
}
void reset(Scene s) { scene=s;searches=0;repaired=false; }
}
int optimizer_fixture_occupancy(Eigen::Vector3d p,double yaw) {
  if(!p.allFinite()||!std::isfinite(yaw))return 1;
  return fixture::scene!=fixture::Scene::Clear && !fixture::repaired &&
      p.x()>=.65 && p.x()<=.95 && std::abs(p.y())<.05;
}
ASTAR_RET AStar::AstarSearch(const double, Eigen::Vector3d p,Eigen::Vector3d q,bool,double) {
  ++fixture::searches;fixture::first=p;fixture::last=q;
  return fixture::scene==fixture::Scene::SearchFailure?ASTAR_RET::SEARCH_ERR:ASTAR_RET::SUCCESS;
}
std::vector<Eigen::Vector3d> AStar::getPath() {
  if(fixture::scene==fixture::Scene::ShortPath)return {};
  fixture::repaired=true;
  return {fixture::first,(fixture::first+fixture::last)*.5+Eigen::Vector3d(0,1,0),fixture::last};
}
// The scripted search owns no native grid-node pool. Keep its lifetime inside
// the same mocked boundary; real native search is tested in separate probes.
AStar::~AStar() {}
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  auto map=std::make_shared<GridMap>();map->initMap(node.get());
  map->occ_timer_->cancel();map->vis_timer_->cancel();
  Eigen::MatrixXd points(3,12);points.setZero();
  for(int i=0;i<points.cols();++i){points(0,i)=.2*i;points(2,i)=.35;}
  scan_planner::BsplineOptimizer optimizer;optimizer.setParam(node.get());
  optimizer.setEnvironment(map);optimizer.a_star_=std::make_shared<AStar>();
  auto initialize=[&](fixture::Scene scene) {
    fixture::reset(scene);auto input=points;
#ifdef OPTIMIZER_PARENT
    return optimizer.initControlPoints(input,true);
#else
    using Status=scan_planner::BsplineOptimizer::ControlPointInitializationStatus;
    Status status=Status::InvalidSearchPath;
    auto paths=optimizer.initControlPoints(input,true,&status);
    fixture::check(status==(scene==fixture::Scene::SearchFailure?Status::SearchFailure:
        scene==fixture::Scene::ShortPath?Status::InvalidSearchPath:Status::Success),"explicit_initialization_status_matches_outcome");
    return paths;
#endif
  };
  fixture::check(initialize(fixture::Scene::Clear).empty()&&fixture::searches==0,"empty_clear_initializer_is_success_without_search");
  fixture::check(initialize(fixture::Scene::SearchFailure).empty()&&fixture::searches==1,"failed_search_returns_no_usable_path");
  fixture::check(initialize(fixture::Scene::ShortPath).empty()&&fixture::searches==1,"short_search_path_is_rejected");
  fixture::check(initialize(fixture::Scene::UsefulRepair).size()==1&&fixture::searches==1,"useful_search_path_remains_available");
  struct Record { bool height;int scene,calls;bool success;double wall_ms; };
  std::vector<Record> records;
  for(bool height:{true,false})for(auto scene:{fixture::Scene::Clear,fixture::Scene::SearchFailure,fixture::Scene::ShortPath,fixture::Scene::UsefulRepair}) {
    initialize(fixture::Scene::Clear);fixture::reset(scene);optimizer.setOptimizeHeight(height);
    Eigen::MatrixXd result;const auto begin=std::chrono::steady_clock::now();
    const bool ok=optimizer.BsplineOptimizeTrajRebound(result,.5);
    const double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
    const bool failed=scene==fixture::Scene::SearchFailure||scene==fixture::Scene::ShortPath;
#ifdef OPTIMIZER_PARENT
    const int expected=failed?3:scene==fixture::Scene::UsefulRepair?1:0;
#else
    const int expected=failed?1:scene==fixture::Scene::UsefulRepair?1:0;
#endif
    fixture::check(ok==!failed,"optimizer_success_or_failure_result_preserved");
    fixture::check(fixture::searches==expected,"repair_search_count_matches_contract");
    fixture::check(result.allFinite()&&(result.leftCols(3)-points.leftCols(3)).norm()<1e-10 &&
        (result.rightCols(3)-points.rightCols(3)).norm()<1e-10,"scripted_boundary_control_points_remain_exact");
    records.push_back({height,int(scene),fixture::searches,ok,ms});
    std::cout<<"V63_OPTIMIZER_CASE height="<<height<<" scene="<<int(scene)<<" calls="<<fixture::searches<<" success="<<ok<<" wall_ms="<<ms<<"\n";
  }
  const char *output=std::getenv("V63_OPTIMIZER_OUTPUT");if(!output)throw std::runtime_error("explicit output required");
  std::ofstream out(output);out<<std::setprecision(17)<<"{\"scripted_map_and_search\":true,\"cases\":[";
  for(size_t i=0;i<records.size();++i){if(i)out<<",";auto x=records[i];out<<"{\"height\":"<<(x.height?"true":"false")<<",\"scene\":"<<x.scene<<",\"calls\":"<<x.calls<<",\"success\":"<<(x.success?"true":"false")<<",\"wall_ms\":"<<x.wall_ms<<"}";}
  out<<"]}\n";
#ifdef OPTIMIZER_PARENT
  std::cout<<"V63_PARENT_REPEATED_FAILURE_REPRODUCED checks="<<fixture::checks<<"\n";
#else
  std::cout<<"V63_OPTIMIZER_PASSED checks="<<fixture::checks<<"\n";
#endif
  rclcpp::shutdown();
}

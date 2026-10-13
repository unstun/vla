// Actual FSM/manager retry ownership; scripted solver and target admission.
// This is a control-flow test, not a collision/dynamics/latency qualification.
#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/timed_cubic_initialization.h>
#include <rcl/time.h>
#include <iomanip>
#include <stdexcept>
#include "retry_fixture.h"

namespace fixture {
rclcpp::Node *node=nullptr;
std::string scenario;
struct Attempt { double epoch; Eigen::Vector3d p,v,a,target; bool warm_allowed,height; };
std::vector<Attempt> attempts;
void check(bool ok,const char *name) { if(!ok)throw std::runtime_error(name); }
void clock(double s) {
  auto *h=node->get_clock()->get_clock_handle();
  check(rcl_enable_ros_time_override(h)==RCL_RET_OK &&
        rcl_set_ros_time_override(h,std::llround(s*1e9))==RCL_RET_OK,"fixture clock");
}
}

bool epoch_test_target(scan_planner::SCANReplanFSM *fsm) {
  fsm->local_projection_time_=0.;fsm->local_measured_projection_time_=0.;
  fsm->reference_frontier_time_=fsm->planner_manager_->global_data_.global_duration_;
  fsm->local_target_time_=.95*fsm->reference_frontier_time_;
  fsm->local_target_pt_=fsm->planner_manager_->global_data_.getPosition(fsm->local_target_time_);
  fsm->local_target_vel_.setZero();return true;
}

bool epoch_test_solve(scan_planner::SCANPlannerManager *manager,
    const Eigen::Vector3d &p,const Eigen::Vector3d &v,const Eigen::Vector3d &a,
    const Eigen::Vector3d &target,const Eigen::Vector3d &end_v,
    bool &attempted,bool allow_warm,bool *used_warm,const rclcpp::Time *origin) {
  using namespace fixture;
  const int id=attempts.size();check(id<20,"bounded retry count");
  check(origin!=nullptr,"captured source epoch retained");
  attempts.push_back({origin->seconds(),p,v,a,target,allow_warm,
                      manager->bspline_optimizer_rebound_->optimizesHeight()});
  attempted=scenario!="seed_exhaust";
  if(used_warm)*used_warm=scenario=="warm_cold" && id==0;
  clock(node->now().seconds()+.001);
  bool success=scenario=="first" ||
    ((scenario=="warm_cold" || scenario=="fixed_height") && id==1) ||
    (scenario=="shorter_target" && id==2);
  if(!success)return false;
  std::vector<Eigen::Vector3d> points;
  for(int i=0;i<=6;++i)points.push_back(p+(target-p)*(double(i)/6.));
  std::vector<Eigen::Vector3d> derivatives{v,end_v,a,Eigen::Vector3d::Zero()};
  Eigen::MatrixXd controls;
  check(reactive_stair::fitCubicBoundaryPva(.5,points,derivatives,controls),"boundary fit");
  scan_planner::UniformBspline curve(controls,3,.5);
  manager->updateTrajInfo(curve,*origin);
  return true;
}

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
#ifdef RETRY_PARENT
  const bool parent=true;
#else
  const bool parent=false;
#endif
  for(const auto &name: {"first","warm_cold","fixed_height","shorter_target","seed_exhaust","optimizer_exhaust"}) {
    auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
    node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);
    node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));
    fixture::node=node.get();fixture::clock(1.);
    scan_planner::SCANReplanFSM fsm;fsm.init(node.get());
    fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();
    auto &manager=*fsm.planner_manager_;
    manager.grid_map_->occ_timer_->cancel();manager.grid_map_->vis_timer_->cancel();
    manager.bspline_optimizer_rebound_->setOptimizeHeight(true);
    Eigen::MatrixXd controls(3,sizeof(fixture_controls)/sizeof(fixture_controls[0]));
    for(int i=0;i<controls.cols();++i)for(int j=0;j<3;++j)controls(j,i)=fixture_controls[i][j];
    Eigen::VectorXd knots(sizeof(fixture_knots)/sizeof(fixture_knots[0]));
    for(int i=0;i<knots.size();++i)knots[i]=fixture_knots[i];
    scan_planner::UniformBspline original(controls,3,1.);original.setKnot(knots);
    fixture::clock(fixture_sample_s);
    manager.updateTrajInfo(original,rclcpp::Time(std::llround(fixture_origin_s*1e9),RCL_ROS_TIME));
    manager.grid_map_->mutableMapState().mp_.map_min_boundary_=Eigen::Vector3d(2.,-11.,0.);
    manager.grid_map_->mutableMapState().mp_.map_max_boundary_=Eigen::Vector3d(12.,-1.,5.);
    fsm.navi_mode_=scan_planner::SCANReplanFSM::REFERENCE_PATH;
    fsm.have_target_=true;fsm.have_new_target_=false;
    fsm.end_pt_=Eigen::Vector3d(8.304121661516781,-3.038938803293399,3.4708704385181113);
    fsm.odom_pos_=original.evaluateDeBoorT(fixture_sample_s-fixture_origin_s);fsm.odom_vel_.setZero();
    fixture::check(manager.planGlobalTrajWaypoints(fsm.odom_pos_,Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero(),
        {fsm.end_pt_},Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero()),"global reference");
    fixture::scenario=name;fixture::attempts.clear();
    const auto original_id=manager.local_data_.traj_id_;
    const bool success=fsm.planFromCurrentTraj();
    const auto attempts=fixture::attempts;
    const bool exhausted=fixture::scenario.find("exhaust")!=std::string::npos;
    const int expected=fixture::scenario=="first"?1:
      fixture::scenario=="shorter_target"?3:
      fixture::scenario=="seed_exhaust"?(parent?6:4):
      fixture::scenario=="optimizer_exhaust"?(parent?12:8):2;
    fixture::check(success==!exhausted,"expected recovery result");
    fixture::check(attempts.size()==size_t(expected),"actual attempt count");
    for(const auto &x:attempts) {
      fixture::check(std::abs(x.epoch-fixture_sample_s)<1e-9,"one checked epoch across retries");
      fixture::check((x.p-attempts[0].p).norm()<1e-12 && (x.v-attempts[0].v).norm()==0 &&
                     (x.a-attempts[0].a).norm()==0,"one sampled PVA across retries");
    }
    fixture::check(manager.bspline_optimizer_rebound_->optimizesHeight(),"height mode restored");
    if(fixture::scenario=="warm_cold") fixture::check(attempts[0].warm_allowed &&
       !attempts[1].warm_allowed && attempts[1].height,"cold retry retained");
    if(fixture::scenario=="fixed_height") fixture::check(attempts[0].height &&
       !attempts[1].height && !attempts[1].warm_allowed,"fixed height retained");
    if(fixture::scenario=="shorter_target") fixture::check(
       (attempts[0].target-attempts[1].target).norm()==0 &&
       (attempts[2].target-attempts[0].target).norm()>.01,"shorter target retained");
    if(exhausted) {
      fixture::check(manager.local_data_.traj_id_==original_id &&
        (manager.local_data_.position_traj_.getControlPoint()-controls).norm()==0,
        "failed round preserves previous curve");
      fixture::check(!fsm.feasible_window_.valid,"failed window invalidated");
      const double next_epoch=node->now().seconds();
      fixture::scenario="first";fixture::attempts.clear();
      fixture::check(fsm.planFromCurrentTraj() && fixture::attempts.size()==1,
        "next round can recover without failure cache");
      fixture::check(std::abs(fixture::attempts[0].epoch-next_epoch)<1e-9,"next round fresh epoch");
    }
    std::cout<<"V126_RETRY_CASE {\"name\":\""<<name<<"\",\"parent\":"
       <<(parent?"true":"false")<<",\"attempts\":"<<attempts.size()
       <<",\"success\":"<<(success?"true":"false")<<",\"passed\":true}\n";
  }
  std::cout<<"V126_RETRY_PASSED\n";
  rclcpp::shutdown();
}

// Compile the actual FSM/manager retry flow. Only target admission and solver
// outcomes are scripted; this probe does not claim collision/dynamics acceptance.
#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/timed_cubic_initialization.h>
#include <rcl/time.h>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <cstdlib>
#include "retry_fixture.h"

namespace epoch_fixture {
rclcpp::Node *node=nullptr;
int checks=0;
struct Attempt { double now,origin;bool sampled;Eigen::Vector3d p,v,a; };
std::vector<Attempt> attempts;
void clock(double seconds) {
  auto *handle=node->get_clock()->get_clock_handle();
  if(rcl_enable_ros_time_override(handle)!=RCL_RET_OK ||
     rcl_set_ros_time_override(handle,std::llround(seconds*1e9))!=RCL_RET_OK)
    throw std::runtime_error("fixture clock");
}
void check(bool ok,const char *name) {
  if(!ok)throw std::runtime_error(name);
  ++checks;std::cout<<"V62_RETRY_CHECK "<<name<<" PASS\n";
}
}

bool epoch_test_target(scan_planner::SCANReplanFSM *fsm) {
  fsm->local_projection_time_=0.;fsm->local_measured_projection_time_=0.;
  fsm->local_target_time_=4.;fsm->reference_frontier_time_=5.;
  fsm->local_target_pt_=fsm->planner_manager_->global_data_.getPosition(4.);
  fsm->local_target_vel_.setZero();return true;
}

bool epoch_test_solve(scan_planner::SCANPlannerManager *manager,
    const Eigen::Vector3d &p,const Eigen::Vector3d &v,const Eigen::Vector3d &a,
    const Eigen::Vector3d &target,const Eigen::Vector3d &end_v,
    bool &optimization_attempted,bool *used_warm,const rclcpp::Time *origin) {
  using namespace epoch_fixture;
  const size_t id=attempts.size();
  if(id>=8)throw std::runtime_error("unexpected extra retry");
  attempts.push_back({node->now().seconds(),origin?origin->seconds():-1.,origin!=nullptr,p,v,a});
  if(used_warm)*used_warm=false;
  // The captured chain starts with a seed failure, then ordinary/fixed-height
  // failures at three prefixes, followed by success in the next init mode.
  optimization_attempted=id!=0;
  constexpr double delays[]={.179,.435,.440,.0028,.0006,.00043,.00059,.200887862};
  clock(node->now().seconds()+delays[id]);
  if(id!=7)return false;
  std::vector<Eigen::Vector3d> points;
  for(int i=0;i<=6;++i)points.push_back(p+(target-p)*(double(i)/6.));
  std::vector<Eigen::Vector3d> derivatives{v,end_v,a,Eigen::Vector3d::Zero()};
  Eigen::MatrixXd controls;
  if(!reactive_stair::fitCubicBoundaryPva(.5,points,derivatives,controls))
    throw std::runtime_error("scripted publication boundary");
  scan_planner::UniformBspline candidate(controls,3,.5);
  const auto publication_origin=origin?*origin:node->now();
  if((node->now()-publication_origin).seconds()>=candidate.getTimeSum())
    throw std::runtime_error("scripted candidate already elapsed");
  manager->updateTrajInfo(candidate,publication_origin);
  return true;
}

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  epoch_fixture::node=node.get();epoch_fixture::clock(1.);
  scan_planner::SCANReplanFSM fsm;fsm.init(node.get());
  fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();
  auto &manager=*fsm.planner_manager_;manager.grid_map_->occ_timer_->cancel();manager.grid_map_->vis_timer_->cancel();
  Eigen::MatrixXd controls(3,sizeof(fixture_controls)/sizeof(fixture_controls[0]));
  for(int i=0;i<controls.cols();++i)for(int j=0;j<3;++j)controls(j,i)=fixture_controls[i][j];
  Eigen::VectorXd knots(sizeof(fixture_knots)/sizeof(fixture_knots[0]));
  for(int i=0;i<knots.size();++i)knots[i]=fixture_knots[i];
  scan_planner::UniformBspline original(controls,3,1.);original.setKnot(knots);
  epoch_fixture::clock(fixture_sample_s);
  manager.updateTrajInfo(original,rclcpp::Time(std::llround(fixture_origin_s*1e9),RCL_ROS_TIME));
  fsm.navi_mode_=scan_planner::SCANReplanFSM::REFERENCE_PATH;
  fsm.have_target_=true;fsm.have_new_target_=false;
  fsm.end_pt_=Eigen::Vector3d(8.304121661516781,-3.038938803293399,3.4708704385181113);
  fsm.odom_pos_=original.evaluateDeBoorT(fixture_sample_s-fixture_origin_s);fsm.odom_vel_.setZero();
  epoch_fixture::check(manager.planGlobalTraj(fsm.odom_pos_,Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero(),
      fsm.end_pt_,Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero()),"fixture_global_reference");
  epoch_fixture::attempts.clear();
  epoch_fixture::check(fsm.planFromCurrentTraj(),"actual_fsm_retry_chain_completes");
  epoch_fixture::check(epoch_fixture::attempts.size()==8,"three_prefixes_and_next_init_mode_exercised");
  const auto &first=epoch_fixture::attempts.front();
  double position_delta=0.,velocity_delta=0.,acceleration_delta=0.;
  for(const auto &attempt:epoch_fixture::attempts) {
    position_delta=std::max(position_delta,(attempt.p-first.p).norm());
    velocity_delta=std::max(velocity_delta,(attempt.v-first.v).norm());
    acceleration_delta=std::max(acceleration_delta,(attempt.a-first.a).norm());
  }
  epoch_fixture::check(position_delta<1e-12 && velocity_delta==0. && acceleration_delta==0.,"sampled_pva_retained_across_actual_calls");
  const double publication=node->now().seconds(),accepted_origin=manager.local_data_.start_time_.seconds();
  epoch_fixture::check(publication>fixture_origin_s+original.getTimeSum(),"old_curve_expired_during_recovery");
  const char *output=std::getenv("V62_RETRY_OUTPUT");
  if(!output)throw std::runtime_error("explicit retry output required");
  std::ofstream out(output);out<<std::setprecision(17);
  if(!out)throw std::runtime_error("retry output unavailable");
  out<<"{\"parent_mode\":"<<
#ifdef EPOCH_PARENT
    "true"
#else
    "false"
#endif
    <<",\"sample_s\":"<<fixture_sample_s<<",\"publication_s\":"<<publication
    <<",\"accepted_origin_s\":"<<accepted_origin<<",\"rebased_by_s\":"<<accepted_origin-fixture_sample_s<<",\"attempts\":[";
  for(size_t i=0;i<epoch_fixture::attempts.size();++i){if(i)out<<",";const auto &x=epoch_fixture::attempts[i];
    out<<"{\"now_s\":"<<x.now<<",\"origin_s\":"<<x.origin<<",\"sampled\":"<<(x.sampled?"true":"false")<<"}";}
  out<<"]}";out.close();
#ifdef EPOCH_PARENT
  epoch_fixture::check(std::abs(accepted_origin-publication)<1e-9 && accepted_origin-fixture_sample_s>1.2,"parent_reproduces_stale_sample_retimestamp");
  std::cout<<"V62_PARENT_RED_REPRODUCED\n";
#else
  for(const auto &x:epoch_fixture::attempts)epoch_fixture::check(x.sampled && std::abs(x.origin-fixture_sample_s)<1e-9,"every_retry_retains_checked_epoch");
  epoch_fixture::check(std::abs(accepted_origin-fixture_sample_s)<1e-9,"candidate_publication_retains_original_epoch");
  const double second_sample=node->now().seconds();epoch_fixture::attempts.clear();
  epoch_fixture::check(fsm.planFromCurrentTraj(),"next_planning_round_completes");
  for(const auto &x:epoch_fixture::attempts)epoch_fixture::check(x.sampled && std::abs(x.origin-second_sample)<1e-9,"next_round_has_its_own_epoch");
  auto &local=manager.local_data_;const auto start=local.position_traj_.evaluateDeBoorT(0.),vel=local.velocity_traj_.evaluateDeBoorT(0.),acc=local.acceleration_traj_.evaluateDeBoorT(0.);
  auto origin=node->now();epoch_fixture::clock(local.start_time_.seconds()+local.duration_+.01);
  epoch_fixture::check(!manager.sampledTrajectoryOrigin(start,vel,acc,0.,origin),"already_expired_parent_not_initially_captured");
  const auto preserved=node->now();epoch_fixture::clock(local.start_time_.seconds()+.02);
  epoch_fixture::check(manager.sampledTrajectoryOrigin(local.position_traj_.evaluateDeBoorT(.01),local.velocity_traj_.evaluateDeBoorT(.01),local.acceleration_traj_.evaluateDeBoorT(.01),.01,origin),"valid_sample_capture");
  auto sentinel=preserved;
  epoch_fixture::check(!manager.sampledTrajectoryOrigin(start+Eigen::Vector3d(.01,0,0),vel,acc,0.,sentinel),"different_pva_not_captured");
  epoch_fixture::check(sentinel==preserved,"failed_capture_does_not_mutate_output");
  epoch_fixture::check(!manager.sampledTrajectoryOrigin(start,vel,acc,-1.,sentinel),"negative_sample_rejected");
  epoch_fixture::attempts.clear();const auto future=node->now()+rclcpp::Duration::from_seconds(.01);
  epoch_fixture::check(!manager.reboundReplan(start,vel,acc,fsm.end_pt_,Eigen::Vector3d::Zero(),false,false,&future) && epoch_fixture::attempts.empty(),"future_explicit_epoch_rejected_before_solver");
  const auto incompatible=rclcpp::Time(1,0,RCL_SYSTEM_TIME);
  epoch_fixture::check(!manager.reboundReplan(start,vel,acc,fsm.end_pt_,Eigen::Vector3d::Zero(),false,false,&incompatible) && epoch_fixture::attempts.empty(),"incompatible_explicit_clock_rejected_before_solver");
  std::cout<<"V62_RETRY_PASSED checks="<<epoch_fixture::checks<<"\n";
#endif
  rclcpp::shutdown();
}

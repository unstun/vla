// Native target/FSM method bodies are included verbatim. The manager's complete
// planning verdict, route and ROS publication are explicit test boundaries.
#include <Eigen/Eigen>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <functional>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
using Eigen::Vector3d;
namespace rclcpp {
struct Time { double value = 1.; double seconds() const { return value; } };
Time operator-(Time a, Time b) { return {a.value-b.value}; }
struct Node {
  Time now() { return {1.}; }
  const char* get_logger() { return "fixture"; }
  int* get_clock() { return nullptr; }
};
}
#define RCLCPP_WARN(logger, ...) std::fprintf(stderr, __VA_ARGS__)
#define RCLCPP_INFO(logger, ...) std::fprintf(stderr, __VA_ARGS__)
#define RCLCPP_ERROR(logger, ...) std::fprintf(stderr, __VA_ARGS__)
#define RCLCPP_WARN_THROTTLE(logger, clock, throttle, ...) std::fprintf(stderr, __VA_ARGS__)
namespace geometry_msgs { namespace msg { struct Point { double x,y,z; }; } }
namespace scan_planner_msgs { namespace msg {
struct Bspline { int order, traj_id; rclcpp::Time start_time; vector<geometry_msgs::msg::Point> pos_pts; vector<double> knots; };
} }
struct FixtureMap {
  function<int(const Vector3d&,double)> query = [](const Vector3d&,double) { return 0; };
  int getInflateOccupancy(const Vector3d& p, double yaw) { return query(p,yaw); }
};
struct Reference {
  Vector3d evaluate(double t) const { return {t,0,0}; }
};
struct GlobalData {
  double global_duration_ = 10., last_progress_time_ = 1.;
  Reference global_traj_;
  Vector3d getPosition(double t) const { return global_traj_.evaluate(t); }
  Vector3d getVelocity(double) const { return {1,0,0}; }
};
struct FixtureCurve {
  Vector3d evaluateDeBoorT(double) const { return Vector3d::Zero(); }
  Eigen::MatrixXd getControlPoint() const { return Eigen::MatrixXd::Zero(3,6); }
  Eigen::VectorXd getKnot() const { return Eigen::VectorXd::LinSpaced(10,-3,6); }
};
struct LocalTrajData {
  rclcpp::Time start_time_;
  double duration_ = 5.;
  int traj_id_ = 1;
  FixtureCurve position_traj_, velocity_traj_, acceleration_traj_;
};
struct Manager {
  struct Parameters { double max_vel_ = 1., max_acc_ = .5; } pp_;
  struct Call { Vector3d start, velocity, acceleration, goal, goal_velocity; bool poly, random; };
  GlobalData global_data_;
  LocalTrajData local_data_;
  shared_ptr<FixtureMap> grid_map_ = make_shared<FixtureMap>();
  vector<Call> calls;
  function<bool(const Call&)> verdict = [](const Call&) { return true; };
  bool reboundReplan(Vector3d p,Vector3d v,Vector3d a,Vector3d goal,Vector3d gv,bool poly,bool random) {
    calls.push_back({p,v,a,goal,gv,poly,random});
    return (goal-p).norm() >= .2 && verdict(calls.back());
  }
  bool planGlobalTraj(Vector3d,Vector3d,Vector3d,Vector3d,Vector3d,Vector3d) { return true; }
};
struct Publisher { int count = 0; void publish(const scan_planner_msgs::msg::Bspline&) { ++count; } };
struct Visualization { void displayOptimalTraj(const FixtureCurve&,int) {} };
class SCANReplanFSM {
 public:
  enum NAVI_MODE { MANUAL_TARGET=1, PRESET_TARGET=2, REFERENCE_PATH=3 };
  enum State { WAIT_TARGET, GEN_NEW_TRAJ, REPLAN_TRAJ, EXEC_TRAJ };
  int navi_mode_ = REFERENCE_PATH, current_wp_ = 0, replan_fail_count_ = 0;
  State state_ = EXEC_TRAJ;
  bool have_target_ = true, have_new_target_ = true;
  double planning_horizon_ = 5.;
  double reference_frontier_time_ = -1., local_target_time_ = 0., local_projection_time_ = 0.;
  Vector3d start_pt_ = Vector3d::Zero(), start_vel_ = Vector3d::Zero(), start_acc_ = Vector3d::Zero();
  Vector3d odom_pos_ = Vector3d::Zero(), end_pt_{10,0,0}, local_target_pt_ = Vector3d::Zero(), local_target_vel_ = Vector3d::Zero();
  vector<Vector3d> active_waypoints_;
  shared_ptr<Manager> planner_manager_ = make_shared<Manager>();
  shared_ptr<Publisher> bspline_pub_ = make_shared<Publisher>();
  shared_ptr<Visualization> visualization_ = make_shared<Visualization>();
  rclcpp::Node node_storage_;
  rclcpp::Node* node_ = &node_storage_;
  double estimateYawFromSegment(const Vector3d& a,const Vector3d& b) const { return atan2(b.y()-a.y(),b.x()-a.x()); }
  void attachP2BIdentity(scan_planner_msgs::msg::Bspline&) {}
  bool isWaypointSequenceMode() const { return navi_mode_ == PRESET_TARGET; }
  bool planNextWaypoint() { return false; }
  void changeFSMExecState(State value, const string&) { state_ = value; }
  bool adjustGlobalTargetIfOccupied();
  bool planFromCurrentTraj();
#ifdef CANDIDATE_REFERENCE_PREFIX
  bool getLocalTarget();
  bool callReboundReplan(bool,bool,int* = nullptr);
#else
  void getLocalTarget();
  bool callReboundReplan(bool,bool);
#endif
  void expireLocal();
};
#include "native_target_methods.inc"

void require(bool value,const char* message) { if(!value) throw runtime_error(message); }
void goalIntact(const SCANReplanFSM& f) {
  require(f.end_pt_ == Vector3d(10,0,0) && f.planner_manager_->global_data_.global_duration_ == 10.,
          "reference goal or full duration was changed");
  require(f.have_target_, "partial work cleared global target");
}
void global_preserved() {
  SCANReplanFSM f;
  f.planner_manager_->grid_map_->query=[](const Vector3d& p,double){return p.x()>8.?1:0;};
  require(f.adjustGlobalTargetIfOccupied(),"frontier not found"); goalIntact(f);
}
void adjusted_commit() {
  SCANReplanFSM f;
  f.planner_manager_->grid_map_->query=[](const Vector3d& p,double){return p.x()>=4.75 && p.x()<=5.5?1:0;};
  require(f.callReboundReplan(true,false),"adjusted target failed");
  require(abs(f.local_target_pt_.x()-4.5)<1e-12,"fixture did not adjust original target");
  require(abs(f.planner_manager_->global_data_.last_progress_time_-4.5)<1e-12,"committed raw rather than adjusted time");
  goalIntact(f);
}
void failed_progress() {
  SCANReplanFSM f; f.planner_manager_->verdict=[](const Manager::Call&){return false;};
  require(!f.callReboundReplan(true,false),"failed manager accepted");
  require(f.planner_manager_->global_data_.last_progress_time_==1. && f.bspline_pub_->count==0,"failed proposal advanced cursor or published");
  require(f.planner_manager_->calls.size()<=4,"prefix round exceeded primary plus three candidates"); goalIntact(f);
}
void prefix_success() {
  SCANReplanFSM f;
  f.start_vel_={.1,0,0}; f.start_acc_={.02,0,0};
  f.planner_manager_->verdict=[](const Manager::Call& c){return c.goal.x()<=3.;};
  require(f.callReboundReplan(true,false),"short route prefix was not tried");
  const auto& calls=f.planner_manager_->calls;
  require(calls.size()==2 && calls[0].goal.x()==5. && calls[1].goal.x()==2.5,"prefix was not bounded route-time halving");
  require(calls[1].goal_velocity.norm()==0. && calls[1].velocity==f.start_vel_ && calls[1].acceleration==f.start_acc_,"prefix did not preserve start PVA or request terminal stop");
  require(f.planner_manager_->global_data_.last_progress_time_==2.5 && f.bspline_pub_->count==1,"prefix success was not committed once");
  goalIntact(f); f.expireLocal();
  require(f.state_==SCANReplanFSM::REPLAN_TRAJ && f.have_target_,"partial expiry marked global completion");
}
void shared_budget() {
  SCANReplanFSM f; f.have_new_target_=false;
  f.planner_manager_->verdict=[](const Manager::Call&){return false;};
  require(!f.planFromCurrentTraj(),"all-failed outer round accepted");
  int prefix=0, primary=0;
  for(const auto& c:f.planner_manager_->calls) { if(c.goal.x()<5.) ++prefix; else ++primary; }
  require(prefix==3 && primary==3 && f.planner_manager_->calls.size()==6,"outer initialization attempts multiplied or skipped shared prefix budget");
  require(f.planner_manager_->global_data_.last_progress_time_==1. && f.bspline_pub_->count==0,"outer failure committed progress"); goalIntact(f);
}
void no_frontier() {
  SCANReplanFSM f;
  f.planner_manager_->grid_map_->query=[](const Vector3d&,double){return -1;};
  require(!f.adjustGlobalTargetIfOccupied(),"negative/Unknown occupancy counted as free frontier");
  require(!f.callReboundReplan(true,false) && f.planner_manager_->calls.empty(),"no-frontier case reused a target");
  require(f.planner_manager_->global_data_.last_progress_time_==1. && f.bspline_pub_->count==0,"no frontier committed state"); goalIntact(f);
}
void near_goal() {
  SCANReplanFSM f; f.start_pt_=f.odom_pos_={9.95,0,0};
  require(!f.callReboundReplan(true,false),"sub-0.2 m target accepted");
  require(f.planner_manager_->calls.empty() && f.planner_manager_->global_data_.last_progress_time_==1.,"too-near proposal reached manager or changed cursor");
}
void frontier_refresh() {
  SCANReplanFSM f; f.planning_horizon_=20.;
  for(double bound:{8.,6.,10.}) {
    f.planner_manager_->grid_map_->query=[bound](const Vector3d& p,double){return p.x()>bound?1:0;};
    require(f.callReboundReplan(true,false),"refreshed frontier failed"); goalIntact(f);
    require(abs(f.local_target_pt_.x()-bound)<1e-10 && f.local_target_vel_.norm()==0.,"frontier point or terminal stop stale");
    require(abs(f.planner_manager_->global_data_.last_progress_time_-bound)<1e-10,"actual successful frontier time not committed");
  }
}
void unchanged_positive() {
  SCANReplanFSM f; require(f.callReboundReplan(true,false),"original free target failed");
  require(f.planner_manager_->calls.size()==1 && f.local_target_pt_==Vector3d(5,0,0) && f.local_target_vel_==Vector3d(1,0,0),"primary target behavior changed");
  require(f.planner_manager_->global_data_.last_progress_time_==5. && f.bspline_pub_->count==1,"primary success not committed"); goalIntact(f);
  f.expireLocal(); require(f.state_==SCANReplanFSM::REPLAN_TRAJ && f.have_target_,"existing partial window completion changed");
}
void legacy_goal_adjustment() {
  SCANReplanFSM f; f.navi_mode_=SCANReplanFSM::MANUAL_TARGET;
  f.planner_manager_->grid_map_->query=[](const Vector3d& p,double){return p.x()>8.?1:0;};
  require(f.adjustGlobalTargetIfOccupied(),"legacy adjustment failed");
  require(f.end_pt_==Vector3d(8,0,0) && f.planner_manager_->global_data_.global_duration_==8.,"non-reference behavior changed");
}
void new_route_reset() {
  SCANReplanFSM f; f.reference_frontier_time_=8.;
  f.end_pt_={4,0,0}; f.planner_manager_->global_data_.global_duration_=4.;
  require(f.callReboundReplan(true,false),"new route failed");
  require(f.local_target_pt_==Vector3d(4,0,0) && f.planner_manager_->global_data_.last_progress_time_==4.,"new route reused previous frontier");
}
int main(int argc,char** argv) {
  try {
    require(argc==2,"one case required"); string name=argv[1];
    if(name=="global_preserved")global_preserved(); else if(name=="adjusted_commit")adjusted_commit();
    else if(name=="failed_progress")failed_progress(); else if(name=="prefix_success")prefix_success();
    else if(name=="shared_budget")shared_budget(); else if(name=="no_frontier")no_frontier();
    else if(name=="near_goal")near_goal(); else if(name=="frontier_refresh")frontier_refresh();
    else if(name=="unchanged_positive")unchanged_positive(); else if(name=="legacy_goal_adjustment")legacy_goal_adjustment();
    else if(name=="new_route_reset")new_route_reset(); else throw runtime_error("unknown case");
    cout<<name<<": PASS\n"; return 0;
  } catch(const exception& e) { cerr<<"FAIL: "<<e.what()<<'\n'; return 1; }
}

#include <scan_nav2_controller/controller.hpp>
#include <scan_nav2_controller/executor_shutdown.hpp>
#include <rclcpp/scope_exit.hpp>
#include <scan_nav2_controller/native_validation.hpp>

#include <map>
#include <filesystem>
#include <rclcpp/parameter_map.hpp>
#include <rcl_yaml_param_parser/parser.h>
#include <plan_manage/scan_replan_fsm.h>
#include <nav2_core/exceptions.hpp>
#include <pluginlib/class_list_macros.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>

namespace scan_nav2_controller
{
class NativeWorker
{
public:
  NativeWorker(const std::string &config, bool use_sim_time, std::function<void(const std::string &)> fault) {
    if (!std::filesystem::is_regular_file(config))
      throw nav2_core::PlannerException("Native SCAN parameter file is required");
    rclcpp::NodeOptions options;
    options.use_global_arguments(false);
    options.arguments({"--ros-args","-r","sensor_pose:=/quad_0/lidar_pose"});
    std::unique_ptr<rcl_params_t,decltype(&rcl_yaml_node_struct_fini)> parsed(
      rcl_yaml_node_struct_init(rcutils_get_default_allocator()),rcl_yaml_node_struct_fini);
    if (!parsed || !rcl_parse_yaml_file(config.c_str(),parsed.get()))
      throw nav2_core::PlannerException("Cannot parse native SCAN parameters");
    const auto map=rclcpp::parameter_map_from(parsed.get());
    auto found=map.find("/quad_0/scan_planner_node");
    if (found==map.end()) found=map.find("/scan_planner_node");
    if (found==map.end()) throw nav2_core::PlannerException("Native SCAN parameter section missing");
    auto parameters=found->second;
    parameters.erase(std::remove_if(parameters.begin(),parameters.end(),[](const rclcpp::Parameter &p) {
      return p.get_name()=="use_sim_time";
    }),parameters.end());
    parameters.emplace_back("use_sim_time",use_sim_time);
    options.parameter_overrides(parameters);
    node_=std::make_shared<rclcpp::Node>("scan_planner_node","/quad_0",options);
    const bool isolated_clock = use_sim_time && std::any_of(parameters.begin(),parameters.end(),
      [](const rclcpp::Parameter &p) { return p.get_name()=="grid_map.sensor_type" &&
        p.get_type()==rclcpp::ParameterType::PARAMETER_STRING && p.as_string()=="lidar"; });
    if (isolated_clock)
      work_group_=node_->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    planner_=std::make_unique<scan_planner::SCANReplanFSM>();
    planner_->init(node_.get(),work_group_);
    terrain_pub_=node_->create_publisher<nav_msgs::msg::OccupancyGrid>("/nav2_scan/terrain_slice",1);
    terrain_timer_=node_->create_wall_timer(std::chrono::milliseconds(100),[this] { publishTerrain(); },work_group_);
    // Foxy schedules /clock in the default callback group. Keep native data and
    // planning serialized, while its real ROS clock can progress during a solve.
    if (isolated_clock)
      executor_=std::make_shared<rclcpp::executors::MultiThreadedExecutor>(rclcpp::ExecutorOptions(),2);
    else executor_=std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
    executor_->add_node(node_);
    worker_=std::thread([this,fault] {
      RCLCPP_SCOPE_EXIT(finished_.store(true););
      try { executor_->spin(); }
      catch (const std::exception &error) { healthy_=false; fault(std::string("native_worker_exception:")+error.what()); }
      catch (...) { healthy_=false; fault("native_worker_unknown_exception"); }
    });
  }
  scan_planner_msgs::msg::P2BExecutionSafety validate(
      const rclcpp::Clock::SharedPtr &clock,const geometry_msgs::msg::PoseStamped &body,
      const scan_planner::UniformBspline &curve,double phase) const {
    auto map=planner_->nav2Map();
    return map ? validateNativeCurve(*map,clock,body,curve,phase) : scan_planner_msgs::msg::P2BExecutionSafety();
  }

  bool healthy() const { return healthy_.load(); }
  ~NativeWorker() {
    joinStoppedExecutor(executor_,worker_,finished_);
    planner_.reset();
  }
private:
  void publishTerrain() {
    auto map=planner_->nav2Map();
    if (!map || !map->mapperHealthy()) return;
    // Acquire a completed immutable revision, then immediately release the
    // publication lock before reading any cells. This callback shares the native
    // executor, so it cannot race another planner read-state update.
    { auto lease=map->beginPublication(); }
    const double stamp=map->observationStamp();
    if (!std::isfinite(stamp) || stamp<=0 || stamp<=terrain_stamp_) return;
    Eigen::Vector3d body;
    if (!planner_->nav2BodyPosition(body)) return;
    nav_msgs::msg::OccupancyGrid grid;
    grid.header.frame_id="world";
    grid.header.stamp=rclcpp::Time(static_cast<int64_t>(stamp*1e9));
    grid.info.resolution=map->getResolution();
    grid.info.width=grid.info.height=static_cast<uint32_t>(std::ceil(6.0/grid.info.resolution));
    grid.info.origin.position.x=body.x()-3.0;
    grid.info.origin.position.y=body.y()-3.0;
    grid.info.origin.position.z=body.z(); // Body-height slice; not a ground-height claim.
    grid.info.origin.orientation.w=1.0;
    grid.data.resize(grid.info.width*grid.info.height,-1);
    for (unsigned y=0;y<grid.info.height;++y) for (unsigned x=0;x<grid.info.width;++x) {
      bool known=true,occupied=false;
      for (double dz=-0.15;dz<=0.15+1e-6;dz+=grid.info.resolution) {
        Eigen::Vector3d point(grid.info.origin.position.x+(x+0.5)*grid.info.resolution,
          grid.info.origin.position.y+(y+0.5)*grid.info.resolution,body.z()+dz);
        if (!map->isInMap(point) || map->isUnknown(point)) { known=false; continue; }
        occupied=occupied || map->getOccupancy(point)>0;
      }
      grid.data[y*grid.info.width+x]=occupied?100:(known?0:-1);
    }
    terrain_stamp_=stamp;
    terrain_pub_->publish(grid);
  }
  rclcpp::Publisher<nav_msgs::msg::OccupancyGrid>::SharedPtr terrain_pub_;
  rclcpp::TimerBase::SharedPtr terrain_timer_;
  double terrain_stamp_{0.0};
  rclcpp::Node::SharedPtr node_;
  rclcpp::CallbackGroup::SharedPtr work_group_;
  std::unique_ptr<scan_planner::SCANReplanFSM> planner_;
  std::shared_ptr<rclcpp::Executor> executor_;
  std::thread worker_;
  std::atomic<bool> healthy_{true};
  std::atomic<bool> finished_{false};
};
namespace
{
template<class A, class B> bool matches(const A &a, const B &b)
{
  return a.run_id == b.run_id && a.epoch == b.epoch && a.request_id == b.request_id &&
    a.goal_id == b.goal_id && a.route_id == b.route_id && a.command_id == b.command_id &&
    a.generation == b.generation && a.map_epoch == b.map_epoch && a.map_revision == b.map_revision;
}
template<class A, class B> void copyIdentity(const A &a, B &b)
{
  b.run_id=a.run_id; b.epoch=a.epoch; b.request_id=a.request_id; b.goal_id=a.goal_id;
  b.route_id=a.route_id; b.command_id=a.command_id; b.generation=a.generation;
  b.map_epoch=a.map_epoch; b.map_revision=a.map_revision;
}
bool finitePose(const geometry_msgs::msg::Pose &p)
{
  const auto &q=p.orientation;
  const double n=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;
  return std::isfinite(p.position.x) && std::isfinite(p.position.y) &&
    std::isfinite(p.position.z) && std::isfinite(n) && std::abs(n-1.0)<1e-6;
}
bool finiteTwist(const geometry_msgs::msg::Twist &t)
{
  return std::isfinite(t.linear.x) && std::isfinite(t.linear.y) && std::isfinite(t.linear.z) &&
    std::isfinite(t.angular.x) && std::isfinite(t.angular.y) && std::isfinite(t.angular.z);
}
bool atGoal(const geometry_msgs::msg::Pose &p, const State &s, double yaw_scale=1.0)
{
  if (!s.route || !finitePose(p)) return false;
  const auto &g=s.route->goal_pose;
  const double yaw=scan_planner::TrackingNode::normalizeAngle(tf2::getYaw(g.orientation)-tf2::getYaw(p.orientation));
  return std::hypot(p.position.x-g.position.x,p.position.y-g.position.y)<=s.xy_tolerance &&
    std::abs(p.position.z-g.position.z)<=s.z_tolerance && std::abs(yaw)<=yaw_scale*s.yaw_tolerance;
}
double stampSeconds(const builtin_interfaces::msg::Time &stamp)
{
  if (stamp.sec<0 || stamp.nanosec>=1000000000u) return std::numeric_limits<double>::quiet_NaN();
  // Match Clock::now().seconds() exactly for the same integer nanoseconds.
  // Separate sec/nanosec floating-point addition can round an identical stamp
  // above now and falsely classify a current pose/binding as future data.
  return rclcpp::Time(stamp).seconds();
}
bool fresh(double now, double stamp, double ttl)
{
  return std::isfinite(now) && std::isfinite(stamp) && stamp>0 && now>=stamp && now-stamp<=ttl;
}
template<class T> T parameter(const rclcpp_lifecycle::LifecycleNode::SharedPtr &node,
  const std::string &name, const T &fallback)
{
  if (!node->has_parameter(name)) node->declare_parameter<T>(name,fallback);
  return node->get_parameter(name).get_value<T>();
}
std::shared_ptr<State> sharedState(const rclcpp_lifecycle::LifecycleNode::SharedPtr &node,
  const std::string &name)
{
  static std::mutex mutex;
  static std::map<std::pair<const void *,std::string>,std::weak_ptr<State>> states;
  std::lock_guard<std::mutex> lock(mutex);
  const auto key=std::make_pair(static_cast<const void *>(node.get()),name);
  auto result=states[key].lock();
  if (!result) { result=std::make_shared<State>(); states[key]=result; }
  return result;
}
}  // namespace

Controller::~Controller() { cleanup(); }

void Controller::configure(const rclcpp_lifecycle::LifecycleNode::SharedPtr &parent,
  std::string name, const std::shared_ptr<tf2_ros::Buffer> &,
  const std::shared_ptr<nav2_costmap_2d::Costmap2DROS> &costmap)
{
  if (parent_) throw nav2_core::PlannerException("SCAN plugin is already configured");
  parent_=parent; name_=std::move(name); state_=sharedState(parent_,name_);
  global_frame_=parameter(parent_,name_+".global_frame",std::string("world"));
  base_frame_=parameter(parent_,name_+".base_frame",std::string("base_link"));
  if (costmap && (costmap->getGlobalFrameID()!=global_frame_ || costmap->getBaseFrameID()!=base_frame_))
    throw nav2_core::PlannerException("SCAN and Nav2 frame configuration disagree");
  binding_timeout_s_=parameter(parent_,name_+".binding_timeout",2.0);
  startup_timeout_s_=parameter(parent_,name_+".startup_timeout",2.0);
  if (!std::isfinite(binding_timeout_s_) || binding_timeout_s_<=0 ||
      !std::isfinite(startup_timeout_s_) || startup_timeout_s_<=0)
    throw nav2_core::PlannerException("Invalid SCAN admission timeout");
  // Preserve body/observation age gates. The new native-validation lease is
  // 100 ms; none of these gates is a tunable performance workaround.
  rclcpp::NodeOptions options;
  options.use_global_arguments(false);
  std::vector<rclcpp::Parameter> parameters;
  const std::vector<std::pair<std::string,double>> defaults={
    {"time_forward",0.8},{"heading_error_threshold",0.8},{"kp_pos",0.8},{"kp_yaw",1.5},
    {"max_vx",0.75},{"max_vy",0.35},{"max_vyaw",1.0},{"finish_dist",0.15},
    {"local_capture_stall_distance",0.03},{"local_capture_stall_timeout",1.0},
    {"local_capture_progress_radius",0.005},{"goal_xy_tolerance",0.25},{"goal_z_tolerance",0.20},{"goal_yaw_tolerance",0.25}};
  for (const auto &entry:defaults) {
    const double value=parameter(parent_,name_+"."+entry.first,entry.second);
    if (!std::isfinite(value) || value<=0) throw nav2_core::PlannerException("Invalid tracking parameter");
    parameters.emplace_back(entry.first,value);
  }
  parameters.emplace_back("use_sim_time",parameter(parent_,"use_sim_time",false));
  parameters.emplace_back("stateful_local_capture",
    parameter(parent_,name_+".stateful_local_capture",false));
  options.parameter_overrides(parameters);
  options.arguments({"--ros-args", "-r", "planning/go2_execution_frozen:="+
    parameter(parent_,name_+".execution_frozen_topic",std::string("/quad_0/planning/go2_execution_frozen"))});
  tracker_=std::make_shared<scan_planner::TrackingNode>(options);
  state_->xy_tolerance=tracker_->goal_xy_tolerance_;
  state_->z_tolerance=tracker_->goal_z_tolerance_;
  state_->yaw_tolerance=tracker_->goal_yaw_tolerance_;
  // Goal hold revokes this owner permanently. Aim inside the acceptance band
  // before revocation so measured braking/dwell has room for residual yaw drift.
  // GoalChecker retains the original configured tolerance and physical proof.
  tracker_->goal_yaw_tolerance_ *= 0.5;
  rclcpp::NodeOptions bridge_options;
  bridge_options.use_global_arguments(false);
  bridge_options.parameter_overrides({rclcpp::Parameter("use_sim_time",parameter(parent_,"use_sim_time",false))});
  bridge_=std::make_shared<rclcpp::Node>("scan_nav2_"+name_,bridge_options);
  const auto topic=[&](const std::string &key,const std::string &fallback) {
    return parameter(parent_,name_+"."+key,fallback);
  };
  route_pub_=bridge_->create_publisher<scan_planner_msgs::msg::P2BRoute>(topic("route_topic","/p2b/route"),10);
  binding_ready_pub_=bridge_->create_publisher<scan_planner_msgs::msg::P2BRoute>(
    topic("binding_ready_topic","/nav2_scan/binding_ready"),10);
  const auto cancel_topic=topic("cancel_topic","/p2b/scan_cancel");
  cancel_pub_=bridge_->create_publisher<scan_planner_msgs::msg::P2BCancel>(cancel_topic,10);
  cancel_admission_pub_=bridge_->create_publisher<scan_planner_msgs::msg::P2BAdmission>("/p2b/scan_admission",10);
  command_pub_=bridge_->create_publisher<scan_planner_msgs::msg::P2BStampedTwist>(
    topic("command_topic","/quad_0/raw_scan_cmd_vel"),20);
  binding_sub_=bridge_->create_subscription<scan_planner_msgs::msg::P2BRoute>(
    topic("binding_topic","/nav2_scan/route_binding"),10,
    std::bind(&Controller::onBinding,this,std::placeholders::_1));
  spline_sub_=bridge_->create_subscription<scan_planner_msgs::msg::Bspline>(
    topic("spline_topic","/quad_0/planning/bspline"),10,
    std::bind(&Controller::onSpline,this,std::placeholders::_1));
  cancel_sub_=bridge_->create_subscription<scan_planner_msgs::msg::P2BCancel>(cancel_topic,10,
    std::bind(&Controller::onCancel,this,std::placeholders::_1));
  safety_sub_=bridge_->create_subscription<scan_planner_msgs::msg::P2BExecutionSafety>(
    topic("safety_topic","/quad_0/planning/execution_safety"),10,
    std::bind(&Controller::onSafety,this,std::placeholders::_1));
  stopped_sub_=bridge_->create_subscription<scan_planner_msgs::msg::P2BStopEvidence>(
    topic("stop_evidence_topic","/nav2_scan/stop_evidence"),10,
    std::bind(&Controller::onStopEvidence,this,std::placeholders::_1));
  executor_=std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
  executor_->add_node(bridge_); executor_->add_node(tracker_);
  thread_finished_=false;
  thread_=std::thread([this] {
    RCLCPP_SCOPE_EXIT(thread_finished_.store(true););
    executor_->spin();
  });
}

void Controller::activate()
{
  if (!state_) throw nav2_core::PlannerException("SCAN plugin is not configured");
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (parameter(parent_,name_+".native_worker_enabled",true) && !native_worker_)
    native_worker_=std::make_unique<NativeWorker>(
      parameter(parent_,name_+".native_planner_config",std::string("")),
      parameter(parent_,"use_sim_time",false), [this](const std::string &reason) { stop(reason); });
  state_->active=true;
}
void Controller::deactivate()
{
  if (!state_) return;
  {
    std::lock_guard<std::mutex> lock(state_->mutex);
    stopLocked("nav2_deactivate"); state_->active=false;
  }
  native_worker_.reset();
}
void Controller::cleanup()
{
  if (!parent_) return;
  deactivate();
  joinStoppedExecutor(executor_,thread_,thread_finished_);
  executor_.reset(); binding_sub_.reset(); spline_sub_.reset(); cancel_sub_.reset();
  safety_sub_.reset(); stopped_sub_.reset(); route_pub_.reset(); binding_ready_pub_.reset(); cancel_pub_.reset(); cancel_admission_pub_.reset(); command_pub_.reset();
  tracker_.reset(); bridge_.reset(); parent_.reset(); state_.reset();
  body_inputs_=scan_input_time::BodyTimeBuffer();last_due_body_.reset();
  pending_.reset(); safety_.reset(); ticket_ready_=false; output_owner_bound_=false;
  candidate_curves_.clear();candidate_proofs_.clear();first_candidate_received_s_=0.0;
}

void Controller::onBinding(scan_planner_msgs::msg::P2BRoute::ConstSharedPtr message)
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (!message->has_goal_pose || !finitePose(message->goal_pose) || message->path.poses.empty() ||
      message->run_id.empty() || message->request_id.empty() || message->goal_id.empty() ||
      message->route_id.empty() || message->command_id.empty() || message->map_epoch.empty() ||
      message->epoch<=0 || message->generation<=0 || message->map_revision<0 ||
      message->path.header.frame_id!=global_frame_) return;
  for (const auto &p:message->path.poses)
    if (p.header.frame_id!=global_frame_ || !finitePose(p.pose)) return;
  if (state_->route && !matches(*state_->route,*message) && !state_->stopped) return;
  if ((!state_->route || !matches(*state_->route,*message)) && message->generation<=generation_high_water_) return;
  if (!fresh(parent_->now().seconds(),stampSeconds(message->path.header.stamp),binding_timeout_s_)) return;
  pending_=message; binding_received_s_=parent_->now().seconds();
  binding_ready_pub_->publish(*message);
}

void Controller::setPlan(const nav_msgs::msg::Path &path)
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  // Foxy's FollowPath may deliver the already admitted path again during an
  // action update. This does not create a new owner or refresh safety evidence.
  if (state_->active && state_->route && !state_->stopping && path==state_->route->path) return;
  if (!state_->active || !pending_ || path!=pending_->path ||
      !fresh(parent_->now().seconds(),binding_received_s_,binding_timeout_s_) ||
      !fresh(parent_->now().seconds(),stampSeconds(path.header.stamp),binding_timeout_s_))
    throw nav2_core::PlannerException("Path lacks a fresh exact P2B binding");
  if (state_->route && matches(*state_->route,*pending_) && !state_->stopping) {
    if (state_->route->goal_pose!=pending_->goal_pose)
      throw nav2_core::PlannerException("Requested goal changed within one identity");
    state_->route=pending_; pending_.reset();
    route_pub_->publish(*state_->route); return;
  }
  if (state_->route && !state_->stopped)
    throw nav2_core::PlannerException("Previous SCAN owner has not physically stopped");
  if (pending_->generation<=generation_high_water_)
    throw nav2_core::PlannerException("SCAN generation cannot be reused");
  state_->route=pending_; pending_.reset();
  generation_high_water_=state_->route->generation;
  state_->stopping=false; state_->stopped=false; state_->stop_requested_s=0;
  safety_.reset(); ticket_ready_=false; tracker_->receive_traj_=false;
  candidate_curves_.clear();candidate_proofs_.clear();first_candidate_received_s_=0.0;
  tracker_->goalCallback(state_->route);
  plan_started_s_=parent_->now().seconds();
  route_pub_->publish(*state_->route);
}

void Controller::onSpline(scan_planner_msgs::msg::Bspline::ConstSharedPtr message)
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (!state_->active || state_->stopping || !state_->route || !matches(*state_->route,*message)) return;
  const auto n=message->pos_pts.size();
  bool valid=message->order==3 && n>=4 && message->knots.size()==n+4 && message->traj_id>0;
  for (const auto &p:message->pos_pts) valid=valid && std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z);
  for (size_t i=0;i<message->knots.size();++i)
    valid=valid && std::isfinite(message->knots[i]) && (i==0 || message->knots[i]>message->knots[i-1]);
  const double origin=stampSeconds(message->start_time), now=parent_->now().seconds();
  valid=valid && origin>0 && origin<=now && message->start_time.nanosec<1000000000u;
  if (valid) valid=now-origin<=message->knots[n]-message->knots[3];
  if(valid && message->reverse_motion) {
    // Only a short, stopped prefix can request reverse body-heading semantics.
    // Ordinary paths retain the original direction contract.
    valid=n>=6 && !message->emergency_stop;
    if(valid) {
      const auto point=[&](size_t i){const auto&p=message->pos_pts[i];return Eigen::Vector3d(p.x,p.y,p.z);};
      double length=0.0;for(size_t i=1;i<n;++i)length+=(point(i)-point(i-1)).norm();
      valid=length<=0.10 && (point(n-1)-point(0)).head<2>().norm()>1e-4;
      for(size_t i=1;i<3;++i)valid=valid && (point(i)-point(0)).norm()<1e-6 && (point(n-1-i)-point(n-1)).norm()<1e-6;
    }
  }
  if (tracker_->receive_traj_ && message->traj_id<=tracker_->traj_id_) return;
  if (!valid) { stopLocked("invalid_scan_spline"); return; }
  if (message->emergency_stop) {stopLocked("scan_emergency_stop");return;}
  if (candidate_curves_.empty()) first_candidate_received_s_=now;
  candidate_curves_[message->traj_id]=message;
  while(candidate_curves_.size()>4)candidate_curves_.erase(candidate_curves_.begin());
  activateProvenCandidate(now);
}

void Controller::onSafety(scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr message)
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (!state_->active || state_->stopping || !state_->route || !matches(*state_->route,message->binding) ||
      message->binding.traj_id<=0 || message->binding.consumer!="native_safety") return;
  if (!std::isfinite(stampSeconds(message->stamp))) { stopLocked("invalid_safety_stamp"); return; }
  if (tracker_->receive_traj_ && message->binding.traj_id==tracker_->traj_id_) {
    if (safety_ && stampSeconds(message->stamp)<=stampSeconds(safety_->stamp)) return;
    // Native negative evidence still revokes. Positive timer messages cannot
    // replace the controller's newer independently checked proof.
    if (!native_worker_ || !message->clear) safety_=message;
    if (!message->clear) stopLocked("scan_safety_rejected");
    return;
  }
  if (tracker_->receive_traj_ && message->binding.traj_id<tracker_->traj_id_) return;
  const auto prior=candidate_proofs_.find(message->binding.traj_id);
  if (prior!=candidate_proofs_.end() && stampSeconds(message->stamp)<=stampSeconds(prior->second->stamp)) return;
  candidate_proofs_[message->binding.traj_id]=message;
  while(candidate_proofs_.size()>4)candidate_proofs_.erase(candidate_proofs_.begin());
  activateProvenCandidate(parent_->now().seconds());
}
void Controller::activateProvenCandidate(double now)
{
  if (state_->stopping) return;
  for(auto candidate=candidate_curves_.rbegin();candidate!=candidate_curves_.rend();++candidate) {
    const auto proof=candidate_proofs_.find(candidate->first);
    if(proof==candidate_proofs_.end())continue;
    if(!proof->second->clear) {
      // Keep the verdict that revoked this owner until a measured-stop handoff.
      safety_=proof->second;
      stopLocked("scan_safety_rejected");return;
    }
    const auto &curve=*candidate->second;
    const double origin=stampSeconds(curve.start_time);
    if(!fresh(now,stampSeconds(proof->second->stamp),safety_timeout_s_) ||
       !fresh(now,proof->second->observation_stamp_s,observation_timeout_s_) ||
       now<origin || now-origin>curve.knots[curve.pos_pts.size()]-curve.knots[3])continue;
    // Both messages bind the same exact owner and trajectory. Preserve their
    // original times; the old executing proof was never refreshed by receipt.
    const auto id=candidate->first;
    tracker_->bsplineCallback(candidate->second);safety_=proof->second;spline_received_s_=now;
    candidate_curves_.erase(candidate_curves_.begin(),candidate_curves_.upper_bound(id));
    candidate_proofs_.erase(candidate_proofs_.begin(),candidate_proofs_.upper_bound(id));
    if(candidate_curves_.empty())first_candidate_received_s_=0.0;
    return;
  }
}
void Controller::onCancel(scan_planner_msgs::msg::P2BCancel::ConstSharedPtr message)
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (pending_ && matches(*pending_,*message)) {
    pending_.reset();
    generation_high_water_=std::max(generation_high_water_,message->generation);
    if (!state_->route || !matches(*state_->route,*message)) {
      scan_planner_msgs::msg::P2BAdmission hold;
      copyIdentity(*message,hold); hold.consumer="controller"; hold.status="stopped";
      hold.hold_confirmed=true; hold.measured_stillness_confirmed=false;
      hold.message="pending_binding_revoked_before_execution";
      cancel_admission_pub_->publish(hold);
    }
  }
  if (state_->route && matches(*state_->route,*message)) {
    if (state_->stopping) {
      // The tracker may never have received a first spline/trajectory identity.
      // This plugin already revoked its output ticket and latched this exact
      // route in stopLocked. A repeated cancel must acknowledge that hold even
      // when the tracker's generation high-water suppresses its second reply.
      scan_planner_msgs::msg::P2BAdmission hold;
      copyIdentity(*state_->route,hold);
      hold.consumer="controller"; hold.status="stopped";
      hold.hold_confirmed=true; hold.measured_stillness_confirmed=false;
      hold.traj_id=tracker_->traj_id_;
      hold.message="bound_controller_output_remains_revoked";
      cancel_admission_pub_->publish(hold);
    }
    else stopLocked(message->reason);
  }
}
void Controller::onStopEvidence(scan_planner_msgs::msg::P2BStopEvidence::ConstSharedPtr message)
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  const auto &a=message->admission;
  const double stamp=stampSeconds(message->stamp);
  if (state_->stopping && state_->route && matches(*state_->route,a) && a.consumer=="controller" &&
      a.status=="stopped" && a.hold_confirmed && a.measured_stillness_confirmed &&
      stamp>=state_->stop_requested_s && fresh(parent_->now().seconds(),stamp,0.2)) state_->stopped=true;
}

geometry_msgs::msg::TwistStamped Controller::ticket(const geometry_msgs::msg::Twist &command)
{
  ticket_.header.frame_id=base_frame_; ticket_.header.stamp=parent_->now(); ticket_.twist=command;
  ticket_identity_=scan_planner_msgs::msg::P2BStampedTwist();
  if (state_->route) copyIdentity(*state_->route,ticket_identity_);
  ticket_identity_.traj_id=tracker_->traj_id_; ticket_identity_.stamp=ticket_.header.stamp;
  ticket_identity_.twist=command; ticket_ready_=true;
  return ticket_;
}

geometry_msgs::msg::TwistStamped Controller::computeVelocityCommands(
  const geometry_msgs::msg::PoseStamped &incoming_pose, const geometry_msgs::msg::Twist &incoming_velocity)
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  auto pose=incoming_pose;
  auto velocity=incoming_velocity;
  if (!state_->active || !state_->route) throw nav2_core::PlannerException("SCAN has no active bound route");
  if (!output_owner_bound_) throw nav2_core::PlannerException("Stock Foxy output is not authorized for SCAN; tagged-output extension required");
  const auto fail=[&](const std::string &reason) {
    stopLocked(reason); throw nav2_core::PlannerException(reason);
  };
  if (native_worker_ && !native_worker_->healthy()) fail("native_planner_worker_failed");
  double now=parent_->now().seconds();
  if (pose.header.frame_id!=global_frame_) fail("scan_body_pose_frame_invalid");
  if (!finitePose(pose.pose) || !finiteTwist(velocity)) fail("scan_body_pose_value_invalid");
  auto incoming=std::make_shared<nav_msgs::msg::Odometry>();
  incoming->header=pose.header;incoming->pose.pose=pose.pose;incoming->twist.twist=velocity;
  const auto decision_time=parent_->now();now=decision_time.seconds();
  const auto source_time=rclcpp::Time(pose.header.stamp);
  const bool future=source_time.nanoseconds()>decision_time.nanoseconds();
  // TF can legitimately answer a historical query. Preserve the ordinary due
  // input path; only future deliveries enter the native ordered source queue.
  if(!body_inputs_.healthy())fail(body_inputs_.error());
  if(future && !body_inputs_.push(incoming))fail(body_inputs_.error());
  if(auto due=body_inputs_.takeDue(decision_time.nanoseconds())) {
    if(!last_due_body_ || rclcpp::Time(due->header.stamp)>rclcpp::Time(last_due_body_->header.stamp))last_due_body_=due;
  }
  if(!future) {
    if(!last_due_body_ || source_time>rclcpp::Time(last_due_body_->header.stamp))last_due_body_=incoming;
  } else if(last_due_body_) {
    pose.header=last_due_body_->header;pose.pose=last_due_body_->pose.pose;
    velocity=last_due_body_->twist.twist;
  }
  const double pose_stamp=stampSeconds(pose.header.stamp);
  if (!fresh(now,pose_stamp,pose_timeout_s_)) {
    RCLCPP_ERROR(parent_->get_logger(),"SCAN body time rejected: now=%.9f source=%.9f age=%.9f limit=%.3f",
      now,pose_stamp,now-pose_stamp,pose_timeout_s_);
    fail(now<pose_stamp?"scan_body_pose_future":"scan_body_pose_stale");
  }
  if(future)RCLCPP_INFO(parent_->get_logger(),
      "V159_DUE_BODY now=%.9f queued_source=%.9f selected_source=%.9f age=%.9f",
      now,source_time.seconds(),pose_stamp,now-pose_stamp);
  const auto stoppedCommand=[&]() {
    // An asynchronous native rejection must fail FollowPath on this tick.
    // Returning normal zeros hides the fault until the progress timeout.
    // Output is already revoked; the existing BT still waits for measured stop.
    if (safety_ && !safety_->clear)
      throw nav2_core::PlannerException("scan_safety_rejected");
    return ticket(geometry_msgs::msg::Twist());
  };
  if (state_->stopping) return stoppedCommand();
  activateProvenCandidate(now);
  if (state_->stopping) return stoppedCommand();
  if (!tracker_->receive_traj_) {
    if (first_candidate_received_s_>0 &&
        !fresh(now,first_candidate_received_s_,safety_timeout_s_)) fail("scan_safety_evidence_stale");
    if (now<plan_started_s_ || now-plan_started_s_>startup_timeout_s_) fail("scan_trajectory_missing");
    return ticket(geometry_msgs::msg::Twist());
  }
  if (native_worker_) {
    auto proof=std::make_shared<scan_planner_msgs::msg::P2BExecutionSafety>(
      native_worker_->validate(parent_->get_clock(),pose,tracker_->traj_.at(0),tracker_->exec_time_));
    copyIdentity(*state_->route,proof->binding);proof->binding.traj_id=tracker_->traj_id_;
    proof->binding.consumer="native_safety";proof->binding.status=proof->clear?"clear":"blocked";
    safety_=proof;now=parent_->now().seconds();
    if(!proof->clear)RCLCPP_ERROR(parent_->get_logger(),"Controller native validation rejected: %s",proof->binding.message.c_str());
  }
  if (!safety_ && now>=spline_received_s_ && now-spline_received_s_<=safety_timeout_s_)
    return ticket(geometry_msgs::msg::Twist());
  if (!safety_ || !safety_->clear || !fresh(now,stampSeconds(safety_->stamp),safety_timeout_s_) ||
      !fresh(now,safety_->observation_stamp_s,observation_timeout_s_)) {
    RCLCPP_ERROR(parent_->get_logger(),
      "SCAN evidence rejected now=%.9f active=%lld proof=%lld clear=%d proof_stamp=%.9f proof_age=%.9f observation_stamp=%.9f observation_age=%.9f pending_curves=%zu pending_proofs=%zu",
      now,static_cast<long long>(tracker_->traj_id_),safety_?static_cast<long long>(safety_->binding.traj_id):-1LL,
      safety_ && safety_->clear,safety_?stampSeconds(safety_->stamp):0.0,
      safety_?now-stampSeconds(safety_->stamp):-1.0,safety_?safety_->observation_stamp_s:0.0,
      safety_?now-safety_->observation_stamp_s:-1.0,candidate_curves_.size(),candidate_proofs_.size());
    fail("scan_safety_evidence_stale");
  }
  if (atGoal(pose.pose,*state_,0.5)) {
    stopLocked("requested_goal_reached"); return ticket(geometry_msgs::msg::Twist());
  }
  const auto command=tracker_->sample(pose);
  if (!finiteTwist(command)) fail("scan_nonfinite_command");
  const auto output=ticket(command);ticket_body_stamp_s_=pose_stamp;return output;
}

void Controller::bindOutputOwner()
{
  std::lock_guard<std::mutex> lock(state_->mutex); output_owner_bound_=true;
}

void Controller::publishCommand(const geometry_msgs::msg::TwistStamped &command)
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (!state_->active || !ticket_ready_ || command!=ticket_) {
    stopLocked("nav2_command_ticket_mismatch"); return;
  }
  const double now=parent_->now().seconds();
  const bool superseded=ticket_identity_.traj_id!=tracker_->traj_id_;
  if (!fresh(now,stampSeconds(ticket_.header.stamp),pose_timeout_s_) ||
      (!superseded && command.twist!=geometry_msgs::msg::Twist() &&
       (!fresh(now,ticket_body_stamp_s_,pose_timeout_s_) ||
        !safety_ || !safety_->clear || !fresh(now,stampSeconds(safety_->stamp),safety_timeout_s_) ||
        !fresh(now,safety_->observation_stamp_s,observation_timeout_s_)))) {
    stopLocked("nav2_command_evidence_expired"); return;
  }
  ticket_ready_=false;
  if (superseded) {
    // Never publish a nonzero command sampled from the replaced trajectory.
    // The next control tick must obtain the new trajectory's own fresh proof.
    scan_planner_msgs::msg::P2BStampedTwist zero;
    copyIdentity(*state_->route,zero);zero.traj_id=tracker_->traj_id_;zero.stamp=parent_->now();
    command_pub_->publish(zero);
    return;
  }
  if (state_->stopping) ticket_identity_.twist=geometry_msgs::msg::Twist();
  command_pub_->publish(ticket_identity_);
}
void Controller::stop(const std::string &reason)
{
  if (!state_) return;
  std::lock_guard<std::mutex> lock(state_->mutex); stopLocked(reason);
}
void Controller::stopLocked(const std::string &reason)
{
  ticket_ready_=false;
  if (!state_->route) return;
  scan_planner_msgs::msg::P2BStampedTwist zero;
  copyIdentity(*state_->route,zero); zero.traj_id=tracker_->traj_id_; zero.stamp=parent_->now();
  command_pub_->publish(zero);
  if (state_->stopping) return;
  candidate_curves_.clear();candidate_proofs_.clear();first_candidate_received_s_=0.0;
  RCLCPP_WARN(parent_->get_logger(), "SCAN output revoked reason=%s trajectory=%lld",
    reason.c_str(), static_cast<long long>(tracker_->traj_id_));
  state_->stopping=true; state_->stopped=false; state_->stop_requested_s=parent_->now().seconds();
  auto cancel=std::make_shared<scan_planner_msgs::msg::P2BCancel>();
  copyIdentity(*state_->route,*cancel); cancel->reason=reason;
  tracker_->p2bCancelCallback(cancel);
  cancel_pub_->publish(*cancel);
}

void GoalChecker::initialize(const rclcpp_lifecycle::LifecycleNode::SharedPtr &parent,
  const std::string &name)
{
  state_=sharedState(parent,parameter(parent,name+".controller_plugin",std::string("SCAN")));
}
void GoalChecker::reset() { /* A Nav2 path reset must not clear ownership or physical-stop evidence. */ }
bool GoalChecker::isGoalReached(const geometry_msgs::msg::Pose &query,
  const geometry_msgs::msg::Pose &, const geometry_msgs::msg::Twist &velocity)
{
  if (!state_) return false;
  std::lock_guard<std::mutex> lock(state_->mutex);
  return state_->active && state_->stopping && state_->stopped && finiteTwist(velocity) && atGoal(query,*state_);
}
}  // namespace scan_nav2_controller

PLUGINLIB_EXPORT_CLASS(scan_nav2_controller::Controller, nav2_core::Controller)
PLUGINLIB_EXPORT_CLASS(scan_nav2_controller::GoalChecker, nav2_core::GoalChecker)

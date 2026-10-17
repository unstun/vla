#include <scan_nav2_controller/controller.hpp>
#include <scan_nav2_controller/executor_shutdown.hpp>
#include <rclcpp/scope_exit.hpp>


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
  NativeWorker(const std::string &config, bool use_sim_time, const std::string &route_topic,
               std::function<void(const std::string &)> fault) {
    if (!std::filesystem::is_regular_file(config))
      throw nav2_core::PlannerException("Native SCAN parameter file is required");
    rclcpp::NodeOptions options;
    options.use_global_arguments(false);
    options.arguments({"--ros-args", "-r", "sensor_pose:=/quad_0/lidar_pose",
                       "-r", "initial_path:=" + route_topic});
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
      return p.get_name()=="use_sim_time" || p.get_name()=="fsm.navi_mode";
    }),parameters.end());
    parameters.emplace_back("use_sim_time",use_sim_time);
    parameters.emplace_back("fsm.navi_mode",3);
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
bool finitePose(const geometry_msgs::msg::Pose &p)
{
  return scan_planner::TrackingNode::validGoalPose(p);
}
bool finiteTwist(const geometry_msgs::msg::Twist &t)
{
  return std::isfinite(t.linear.x) && std::isfinite(t.linear.y) && std::isfinite(t.linear.z) &&
    std::isfinite(t.angular.x) && std::isfinite(t.angular.y) && std::isfinite(t.angular.z);
}
bool stoppedVelocity(const geometry_msgs::msg::Twist &t)
{
  return finiteTwist(t) && std::hypot(std::hypot(t.linear.x, t.linear.y), t.linear.z) <= 0.03 &&
    std::hypot(std::hypot(t.angular.x, t.angular.y), t.angular.z) <= 0.05;
}
bool validSplineLayout(const scan_planner_msgs::msg::Bspline &m)
{
  if (m.order != 3 || m.start_time.sec < 0 || m.start_time.nanosec >= 1000000000u) return false;
  Eigen::MatrixXd points(3, m.pos_pts.size());
  Eigen::VectorXd knots(m.knots.size());
  for (size_t i=0; i<m.pos_pts.size(); ++i)
    points.col(i) << m.pos_pts[i].x, m.pos_pts[i].y, m.pos_pts[i].z;
  for (size_t i=0; i<m.knots.size(); ++i) knots(i)=m.knots[i];
  return reactive_stair::validSplineLayout(points, knots, 3);
}
template<class T> T parameter(const rclcpp_lifecycle::LifecycleNode::SharedPtr &node,
  const std::string &name, const T &fallback)
{
  if (!node->has_parameter(name)) node->declare_parameter<T>(name, fallback);
  return node->get_parameter(name).get_value<T>();
}
std::shared_ptr<State> sharedState(const rclcpp_lifecycle::LifecycleNode::SharedPtr &node,
  const std::string &name)
{
  static std::mutex mutex;
  static std::map<std::pair<const void *, std::string>, std::weak_ptr<State>> states;
  std::lock_guard<std::mutex> lock(mutex);
  const auto key=std::make_pair(static_cast<const void *>(node.get()), name);
  auto result=states[key].lock();
  if (!result) { result=std::make_shared<State>(); states[key]=result; }
  return result;
}
}  // namespace

Controller::Controller() = default;
Controller::~Controller() { cleanup(); }

void Controller::configure(const rclcpp_lifecycle::LifecycleNode::SharedPtr &parent,
  std::string name, const std::shared_ptr<tf2_ros::Buffer> &,
  const std::shared_ptr<nav2_costmap_2d::Costmap2DROS> &costmap)
{
  if (parent_) throw nav2_core::PlannerException("SCAN plugin is already configured");
  parent_=parent; name_=std::move(name); state_=sharedState(parent_, name_);
  global_frame_=parameter(parent_, name_+".global_frame", std::string("world"));
  base_frame_=parameter(parent_, name_+".base_frame", std::string("base_link"));
  if (costmap && (costmap->getGlobalFrameID()!=global_frame_ || costmap->getBaseFrameID()!=base_frame_))
    throw nav2_core::PlannerException("SCAN and Nav2 frame configuration disagree");
  bspline_timeout_s_=parameter(parent_, name_+".bspline_timeout", 5.0);
  if (!std::isfinite(bspline_timeout_s_) || bspline_timeout_s_ <= 0.0)
    throw nav2_core::PlannerException("Invalid SCAN B-spline timeout");
  state_->completion.hold_s=parameter(parent_, name_+".stand_hold_seconds", 2.0);
  state_->completion.timeout_s=parameter(parent_, name_+".stand_timeout_seconds", 10.0);
  state_->completion.max_gap_s=parameter(parent_, name_+".execution_max_age_seconds", 0.25);
  if (!std::isfinite(state_->completion.hold_s) || state_->completion.hold_s<=0 ||
      !std::isfinite(state_->completion.timeout_s) || state_->completion.timeout_s<=state_->completion.hold_s ||
      !std::isfinite(state_->completion.max_gap_s) || state_->completion.max_gap_s<=0)
    throw nav2_core::PlannerException("Invalid terminal completion timing");
  native_worker_enabled_=parameter(parent_, name_+".native_worker_enabled", true);
  const bool use_sim=parameter(parent_, "use_sim_time", false);
  rclcpp::NodeOptions options;
  options.use_global_arguments(false);
  std::vector<rclcpp::Parameter> parameters;
  const std::vector<std::pair<std::string, double>> defaults={
    {"time_forward",0.8},{"heading_error_threshold",0.8},{"kp_pos",0.8},{"kp_yaw",1.5},
    {"max_vx",0.75},{"max_vy",0.35},{"max_vyaw",1.0},{"finish_dist",0.15},
    {"goal_xy_tolerance",0.25},{"goal_z_tolerance",0.20},{"goal_yaw_tolerance",0.25},
    {"route_lookahead_dist",0.5}};
  for (const auto &entry: defaults) {
    const double value=parameter(parent_, name_+"."+entry.first, entry.second);
    if (!std::isfinite(value) || value<=0) throw nav2_core::PlannerException("Invalid tracking parameter");
    parameters.emplace_back(entry.first, value);
  }
  parameters.emplace_back("use_sim_time", use_sim);
  parameters.emplace_back("route_lookahead_heading_enabled",
    parameter(parent_, name_+".route_lookahead_heading_enabled", false));
  options.parameter_overrides(parameters);
  options.arguments({"--ros-args", "-r", "planning/go2_execution_frozen:="+
    parameter(parent_, name_+".execution_frozen_topic", std::string("/quad_0/planning/go2_execution_frozen"))});
  tracker_=std::make_shared<scan_planner::TrackingNode>(options);
  state_->xy_tolerance=tracker_->goal_xy_tolerance_;
  state_->z_tolerance=tracker_->goal_z_tolerance_;
  state_->yaw_tolerance=tracker_->goal_yaw_tolerance_;
  // Enter braking inside the inner band; the goal checker retains the outer band.
  tracker_->goal_yaw_tolerance_ *= 0.5;
  rclcpp::NodeOptions bridge_options;
  bridge_options.use_global_arguments(false);
  bridge_options.parameter_overrides({rclcpp::Parameter("use_sim_time", use_sim)});
  bridge_=std::make_shared<rclcpp::Node>("scan_nav2_"+name_, bridge_options);
  route_topic_=parameter(parent_, name_+".route_topic", std::string("/pct_path"));
  route_pub_=bridge_->create_publisher<nav_msgs::msg::Path>(
    route_topic_, rclcpp::QoS(1).reliable().transient_local());
  spline_sub_=bridge_->create_subscription<scan_planner_msgs::msg::Bspline>(
    parameter(parent_, name_+".spline_topic", std::string("/quad_0/planning/bspline")), 10,
    std::bind(&Controller::onSpline, this, std::placeholders::_1));
  execution_sub_=bridge_->create_subscription<lite3_nav2_interfaces::msg::RobotExecutionState>(
    parameter(parent_, name_+".execution_state_topic", std::string("/quad_0/execution_state")), 10,
    std::bind(&Controller::onExecution, this, std::placeholders::_1));
  executor_=std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
  executor_->add_node(bridge_);
  executor_->add_node(tracker_);
}

void Controller::activate()
{
  if (!state_) throw nav2_core::PlannerException("SCAN plugin is not configured");
  if (native_worker_enabled_ && !native_worker_)
    native_worker_=std::make_unique<NativeWorker>(
      parameter(parent_, name_+".native_planner_config", std::string("")),
      parameter(parent_, "use_sim_time", false), route_topic_,
      [this](const std::string &reason) { stop(reason); });
  std::lock_guard<std::mutex> lock(state_->mutex);
  state_->active=true;
}

void Controller::deactivate()
{
  if (!state_) return;
  stop("nav2_deactivate");
  { std::lock_guard<std::mutex> lock(state_->mutex); state_->active=false; }
  native_worker_.reset();
}

void Controller::cleanup()
{
  if (!parent_) return;
  deactivate();
  executor_.reset(); spline_sub_.reset(); execution_sub_.reset(); route_pub_.reset();
  tracker_.reset(); bridge_.reset(); parent_.reset(); state_.reset();
}

void Controller::setPlan(const nav_msgs::msg::Path &path)
{
  if (path.poses.empty()) throw nav2_core::PlannerException("Path is empty");
  if (path.header.frame_id != global_frame_) throw nav2_core::PlannerException("Path frame mismatch");
  for (const auto &p: path.poses)
    if ((!p.header.frame_id.empty() && p.header.frame_id != global_frame_) || !finitePose(p.pose))
      throw nav2_core::PlannerException("Path has an invalid pose or frame");
  std::lock_guard<std::mutex> lock(state_->mutex);
  const bool same_goal=has_active_plan_ && state_->has_goal_pose &&
    state_->goal_pose == path.poses.back().pose;
  if (!same_goal) {
    state_->completion.resetGoal();
    tracker_->clearTrajectory();
    waiting_for_spline_=true;
    waiting_for_spline_since_=parent_->now();
    route_sent_at_=waiting_for_spline_since_;
    state_->goal_reached=false;
    goal_braking_=false;
    state_->stopped=false;
  } else if (!tracker_->haveTrajectory() && !waiting_for_spline_) {
    waiting_for_spline_=true;
    waiting_for_spline_since_=parent_->now();
    route_sent_at_=waiting_for_spline_since_;
  }
  const bool same_geometry = same_goal && path.poses.size() == last_published_path_.poses.size() &&
    std::equal(path.poses.begin(), path.poses.end(), last_published_path_.poses.begin(),
      [](const auto &a, const auto &b) { return a.pose == b.pose; });
  const bool publish_route = !same_geometry || !tracker_->haveTrajectory() || waiting_for_spline_;
  tracker_->setReferencePath(path);
  has_active_plan_=true;
  terminal_timeout_started_=false;
  state_->active=true;
  state_->has_goal_pose=true; state_->goal_pose=path.poses.back().pose;
  if (publish_route) {
    route_pub_->publish(path);
    last_published_path_ = path;
  }
}

void Controller::onSpline(scan_planner_msgs::msg::Bspline::ConstSharedPtr message)
{
  if (!message || message->order != 3 || !validSplineLayout(*message)) return;
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (!has_active_plan_) return;
  if (message->emergency_stop) {
    if (tracker_->haveTrajectory() || !waiting_for_spline_) {
      waiting_for_spline_=true;
      waiting_for_spline_since_=parent_->now();
      route_sent_at_=waiting_for_spline_since_;
    }
    tracker_->clearTrajectory();
    terminal_timeout_started_=false;
    return;
  }
  tracker_->bsplineCallback(message);
  waiting_for_spline_=false;
  terminal_timeout_started_=false;
}

void Controller::onExecution(lite3_nav2_interfaces::msg::RobotExecutionState::ConstSharedPtr message)
{
  if (!message || message->header.frame_id!=base_frame_ || message->header.stamp.sec<0 ||
      message->header.stamp.nanosec>=1000000000u ||
      static_cast<uint64_t>(message->header.stamp.sec)*1000000000ULL+
        message->header.stamp.nanosec!=message->simulation_time_ns) return;
  std::lock_guard<std::mutex> lock(state_->mutex);
  state_->completion.observe(*message);
}
bool Controller::terminalPhase() const
{
  if (!state_) return false;
  std::lock_guard<std::mutex> lock(state_->mutex);
  return state_->active && state_->has_goal_pose && state_->completion.waiting();
}

void Controller::spinBridge()
{
  if (executor_) executor_->spin_some();
}
void Controller::serviceNativeWork()
{
  // Native callbacks run on their own serialized executor, including Path intake.
  if (native_worker_ && !native_worker_->healthy()) {
    stop("native_planner_worker_failed");
    throw nav2_core::PlannerException("Native SCAN worker failed");
  }
}
bool Controller::withinGoalPosition(const geometry_msgs::msg::Pose &pose) const
{
  const auto &g=state_->goal_pose.position;
  return state_->has_goal_pose && std::hypot(pose.position.x-g.x, pose.position.y-g.y)<=state_->xy_tolerance &&
    std::abs(pose.position.z-g.z)<=state_->z_tolerance;
}
bool Controller::withinGoalYaw(const geometry_msgs::msg::Pose &pose, bool braking) const
{
  return state_->has_goal_pose && std::abs(scan_planner::TrackingNode::normalizeAngle(
    tf2::getYaw(state_->goal_pose.orientation)-tf2::getYaw(pose.orientation)))<=
    (braking ? state_->yaw_tolerance : tracker_->goal_yaw_tolerance_);
}
geometry_msgs::msg::TwistStamped Controller::stampedCommand(const geometry_msgs::msg::Twist &command)
{
  geometry_msgs::msg::TwistStamped result;
  result.header.frame_id=base_frame_; result.header.stamp=parent_->now(); result.twist=command;
  return result;
}

geometry_msgs::msg::TwistStamped Controller::computeVelocityCommands(
  const geometry_msgs::msg::PoseStamped &pose, const geometry_msgs::msg::Twist &velocity)
{
  return computeVelocityCommands(pose, velocity, nullptr);
}
geometry_msgs::msg::TwistStamped Controller::computeVelocityCommands(
  const geometry_msgs::msg::PoseStamped &pose, const geometry_msgs::msg::Twist &velocity,
  nav2_core::GoalChecker *)
{
  spinBridge();
  serviceNativeWork();
  std::unique_lock<std::mutex> lock(state_->mutex);
  if (!has_active_plan_) throw nav2_core::PlannerException("No active plan");
  if (pose.header.frame_id != global_frame_ || !finitePose(pose.pose) || !finiteTwist(velocity)) {
    throw nav2_core::PlannerException("Invalid controller pose, velocity or frame");
  }
  state_->pose=pose.pose; state_->velocity=velocity; state_->pose_valid=true;
  state_->stopped=stoppedVelocity(velocity);
  goal_braking_=withinGoalPosition(pose.pose) && withinGoalYaw(pose.pose, goal_braking_);
  state_->goal_reached=goal_braking_;
  state_->completion.updatePose(goal_braking_, parent_->now().nanoseconds());
  if (state_->goal_reached) {
    if (state_->completion.timedOut() &&
        !(state_->stopped && state_->completion.ready(parent_->now().nanoseconds())))
      throw nav2_core::PlannerException("terminal_settle_timeout");
    return stampedCommand(geometry_msgs::msg::Twist());
  }
  if (!tracker_->haveTrajectory()) {
    if (!waiting_for_spline_) {
      waiting_for_spline_=true;
      waiting_for_spline_since_=parent_->now();
      route_sent_at_=waiting_for_spline_since_;
    }
    if ((parent_->now()-waiting_for_spline_since_).seconds() > bspline_timeout_s_) {
      lock.unlock();  // stop() acquires the same state mutex.
      stop("scan_bspline_timeout");
      throw nav2_core::PlannerException("Native SCAN did not publish a trajectory before timeout");
    }
    return stampedCommand(geometry_msgs::msg::Twist());
  }
  const auto sample=tracker_->sampleCommand(pose.pose, velocity, true);
  if (!sample.valid || !finiteTwist(sample.twist)) {
    lock.unlock();
    stop("scan_invalid_command");
    throw nav2_core::PlannerException("Native SCAN trajectory sample invalid");
  }
  return stampedCommand(sample.twist);
}

void Controller::stop(const std::string &reason)
{
  if (!state_) return;
  std::lock_guard<std::mutex> lock(state_->mutex);
  has_active_plan_=false;
  state_->completion.resetGoal();
  goal_braking_=false;
  waiting_for_spline_=false;
  terminal_timeout_started_=false;
  state_->goal_reached=false;
  state_->has_goal_pose=false;
  state_->stopped=false;
  if (tracker_) tracker_->clearTrajectory();
  RCLCPP_DEBUG(parent_->get_logger(), "SCAN stopped: %s", reason.c_str());
}

void GoalChecker::initialize(const rclcpp_lifecycle::LifecycleNode::SharedPtr &parent,
  const std::string &name)
{
  state_=sharedState(parent, parameter(parent, name+".controller_plugin", std::string("SCAN")));
  clock_=parent->get_clock();
}
void GoalChecker::reset()
{
  if (state_) { std::lock_guard<std::mutex> lock(state_->mutex); state_->goal_reached=false; }
}
bool GoalChecker::isGoalReached(const geometry_msgs::msg::Pose &query,
  const geometry_msgs::msg::Pose &, const geometry_msgs::msg::Twist &velocity)
{
  if (!state_) return false;
  std::lock_guard<std::mutex> lock(state_->mutex);
  const auto &g=state_->goal_pose.position;
  return state_->active && state_->has_goal_pose && state_->goal_reached && state_->stopped &&
    state_->completion.ready(clock_->now().nanoseconds()) &&
    finitePose(query) && stoppedVelocity(velocity) &&
    std::hypot(query.position.x-g.x,query.position.y-g.y)<=state_->xy_tolerance &&
    std::abs(query.position.z-g.z)<=state_->z_tolerance &&
    std::abs(scan_planner::TrackingNode::normalizeAngle(
      tf2::getYaw(state_->goal_pose.orientation)-tf2::getYaw(query.orientation)))<=state_->yaw_tolerance;
}
}  // namespace scan_nav2_controller

PLUGINLIB_EXPORT_CLASS(scan_nav2_controller::Controller, nav2_core::Controller)
PLUGINLIB_EXPORT_CLASS(scan_nav2_controller::GoalChecker, nav2_core::GoalChecker)

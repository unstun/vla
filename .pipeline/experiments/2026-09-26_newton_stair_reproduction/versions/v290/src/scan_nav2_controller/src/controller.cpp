#include <scan_nav2_controller/controller.hpp>
#include <scan_nav2_controller/tracking_node.hpp>

#include <map>
#include <nav2_core/exceptions.hpp>
#include <pluginlib/class_list_macros.hpp>

namespace scan_nav2_controller
{
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
  state_->completion.hold_s=parameter(parent_, name_+".stand_hold_seconds", 2.0);
  state_->completion.timeout_s=parameter(parent_, name_+".stand_timeout_seconds", 10.0);
  state_->completion.max_gap_s=parameter(parent_, name_+".execution_max_age_seconds", 0.25);
  if (!std::isfinite(state_->completion.hold_s) || state_->completion.hold_s<=0 ||
      !std::isfinite(state_->completion.timeout_s) || state_->completion.timeout_s<=state_->completion.hold_s ||
      !std::isfinite(state_->completion.max_gap_s) || state_->completion.max_gap_s<=0)
    throw nav2_core::PlannerException("Invalid terminal completion timing");
  const bool use_sim=parameter(parent_,"use_sim_time",false);
  rclcpp::NodeOptions bridge_options;
  bridge_options.use_global_arguments(false);
  bridge_options.parameter_overrides({rclcpp::Parameter("use_sim_time", use_sim)});
  bridge_=std::make_shared<rclcpp::Node>("scan_nav2_"+name_, bridge_options);
  motion_=std::make_unique<LocalMotion>(parent_,bridge_,name_);
  const auto tolerances=motion_->tolerances();
  state_->xy_tolerance=tolerances.xy;state_->z_tolerance=tolerances.z;state_->yaw_tolerance=tolerances.yaw;
  execution_sub_=bridge_->create_subscription<lite3_nav2_interfaces::msg::RobotExecutionState>(
    parameter(parent_, name_+".execution_state_topic", std::string("/quad_0/execution_state")), 10,
    std::bind(&Controller::onExecution, this, std::placeholders::_1));
  executor_=std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
  executor_->add_node(bridge_);
}

void Controller::activate()
{
  if (!state_ || !motion_) throw nav2_core::PlannerException("SCAN plugin is not configured");
  motion_->activate();
  std::lock_guard<std::mutex> lock(state_->mutex);
  state_->active=true;
}

void Controller::deactivate()
{
  if (!state_) return;
  stop("nav2_deactivate");
  { std::lock_guard<std::mutex> lock(state_->mutex); state_->active=false; }
  if (motion_) motion_->deactivate();
}

void Controller::cleanup()
{
  if (!parent_) return;
  deactivate();
  executor_.reset(); execution_sub_.reset(); motion_.reset();
  bridge_.reset(); parent_.reset(); state_.reset();
}

void Controller::setPlan(const nav_msgs::msg::Path &path)
{
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (!motion_->setRoute(path)) {
    state_->completion.resetGoal();state_->goal_reached=false;goal_braking_=false;state_->stopped=false;
  }
  state_->active=true;state_->has_goal_pose=true;state_->goal_pose=path.poses.back().pose;
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
    (braking ? state_->yaw_tolerance : state_->yaw_tolerance*0.5);
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
  std::unique_lock<std::mutex> lock(state_->mutex);
  try { motion_->update(); }
  catch (...) {
    lock.unlock(); stop("native_planner_worker_failed"); throw;
  }
  if (!motion_->hasRoute()) throw nav2_core::PlannerException("No active plan");
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
      throw TerminalSettleTimeout();
    return stampedCommand(motion_->brakeCommand());
  }
  try { return stampedCommand(motion_->command(pose.pose,velocity)); }
  catch (...) {
    lock.unlock(); stop("scan_command_failed"); throw;
  }
}

void Controller::stop(const std::string &reason)
{
  if (!state_) return;
  std::lock_guard<std::mutex> lock(state_->mutex);
  if (motion_) motion_->cancel();
  state_->completion.resetGoal();
  goal_braking_=false;
  state_->goal_reached=false;
  state_->has_goal_pose=false;
  state_->stopped=false;
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

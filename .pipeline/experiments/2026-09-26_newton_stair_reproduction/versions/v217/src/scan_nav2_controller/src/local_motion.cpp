#include <scan_nav2_controller/local_motion.hpp>
#include <scan_nav2_controller/tracking_node.hpp>
#include <scan_nav2_controller/executor_shutdown.hpp>
#include <rclcpp/scope_exit.hpp>
#include <filesystem>
#include <rclcpp/parameter_map.hpp>
#include <rcl_yaml_param_parser/parser.h>
#include <plan_manage/scan_replan_fsm.h>
#include <nav2_core/exceptions.hpp>

namespace scan_nav2_controller
{
class NativeWorker
{
public:
  NativeWorker(const std::string &config, bool use_sim_time, std::shared_ptr<MotionExchange> exchange) {
    exchange_=std::move(exchange);
    if (!std::filesystem::is_regular_file(config))
      throw nav2_core::PlannerException("Native SCAN parameter file is required");
    rclcpp::NodeOptions options;
    options.use_global_arguments(false);
    options.arguments({"--ros-args", "-r", "sensor_pose:=/quad_0/lidar_pose"});
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
    scan_planner::SCANReplanFSM::DirectIO direct;
    direct.before_work=[this] { consumeInput(); };
    direct.spline=[this](const scan_planner_msgs::msg::Bspline &spline) {
      exchange_->publish(current_generation_,spline);
    };
    planner_->init(node_.get(),work_group_,std::move(direct));
    // Foxy schedules /clock in the default callback group. Keep native data and
    // planning serialized, while its real ROS clock can progress during a solve.
    if (isolated_clock)
      executor_=std::make_shared<rclcpp::executors::MultiThreadedExecutor>(rclcpp::ExecutorOptions(),2);
    else executor_=std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
    executor_->add_node(node_);
    worker_=std::thread([this] {
      RCLCPP_SCOPE_EXIT(finished_.store(true););
      try { executor_->spin(); }
      catch (const std::exception &error) { healthy_=false; RCLCPP_ERROR(node_->get_logger(),"Native worker: %s",error.what()); }
      catch (...) { healthy_=false; RCLCPP_ERROR(node_->get_logger(),"Native worker unknown exception"); }
    });
  }
  bool healthy() const { return healthy_.load(); }
  ~NativeWorker() {
    joinStoppedExecutor(executor_,worker_,finished_);
    planner_.reset();
  }
private:
  void consumeInput() {
    const auto input=exchange_->input();
    if (input.revision!=input_revision_) {
      if (input.reset!=reset_revision_) planner_->cancelReference();
      current_generation_=input.generation;
      input_revision_=input.revision; reset_revision_=input.reset;
      if (input.route) planner_->setReferencePath(input.route);
      exchange_->applied_revision.store(input.revision);
    }
    planner_->setExecutionFeedback(input.feedback.frozen,input.feedback.trajectory);
  }
  std::shared_ptr<MotionExchange> exchange_;
  uint64_t current_generation_{0},input_revision_{0},reset_revision_{0};
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
}  // namespace

LocalMotion::LocalMotion(rclcpp_lifecycle::LifecycleNode::SharedPtr parent,
    rclcpp::Node::SharedPtr observations,const std::string &name)
  : parent_(std::move(parent)),observations_(std::move(observations)),name_(name)
{
  global_frame_=parameter(parent_,name_+".global_frame",std::string("world"));
  bspline_timeout_s_=parameter(parent_,name_+".bspline_timeout",5.0);
  trajectory_starvation_timeout_s_=parameter(parent_,name_+".trajectory_starvation_timeout",0.75);
  if (!std::isfinite(bspline_timeout_s_) || bspline_timeout_s_<=0 ||
      !std::isfinite(trajectory_starvation_timeout_s_) || trajectory_starvation_timeout_s_<=0)
    throw nav2_core::PlannerException("Invalid SCAN B-spline timeout");
  native_worker_enabled_=parameter(parent_, name_+".native_worker_enabled", true);
  const bool use_sim=parameter(parent_, "use_sim_time", false);
  rclcpp::NodeOptions options;
  options.use_global_arguments(false);
  std::vector<rclcpp::Parameter> parameters;
  const std::vector<std::pair<std::string, double>> defaults={
    {"time_forward",0.8},{"heading_error_threshold",1.0},{"heading_resume_threshold",0.6},
    {"linear_acceleration",1.0},{"linear_deceleration",2.0},
    {"angular_acceleration",2.0},{"angular_deceleration",3.0},
    {"expired_min_walk_speed",0.20},{"kp_pos",0.8},{"kp_yaw",1.5},
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
  tolerances_={tracker_->goal_xy_tolerance_,tracker_->goal_z_tolerance_,tracker_->goal_yaw_tolerance_};
  // Enter braking inside the inner band; the goal checker retains the outer band.
  tracker_->goal_yaw_tolerance_ *= 0.5;
  route_topic_=parameter(parent_,name_+".route_topic",std::string("/pct_path"));
  route_pub_=observations_->create_publisher<nav_msgs::msg::Path>(
    route_topic_,rclcpp::QoS(1).reliable().transient_local());
  executor_=std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
  executor_->add_node(tracker_);
}
LocalMotion::~LocalMotion() {deactivate();}
void LocalMotion::activate()
{
  if (native_worker_enabled_ && !native_worker_)
    native_worker_=std::make_unique<NativeWorker>(
      parameter(parent_,name_+".native_planner_config",std::string("")),
      parameter(parent_,"use_sim_time",false),exchange_);
}
void LocalMotion::deactivate() {cancel();native_worker_.reset();}
void LocalMotion::cancel()
{
  exchange_->cancel();has_active_plan_=false;waiting_for_spline_=false;
  received_spline_=false;
  tracker_->clearTrajectory();
}
bool LocalMotion::setRoute(const nav_msgs::msg::Path &path)
{
  if (path.poses.empty()) throw nav2_core::PlannerException("Path is empty");
  if (path.header.frame_id!=global_frame_) throw nav2_core::PlannerException("Path frame mismatch");
  for (const auto &p:path.poses)
    if ((!p.header.frame_id.empty() && p.header.frame_id!=global_frame_) ||
        !scan_planner::TrackingNode::validGoalPose(p.pose))
      throw nav2_core::PlannerException("Path has an invalid pose or frame");
  const bool same_goal=has_active_plan_ && reference_path_.poses.back().pose==path.poses.back().pose;
  const bool same_geometry=same_goal && path.poses.size()==reference_path_.poses.size() &&
    std::equal(path.poses.begin(),path.poses.end(),reference_path_.poses.begin(),
      [](const auto &a,const auto &b){return a.pose==b.pose;});
  if (!same_goal) {
    received_spline_=false;
    tracker_->clearTrajectory();waiting_for_spline_=true;waiting_for_spline_since_=parent_->now();
  } else if (!tracker_->haveTrajectory() && !waiting_for_spline_) {
    waiting_for_spline_=true;waiting_for_spline_since_=parent_->now();
  }
  const bool submit=!same_geometry || !tracker_->haveTrajectory() || waiting_for_spline_;
  tracker_->setReferencePath(path);reference_path_=path;has_active_plan_=true;
  if (submit) {
    generation_=exchange_->setRoute(path,!same_goal);
    route_pub_->publish(path); // Observation; SCAN consumes the snapshot above.
  }
  return same_goal;
}
void LocalMotion::acceptSpline(const MotionExchange::Output &output)
{
  const auto &message=output.spline;
  if (!has_active_plan_ || output.generation!=generation_ || !message || !validSplineLayout(*message)) return;
  if (message->emergency_stop) {
    if (!waiting_for_spline_) {
      waiting_for_spline_=true;waiting_for_spline_since_=parent_->now();
    }
    tracker_->clearTrajectory();return;
  }
  tracker_->bsplineCallback(message);waiting_for_spline_=false;received_spline_=true;
}
void LocalMotion::update()
{
  executor_->spin_some(); // Tracker clock, never route/spline/freeze subscriptions.
  if (native_worker_ && !native_worker_->healthy()) {
    cancel();throw nav2_core::PlannerException("Native SCAN worker failed");
  }
  const auto output=exchange_->take();
  if (output) acceptSpline(*output);
}
geometry_msgs::msg::Twist LocalMotion::brakeCommand()
{
  if (!tracker_->haveTrajectory()) { tracker_->hardStop(); return {}; }
  tracker_->publishExecutionFrozen(true);
  tracker_->publishStop();
  exchange_->feedback(generation_,true,tracker_->traj_id_);
  return tracker_->sampled_command_;
}
void LocalMotion::waitForExecutableSpline()
{
  if (!waiting_for_spline_) {
    waiting_for_spline_=true;waiting_for_spline_since_=parent_->now();
  }
  const double elapsed=(parent_->now()-waiting_for_spline_since_).seconds();
  // Initial map/reference admission keeps its original budget. Once moving,
  // a missing or expired curve is a local failure, not a new initialization.
  const double limit=received_spline_ ? trajectory_starvation_timeout_s_ : bspline_timeout_s_;
  if (elapsed>limit) {
    RCLCPP_WARN(parent_->get_logger(),
      "local_trajectory_starvation elapsed_s=%.6f limit_s=%.6f generation=%lu; ordinary recovery required",
      elapsed,limit,static_cast<unsigned long>(generation_));
    cancel();
    throw nav2_core::PlannerException("Native SCAN has no executable trajectory before timeout");
  }
}
geometry_msgs::msg::Twist LocalMotion::command(const geometry_msgs::msg::Pose &pose,
    const geometry_msgs::msg::Twist &velocity)
{
  if (!has_active_plan_) throw nav2_core::PlannerException("No active plan");
  if (!tracker_->haveTrajectory()) {
    waitForExecutableSpline();
    return geometry_msgs::msg::Twist();
  }
  const auto sample=tracker_->sampleCommand(pose,velocity,true);
  const auto &t=sample.twist;
  if (!sample.valid || !std::isfinite(t.linear.x) || !std::isfinite(t.linear.y) ||
      !std::isfinite(t.linear.z) || !std::isfinite(t.angular.x) ||
      !std::isfinite(t.angular.y) || !std::isfinite(t.angular.z)) {
    cancel();throw nav2_core::PlannerException("Native SCAN trajectory sample invalid");
  }
  if (tracker_->awaitingReplacement()) waitForExecutableSpline();
  else waiting_for_spline_=false;
  exchange_->feedback(generation_,tracker_->executionFrozen(),tracker_->executionFrozenTrajectory());
  return sample.twist;
}
}  // namespace scan_nav2_controller

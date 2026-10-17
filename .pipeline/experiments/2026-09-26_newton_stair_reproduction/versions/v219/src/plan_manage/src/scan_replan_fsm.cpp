#include <bspline_opt/full_trajectory_collision.h>

#include <plan_manage/scan_replan_fsm.h>
#include <plan_manage/reference_path_utils.h>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <iomanip>
#include <sstream>

namespace
{
  constexpr int kReferencePrefixProposalBudget = 6;

  template <typename T>
  T load_parameter(rclcpp::Node *node, const std::string &name, const T &default_value)
  {
    if (!node->has_parameter(name)) node->declare_parameter<T>(name, default_value);
    return node->get_parameter(name).get_value<T>();
  }

  bool qualifiedGoal(const geometry_msgs::msg::Pose &pose)
  {
    const auto &p = pose.position;
    const auto &q = pose.orientation;
    const double norm2 = q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w;
    return std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z) &&
        std::isfinite(norm2) && std::abs(norm2 - 1.0) <= 1e-6;
  }

  // v31: take the FSM's pending body_pose messages and apply them through the
  // unchanged odometryCallback, so odom_pos_ and odom_vel_ are as fresh as the
  // map's body pose when a timer callback starts. A failed take is logged and
  // skipped, as on the executor path.
  template <typename Callback>
  int takePendingOdometry(const rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr &subscription,
                          const rclcpp::Logger &logger, Callback &&callback)
  {
    int applied = 0;
    rclcpp::MessageInfo info;
    while (subscription)
    {
      auto message = std::make_shared<nav_msgs::msg::Odometry>();
      try
      {
        if (!subscription->take(*message, info)) break;
      }
      catch (const rclcpp::exceptions::RCLError &error)
      {
        RCLCPP_ERROR(logger, "input_refresh take from body_pose (fsm) failed: %s", error.what());
        break;
      }
      callback(message);
      ++applied;
    }
    return applied;
  }

  template <typename Message, typename Callback>
  void takePendingMission(const typename rclcpp::Subscription<Message>::SharedPtr &subscription,
                          int capacity, Callback &&callback)
  {
    rclcpp::MessageInfo info;
    for (int i=0; subscription && i<capacity; ++i) {
      auto message=std::make_shared<Message>();
      if (!subscription->take(*message,info)) break;
      callback(message);
    }
  }
} // namespace

namespace scan_planner
{

  void SCANReplanFSM::init(rclcpp::Node *node, rclcpp::CallbackGroup::SharedPtr callback_group, DirectIO direct_io)
  {
    node_ = node;
    direct_io_ = std::move(direct_io);
    current_wp_ = 0;
    exec_state_ = FSM_EXEC_STATE::INIT;
    trigger_ = false;
    have_target_ = false;
    have_odom_ = false;
    have_new_target_ = false;
    rviz_height_ready_ = false;
    go2_execution_frozen_ = false;
    flag_escape_emergency_ = true;
    need_hover_stop_ = false;
    replan_fail_count_ = 0;
    last_freeze_update_time_ = node_->now();

    /*  fsm param  */
    navi_mode_ = load_parameter<int>(node_, "fsm.navi_mode", -1);
    replan_frequency_ = load_parameter<double>(node_, "fsm.replan_frequency", 0.0);
    if (!std::isfinite(replan_frequency_) || replan_frequency_ < 0.0 ||
        replan_frequency_ > 100.0 ||
        (replan_frequency_ > 0.0 && !std::isfinite(1.0 / replan_frequency_)))
      throw std::runtime_error("fsm.replan_frequency must be zero or a finite frequency in (0, 100] Hz");
    last_nominal_replan_s_ = -1.0;
    replan_use_wall_clock_ = load_parameter<bool>(node_, "fsm.replan_use_wall_clock", true);
    replan_thresh_ = load_parameter<double>(node_, "fsm.thresh_replan", -1.0);
    no_replan_thresh_ = load_parameter<double>(node_, "fsm.thresh_no_replan", -1.0);
    planning_horizon_ = load_parameter<double>(node_, "fsm.planning_horizon", -1.0);
    goal_neighbor_tolerance_ = load_parameter<double>(node_, "fsm.goal_neighbor_tolerance", 0.5);
    if (!std::isfinite(goal_neighbor_tolerance_) || goal_neighbor_tolerance_ <= 0.0 ||
        goal_neighbor_tolerance_ > planning_horizon_) throw std::runtime_error("Invalid local goal neighborhood");
    emergency_time_ = load_parameter<double>(node_, "fsm.emergency_time", 1.0);
    enable_fail_safe_ = load_parameter<bool>(node_, "fsm.fail_safe", true);
    max_replan_fail_count_ = load_parameter<int>(node_, "fsm.max_replan_fail_count", 1000);
    self_inflation_z_up_ = load_parameter<double>(node_, "grid_map.obstacles_inflation_z_up", 0.0);
    self_inflation_z_down_ = load_parameter<double>(node_, "grid_map.obstacles_inflation_z_down", 0.0);
    self_double_cylinder_radius_ = load_parameter<double>(node_, "grid_map.double_cylinder_radius", 0.0);
    self_double_cylinder_offset_ = load_parameter<double>(node_, "grid_map.double_cylinder_offset", 0.0);
    body_height_ = load_parameter<double>(node_, "grid_map.body_height", 0.0);
    reference_path_min_distance_ =
        load_parameter<double>(node_, "fsm.reference_path_min_distance", 0.5);
    reference_path_simplify_tolerance_ =
        load_parameter<double>(node_, "fsm.reference_path_simplify_tolerance", 0.0);
    self_inflation_frame_id_ = load_parameter<std::string>(node_, "grid_map.frame_id", "world");

    if (navi_mode_ == NAVI_MODE::PRESET_TARGET)
    {
      const auto flat_waypoints = load_parameter<std::vector<double>>(node_, "fsm.waypoints", {});
      if (flat_waypoints.empty() || flat_waypoints.size() % 3 != 0)
        throw std::runtime_error("navi_mode=2 requires non-empty fsm.waypoints with x,y,z triples");
      waypoint_num_ = static_cast<int>(flat_waypoints.size() / 3);
      preset_waypoints_.resize(waypoint_num_);
      for (int i = 0; i < waypoint_num_; i++)
      {
        preset_waypoints_[i] = Eigen::Vector3d(flat_waypoints[3 * i], flat_waypoints[3 * i + 1],
                                               flat_waypoints[3 * i + 2]);
      }
    }

    /* initialize main modules */
    visualization_.reset(new PlanningVisualization(node_));
    planner_manager_.reset(new SCANPlannerManager);
    planner_manager_->initPlanModules(node_, visualization_, callback_group);

    /* callback */
    rclcpp::SubscriptionOptions subscription_options;
    subscription_options.callback_group = callback_group;
    exec_timer_ = node_->create_wall_timer(std::chrono::milliseconds(10),
                                           std::bind(&SCANReplanFSM::execFSMCallback, this), callback_group);
    safety_timer_ = node_->create_wall_timer(std::chrono::milliseconds(50),
                                             std::bind(&SCANReplanFSM::checkCollisionCallback, this), callback_group);
    odom_sub_ = node_->create_subscription<nav_msgs::msg::Odometry>(
        "body_pose", rclcpp::SensorDataQoS(),
        std::bind(&SCANReplanFSM::odometryCallback, this, std::placeholders::_1), subscription_options);
    if (!direct_io_.spline) go2_execution_frozen_sub_ = node_->create_subscription<std_msgs::msg::Bool>(
        "planning/go2_execution_frozen", 10,
        std::bind(&SCANReplanFSM::go2ExecutionFrozenCallback, this, std::placeholders::_1), subscription_options);

    bspline_pub_ = node_->create_publisher<scan_planner_msgs::msg::Bspline>("planning/bspline", 10);
    data_disp_pub_ = node_->create_publisher<scan_planner_msgs::msg::DataDisp>("planning/data_display", 100);
    self_inflation_pub_ = node_->create_publisher<visualization_msgs::msg::Marker>(
        "self_inflation", rclcpp::QoS(1).reliable().transient_local());

    if (navi_mode_ == NAVI_MODE::MANUAL_TARGET)
      goal_sub_ = node_->create_subscription<geometry_msgs::msg::PoseStamped>(
          "move_base_simple/goal", 1,
          std::bind(&SCANReplanFSM::rvizGoalCallback, this, std::placeholders::_1), subscription_options);
    else if (navi_mode_ == NAVI_MODE::REFERENCE_PATH && !direct_io_.spline)
      path_sub_ = node_->create_subscription<nav_msgs::msg::Path>(
          "initial_path", rclcpp::QoS(1).reliable().transient_local(),
          std::bind(&SCANReplanFSM::pathCallback, this, std::placeholders::_1), subscription_options);
    else if (navi_mode_ == NAVI_MODE::PRESET_TARGET)
      RCLCPP_INFO(node_->get_logger(), "Preset waypoint mode will start after the first odometry message");
    else if (!(navi_mode_ == NAVI_MODE::REFERENCE_PATH && direct_io_.spline))
      throw std::runtime_error("fsm.navi_mode must be 1, 2, or 3");
  }

  void SCANReplanFSM::planGlobalTrajbyGivenWps()
  {
    std::vector<Eigen::Vector3d> wps = preset_waypoints_;

    for (size_t i = 0; i < wps.size(); i++)
    {
      visualization_->displayGoalPoint(wps[i], Eigen::Vector4d(0, 0.5, 0.5, 1), 0.3, i);
    }

    active_waypoints_ = wps;
    current_wp_ = 0;
    trigger_ = true;
    init_pt_ = odom_pos_;

    if (planNextWaypoint())
    {
      changeFSMExecState(GEN_NEW_TRAJ, "TRIG");
    }
    else
    {
      RCLCPP_ERROR(node_->get_logger(), "Unable to generate global trajectory to first preset waypoint");
    }
  }

  void SCANReplanFSM::rvizGoalCallback(geometry_msgs::msg::PoseStamped::ConstSharedPtr msg)
  {
    if (!msg)
      return;

    if (!rviz_height_ready_)
    {
      RCLCPP_WARN(node_->get_logger(), "Ignore RViz goal before receiving initial body pose");
      return;
    }

    auto path = std::make_shared<nav_msgs::msg::Path>();
    path->header = msg->header;
    path->poses.push_back(*msg);
    waypointCallback(path);
  }

  void SCANReplanFSM::waypointCallback(nav_msgs::msg::Path::ConstSharedPtr msg)
  {
    if (!msg || msg->poses.empty())
    {
      RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 1000,
                           "Empty waypoint message; ignoring");
      return;
    }

    if (msg->poses[0].pose.position.z < -0.1)
      return;

    cout << "Triggered!" << endl;
    trigger_ = true;
    init_pt_ = odom_pos_;

    bool success = false;
    end_pt_ << msg->poses[0].pose.position.x, msg->poses[0].pose.position.y, rviz_goal_height_;
    success = planner_manager_->planGlobalTraj(odom_pos_, odom_vel_, Eigen::Vector3d::Zero(), end_pt_, Eigen::Vector3d::Zero(), Eigen::Vector3d::Zero());

    if (success)
      success = adjustGlobalTargetIfOccupied();

    visualization_->displayGoalPoint(end_pt_, Eigen::Vector4d(0, 0.5, 0.5, 1), 0.3, 0);

    if (success)
    {

      /*** display ***/
      constexpr double step_size_t = 0.1;
      int i_end = floor(planner_manager_->global_data_.global_duration_ / step_size_t);
      vector<Eigen::Vector3d> gloabl_traj(i_end);
      for (int i = 0; i < i_end; i++)
      {
        gloabl_traj[i] = planner_manager_->global_data_.global_traj_.evaluate(i * step_size_t);
      }

      end_vel_.setZero();
      have_target_ = true;
      have_new_target_ = true;

      /*** FSM ***/
      if (exec_state_ == WAIT_TARGET)
        changeFSMExecState(GEN_NEW_TRAJ, "TRIG");
      else if (exec_state_ == EXEC_TRAJ)
        changeFSMExecState(REPLAN_TRAJ, "TRIG");

      // visualization_->displayGoalPoint(end_pt_, Eigen::Vector4d(1, 0, 0, 1), 0.3, 0);
      visualization_->displayGlobalPathList(gloabl_traj, 0.1, 0);
    }
    else
    {
      RCLCPP_ERROR(node_->get_logger(), "Unable to generate global trajectory");
    }
  }

  bool SCANReplanFSM::planGlobalTrajByWaypoints(const std::vector<Eigen::Vector3d> &waypoints, bool preserve_binding)
  {
    if (!preserve_binding) {
      planner_manager_->invalidateWarmStart();
      feasible_window_.valid = false;
    } // Compatible callbacks reproject geometry after successful regeneration.
    if (waypoints.size() < 2)
    {
      RCLCPP_WARN(node_->get_logger(), "Reference path requires at least two points");
      return false;
    }

    end_pt_ = waypoints.back();
    std::vector<Eigen::Vector3d> reference_waypoints(waypoints.begin() + 1, waypoints.end());

    for (size_t i = 0; i < waypoints.size(); i++)
    {
      visualization_->displayGoalPoint(waypoints[i], Eigen::Vector4d(0, 0.5, 0.5, 1), 0.3, i);
    }

    bool success = planner_manager_->planGlobalTrajWaypoints(
        waypoints.front(),
        Eigen::Vector3d::Zero(),
        Eigen::Vector3d::Zero(),
        reference_waypoints,
        Eigen::Vector3d::Zero(),
        Eigen::Vector3d::Zero(), preserve_binding);

    if (!success)
    {
      RCLCPP_ERROR(node_->get_logger(), "Unable to generate global trajectory from waypoints");
      return false;
    }

    // New-reference admission precedes local PVA initialization. Its search
    // origin is the due measured body, not a previous/uninitialized local seed.
    const Eigen::Vector3d query_start = have_odom_ ? odom_pos_ : waypoints.front();
    const auto admission_started = std::chrono::steady_clock::now();
    const char *failure_reason = "none";
    int failure_sample = -1;
    const double admission_ros_start = node_->now().seconds();
    const bool body_heading_before = std::isfinite(planner_manager_->grid_map_->collisionSegmentYaw(query_start, query_start));
    const bool admitted = adjustGlobalTargetIfOccupied(query_start, &failure_reason, &failure_sample);
    const double admission_ros_end = node_->now().seconds();
    const bool body_heading_after = std::isfinite(planner_manager_->grid_map_->collisionSegmentYaw(query_start, query_start));
    RCLCPP_INFO(node_->get_logger(),
        "V132_REFERENCE_ADMISSION generation=%ld accepted=%d reason=%s sample=%d wall_ms=%.9f ros_start=%.9f ros_end=%.9f observation_stamp=%.9f heading_before=%d heading_after=%d",
        static_cast<long>(route_generation_), admitted, failure_reason, failure_sample,
        std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now()-admission_started).count(),
        admission_ros_start, admission_ros_end, planner_manager_->grid_map_->observationStamp(),
        body_heading_before, body_heading_after);
    if (!admitted) return false;

    constexpr double step_size_t = 0.1;
    int i_end = floor(planner_manager_->global_data_.global_duration_ / step_size_t);
    std::vector<Eigen::Vector3d> gloabl_traj(i_end);
    for (int i = 0; i < i_end; i++)
    {
      gloabl_traj[i] = planner_manager_->global_data_.global_traj_.evaluate(i * step_size_t);
    }

    end_vel_.setZero();
    have_target_ = true;
    have_new_target_ = true;
    visualization_->displayGlobalPathList(gloabl_traj, 0.1, 0);
    visualization_->displayGoalPoint(end_pt_, Eigen::Vector4d(0, 0.5, 0.5, 1), 0.3, static_cast<int>(waypoints.size()) - 1);

    return true;
  }

  bool SCANReplanFSM::planNextWaypoint()
  {
    if (current_wp_ < 0 || current_wp_ >= (int)active_waypoints_.size())
    {
      RCLCPP_WARN(node_->get_logger(), "[navi_mode=%d] No active waypoint to plan", navi_mode_);
      return false;
    }

    end_pt_ = active_waypoints_[current_wp_];
    setStartStateFromOdomOrCurrentTraj();

    bool success = planner_manager_->planGlobalTraj(
        start_pt_,
        start_vel_,
        start_acc_,
        end_pt_,
        Eigen::Vector3d::Zero(),
        Eigen::Vector3d::Zero());

    if (!success)
    {
      RCLCPP_ERROR(node_->get_logger(), "[navi_mode=%d] Unable to generate trajectory to waypoint %d",
                   navi_mode_, current_wp_ + 1);
      return false;
    }

    if (!adjustGlobalTargetIfOccupied())
      return false;

    constexpr double step_size_t = 0.1;
    int i_end = floor(planner_manager_->global_data_.global_duration_ / step_size_t);
    std::vector<Eigen::Vector3d> gloabl_traj(i_end);
    for (int i = 0; i < i_end; i++)
    {
      gloabl_traj[i] = planner_manager_->global_data_.global_traj_.evaluate(i * step_size_t);
    }

    end_vel_.setZero();
    have_target_ = true;
    have_new_target_ = true;
    visualization_->displayGlobalPathList(gloabl_traj, 0.1, 0);
    visualization_->displayGoalPoint(end_pt_, Eigen::Vector4d(0, 0.5, 0.5, 1), 0.3, current_wp_);
    RCLCPP_INFO(node_->get_logger(), "[navi_mode=%d] Planning to waypoint %d/%zu: [%.2f, %.2f, %.2f]",
                navi_mode_, current_wp_ + 1, active_waypoints_.size(), end_pt_(0), end_pt_(1), end_pt_(2));

    return true;
  }

  bool SCANReplanFSM::isWaypointSequenceMode() const
  {
    return navi_mode_ == NAVI_MODE::PRESET_TARGET;
  }

  bool SCANReplanFSM::adjustGlobalTargetIfOccupied()
  {
    return adjustGlobalTargetIfOccupied(start_pt_);
  }

  bool SCANReplanFSM::adjustGlobalTargetIfOccupied(const Eigen::Vector3d &query_start,
      const char **failure_reason, int *failure_sample)
  {
    const auto reject = [&](const char *reason, int sample = -1) {
      if (failure_reason) *failure_reason = reason;
      if (failure_sample) *failure_sample = sample;
      return false;
    };
    auto map = planner_manager_->grid_map_;
    // v31: check the target, search its neighbourhood and walk the route with the
    // newest received inputs; a route message reaches here without a timer.
    if (map) map->refreshSensorInputs("target_check");
    auto &global_data = planner_manager_->global_data_;
    const double duration = global_data.global_duration_;
    const bool reference = navi_mode_ == NAVI_MODE::REFERENCE_PATH;
    reference_frontier_time_ = -1.0;
    reference_neighbor_target_ = false;
    if (reference && (!map || !std::isfinite(duration) || duration < 1e-3 ||
                      duration / 0.05 >= std::numeric_limits<int>::max()))
      return reject("invalid_reference_context");
    if (!map || duration < 1e-3)
      return true;

    constexpr double sample_dt = 0.05;
    const int sample_num = std::max(1, static_cast<int>(std::ceil(duration / sample_dt)));
    const Eigen::Vector3d final_pt = global_data.global_traj_.evaluate(duration);
    const Eigen::Vector3d final_prev = global_data.global_traj_.evaluate(duration * (sample_num - 1) / sample_num);
    if (reference && (!final_pt.allFinite() || !final_prev.allFinite())) return reject("nonfinite_final_geometry");
    const double final_yaw = estimateYawFromSegment(final_prev, final_pt);
    if (reference && !std::isfinite(final_yaw)) return reject("nonfinite_final_heading");
    const int final_occ = map->getInflateOccupancy(final_pt, final_yaw);
    if (reference ? final_occ == 0 : final_occ <= 0) {
      if (reference) reference_frontier_time_ = duration;
      return true;
    }

    if (reference) {
      const auto path = planner_manager_->findGoalNeighborhoodPath(query_start, final_pt, goal_neighbor_tolerance_);
      if (!path.empty()) {
        if (path.size() > 1 && (path.back() - final_pt).norm() <= goal_neighbor_tolerance_ &&
            planner_manager_->hasLocalTranslation(query_start, path.back())) {
          reference_neighbor_point_ = path.back();
          reference_frontier_time_ = duration;
          reference_neighbor_target_ = true;
          RCLCPP_INFO(node_->get_logger(), "reference_goal_neighbor xyz=[%.12f,%.12f,%.12f] displacement=%.12f reached_path_points=%zu final_goal_unchanged=1",
                      path.back().x(), path.back().y(), path.back().z(), (path.back()-final_pt).norm(), path.size());
          return true;
        }
      }
    }

    // Goal-neighborhood search may outlive body/map validity. Apply inputs
    // already received before checking the fallback reference points. Their
    // original stamps and all collision/freshness rules remain unchanged.
    if (reference) map->refreshSensorInputs("target_fallback");

    for (int i = sample_num; i >= 0; --i)
    {
      const double t = duration * i / sample_num;
      const double prev_t = duration * std::max(0, i - 1) / sample_num;
      const Eigen::Vector3d pt = global_data.global_traj_.evaluate(t);
      const Eigen::Vector3d prev_pt = global_data.global_traj_.evaluate(prev_t);

      if (reference && (!pt.allFinite() || !prev_pt.allFinite())) return reject("nonfinite_sample_geometry", i);
      const double yaw = estimateYawFromSegment(prev_pt, pt);
      if (reference && !std::isfinite(yaw)) return reject("nonfinite_sample_heading", i);
      if (map->getInflateOccupancy(pt, yaw) == 0)
      {
        if (reference) {
          reference_frontier_time_ = t;
          RCLCPP_INFO(node_->get_logger(),
                      "reference_frontier time=%.12f full_duration=%.12f xyz=[%.12f,%.12f,%.12f]",
                      t, duration, pt.x(), pt.y(), pt.z());
          return true;
        }
        const Eigen::Vector3d raw_end = end_pt_;
        end_pt_ = pt;
        global_data.global_duration_ = t;
        global_data.last_progress_time_ = std::min(global_data.last_progress_time_, t);
        RCLCPP_WARN(node_->get_logger(),
                    "Target [%.2f, %.2f, %.2f] is occupied; using [%.2f, %.2f, %.2f]",
                    raw_end(0), raw_end(1), raw_end(2), end_pt_(0), end_pt_(1), end_pt_(2));
        return true;
      }
    }

    RCLCPP_ERROR(node_->get_logger(),
                 "Target is occupied and no collision-free point was found on the global trajectory");
    return reject("no_collision_free_point");
  }


  void SCANReplanFSM::pathCallback(nav_msgs::msg::Path::ConstSharedPtr msg)
  {
    takePendingOdometry(odom_sub_, node_->get_logger(),
        [this](nav_msgs::msg::Odometry::ConstSharedPtr body) { odometryCallback(body); });
    applyDueOdometry();
    if (!msg || msg->poses.empty()) {
      RCLCPP_WARN(node_->get_logger(), "Ignoring empty reference path");
      return;
    }
    std::vector<Eigen::Vector3d> waypoints;
    std::string path_error;
    if (!prepareReferenceWaypoints(*msg, body_height_, reference_path_min_distance_,
                                  waypoints, &path_error, reference_path_simplify_tolerance_)) {
      RCLCPP_WARN(node_->get_logger(), "Ignoring reference path: %s", path_error.c_str());
      return;
    }
    auto map = planner_manager_->grid_map_;
    map->refreshSensorInputs("route_input_ready");
    const auto inputs_ready = [&] {
      return map->planningInputsReady() && std::isfinite(map->collisionSegmentYaw(odom_pos_, odom_pos_));
    };
    if (!have_odom_ || exec_state_ == EMERGENCY_STOP || !inputs_ready()) {
      deferred_path_ = msg;
      return;
    }
    // The newest valid path supersedes a previously deferred route.
    deferred_path_.reset();
    const auto previous_generation = route_generation_;
    const bool previous_goal_valid = have_requested_goal_pose_;
    const auto previous_goal = requested_goal_pose_;
    const auto previous_global = planner_manager_->global_data_;
    const auto previous_window = feasible_window_;
    const auto previous_end = end_pt_, previous_end_vel = end_vel_;
    const auto previous_neighbor = reference_neighbor_point_;
    const double previous_frontier = reference_frontier_time_;
    const bool previous_neighbor_target = reference_neighbor_target_;
    const bool previous_trigger = trigger_, previous_target = have_target_, previous_new = have_new_target_;
    const auto previous_binding = planner_manager_->warmStartBinding();
    const auto goal_pose = msg->poses.back().pose;
    const bool goal_valid = qualifiedGoal(goal_pose);
    const bool compatible = have_requested_goal_pose_ && goal_valid &&
        requested_goal_pose_ == goal_pose && canPreserveReferenceBinding();
    if (!compatible) ++route_generation_;
    requested_goal_pose_ = goal_pose;
    have_requested_goal_pose_ = goal_valid;
    trigger_ = true;
    end_pt_ = waypoints.back();
    const bool success = planGlobalTrajByWaypoints(waypoints, compatible);
    const bool ready_after = inputs_ready();
    if (success && ready_after) {
      if (compatible) reprojectFeasibleWindow();
      if (exec_state_ == WAIT_TARGET) changeFSMExecState(GEN_NEW_TRAJ, "PATH");
      else if (exec_state_ == EXEC_TRAJ) changeFSMExecState(REPLAN_TRAJ, "PATH");
      else if (exec_state_ == REPLAN_TRAJ) {
        const auto &info = planner_manager_->local_data_;
        const double raw_t_cur = (node_->now() - info.start_time_).seconds();
        if (info.start_time_.seconds() < 1e-5 || raw_t_cur >= info.duration_ || replan_fail_count_ > 0) {
          start_pt_ = odom_pos_; start_vel_ = odom_vel_; start_acc_.setZero();
          planner_manager_->invalidateWarmStart();
          changeFSMExecState(GEN_NEW_TRAJ, "PATH_RECOVERY");
        }
      }
    } else {
      if (!ready_after) deferred_path_ = msg;
      else RCLCPP_ERROR(node_->get_logger(), "Unable to generate global trajectory from reference path");
      route_generation_ = previous_generation;
      requested_goal_pose_ = previous_goal;
      have_requested_goal_pose_ = previous_goal_valid;
      planner_manager_->global_data_ = previous_global;
      feasible_window_ = previous_window;
      end_pt_ = previous_end; end_vel_ = previous_end_vel;
      reference_frontier_time_ = previous_frontier;
      reference_neighbor_point_ = previous_neighbor;
      reference_neighbor_target_ = previous_neighbor_target;
      trigger_ = previous_trigger; have_target_ = previous_target; have_new_target_ = previous_new;
      planner_manager_->restoreWarmStartBinding(previous_binding);
    }
  }

  void SCANReplanFSM::odometryCallback(nav_msgs::msg::Odometry::ConstSharedPtr msg)
  {
    applyDueOdometry();
    if (!body_inputs_.push(msg)) {
      have_odom_=false;
      flag_escape_emergency_=true;
      need_hover_stop_=true;
      RCLCPP_ERROR(node_->get_logger(),"FSM body admission failed: %s",body_inputs_.error().c_str());
      changeFSMExecState(EMERGENCY_STOP,"BODY_TIME_INPUT");
      return;
    }
    applyDueOdometry();
  }

  void SCANReplanFSM::applyDueOdometry()
  {
    const auto message=body_inputs_.takeDue(node_->now().nanoseconds());
    if (message) applyOdometry(message);
  }

  void SCANReplanFSM::applyOdometry(nav_msgs::msg::Odometry::ConstSharedPtr msg)
  {
    odom_pos_(0) = msg->pose.pose.position.x;
    odom_pos_(1) = msg->pose.pose.position.y;
    odom_pos_(2) = msg->pose.pose.position.z;

    if (navi_mode_ == NAVI_MODE::MANUAL_TARGET && !rviz_height_ready_)
    {
      rviz_goal_height_ = odom_pos_(2);
      rviz_height_ready_ = true;
      RCLCPP_INFO(node_->get_logger(), "Set RViz goal height from initial body_pose z: %.3f", rviz_goal_height_);
    }

    odom_vel_(0) = msg->twist.twist.linear.x;
    odom_vel_(1) = msg->twist.twist.linear.y;
    odom_vel_(2) = msg->twist.twist.linear.z;

    //odom_acc_ = estimateAcc( msg );

    odom_orient_.w() = msg->pose.pose.orientation.w;
    odom_orient_.x() = msg->pose.pose.orientation.x;
    odom_orient_.y() = msg->pose.pose.orientation.y;
    odom_orient_.z() = msg->pose.pose.orientation.z;

    // Lite3 interface: Odometry twist is in child_frame_id=base;
    // native SCAN's seed velocity is in the world frame.
    if (msg->child_frame_id == "base")
      odom_vel_ = odom_orient_ * odom_vel_;


    have_odom_ = true;
    publishSelfInflationMarker();
    if (navi_mode_ == NAVI_MODE::PRESET_TARGET && !preset_started_)
    {
      preset_started_ = true;
      planGlobalTrajbyGivenWps();
    }
  }

  void SCANReplanFSM::publishSpline(const scan_planner_msgs::msg::Bspline &spline)
  {
    // Capture the complete result while the existing map publication lease holds.
    if (direct_io_.spline) direct_io_.spline(spline);
    bspline_pub_->publish(spline); // Observation only in direct mode.
  }

  void SCANReplanFSM::setExecutionFeedback(bool frozen,int64_t trajectory)
  {
    go2_execution_frozen_ = trajectory == planner_manager_->local_data_.traj_id_ && frozen;
  }

  void SCANReplanFSM::cancelReference()
  {
    deferred_path_.reset(); active_waypoints_.clear();
    trigger_=have_target_=have_new_target_=have_requested_goal_pose_=false;
    go2_execution_frozen_=false; need_hover_stop_=false;
    feasible_window_.valid=false; steering_prefix_generation_=-1;
    reference_frontier_time_=-1; reference_neighbor_target_=false;
    ++route_generation_; replan_fail_count_=0;
    last_nominal_replan_s_=next_nominal_replan_s_=last_replan_clock_s_=-1;
    planner_manager_->invalidateWarmStart();
    planner_manager_->local_data_.duration_=0;
    planner_manager_->local_data_.start_time_=rclcpp::Time(0,0,node_->get_clock()->get_clock_type());
    last_freeze_traj_id_=-1; last_freeze_update_time_=node_->now();
    exec_state_=have_odom_ ? WAIT_TARGET : INIT;
  }

  void SCANReplanFSM::go2ExecutionFrozenCallback(std_msgs::msg::Bool::ConstSharedPtr msg)
  {
    go2_execution_frozen_ = msg->data;
  }

  void SCANReplanFSM::updateLocalTrajTimeFreeze()
  {
    const rclcpp::Time now = node_->now();
    LocalTrajData *info = &planner_manager_->local_data_;
    if (info->traj_id_ != last_freeze_traj_id_) {
      last_freeze_traj_id_ = info->traj_id_;
      last_freeze_update_time_ = now;
      return;  // Never charge the previous trajectory's frozen interval to this one.
    }
    const double dt = (now - last_freeze_update_time_).seconds();
    last_freeze_update_time_ = now;
    if (go2_execution_frozen_ && dt > 0.0 && dt <= 0.2 &&
        info->start_time_.seconds() > 1e-5 && info->start_time_ <= now) {
      info->start_time_ += rclcpp::Duration::from_seconds(dt);
      if (info->start_time_ > now) info->start_time_ = now;
    }
    // An already future-stamped input is not repaired here: the validator rejects it.
  }

  double SCANReplanFSM::getOdomYaw() const
  {
    Eigen::Vector3d heading = odom_orient_.toRotationMatrix().col(0);
    if (heading.head<2>().squaredNorm() < 1e-8)
      return 0.0;
    return std::atan2(heading(1), heading(0));
  }

  double SCANReplanFSM::estimateYawFromSegment(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const
  {
    return planner_manager_->grid_map_->collisionSegmentYaw(from, to);
  }

  void SCANReplanFSM::publishSelfInflationMarker()
  {
    const double radius = std::max(0.0, self_double_cylinder_radius_);
    const double z_up = std::max(0.0, self_inflation_z_up_);
    const double z_down = std::max(0.0, self_inflation_z_down_);
    const double height = std::max(1e-3, z_up + z_down);

    visualization_msgs::msg::Marker marker;
    marker.header.frame_id = self_inflation_frame_id_.empty() ? "world" : self_inflation_frame_id_;
    marker.header.stamp = node_->now();
    marker.ns = "self_inflation";
    marker.type = visualization_msgs::msg::Marker::CYLINDER;
    marker.action = visualization_msgs::msg::Marker::ADD;
    marker.pose.orientation.w = 1.0;
    marker.scale.x = 2.0 * radius;
    marker.scale.y = 2.0 * radius;
    marker.scale.z = height;
    marker.color.r = 0.1;
    marker.color.g = 0.6;
    marker.color.b = 1.0;
    marker.color.a = 0.4;
    marker.lifetime = rclcpp::Duration::from_seconds(0.2);

    Eigen::Vector3d center = odom_pos_;
    center(2) += 0.5 * (z_up - z_down);

    Eigen::Vector3d heading(std::cos(getOdomYaw()), std::sin(getOdomYaw()), 0.0);
    Eigen::Vector3d front = center + self_double_cylinder_offset_ * heading;
    Eigen::Vector3d rear = center - self_double_cylinder_offset_ * heading;

    marker.id = 0;
    marker.pose.position.x = front(0);
    marker.pose.position.y = front(1);
    marker.pose.position.z = front(2);
    self_inflation_pub_->publish(marker);

    marker.id = 1;
    marker.pose.position.x = rear(0);
    marker.pose.position.y = rear(1);
    marker.pose.position.z = rear(2);
    self_inflation_pub_->publish(marker);
  }

  void SCANReplanFSM::changeFSMExecState(FSM_EXEC_STATE new_state, string pos_call)
  {

    if (new_state == exec_state_)
      continuously_called_times_++;
    else
      continuously_called_times_ = 1;

    static string state_str[7] = {"INIT", "WAIT_TARGET", "GEN_NEW_TRAJ", "REPLAN_TRAJ", "EXEC_TRAJ", "EMERGENCY_STOP"};
    int pre_s = int(exec_state_);
    exec_state_ = new_state;
    cout << "[" + pos_call + "]: from " + state_str[pre_s] + " to " + state_str[int(new_state)] << endl;
  }

  std::pair<int, SCANReplanFSM::FSM_EXEC_STATE> SCANReplanFSM::timesOfConsecutiveStateCalls()
  {
    return std::pair<int, FSM_EXEC_STATE>(continuously_called_times_, exec_state_);
  }

  void SCANReplanFSM::printFSMExecState()
  {
    static string state_str[7] = {"INIT", "WAIT_TARGET", "GEN_NEW_TRAJ", "REPLAN_TRAJ", "EXEC_TRAJ", "EMERGENCY_STOP"};

    cout << "[FSM]: state: " + state_str[int(exec_state_)] << endl;
  }

  bool SCANReplanFSM::nominalReplanDue(bool mark_attempt)
  {
    if (replan_frequency_ <= 0.0) return true;
    const double now_s = replan_use_wall_clock_ ? std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count() : node_->now().seconds();
    const double period = 1.0 / replan_frequency_;
    // Observe every check: a rollback can remain later than the last attempt.
    if (last_replan_clock_s_ >= 0.0 && now_s < last_replan_clock_s_)
    {
      last_replan_clock_s_ = now_s;
      last_nominal_replan_s_ = now_s;
      next_nominal_replan_s_ = now_s + period;
      return false;
    }
    last_replan_clock_s_ = now_s;
    if (next_nominal_replan_s_ < 0.0) next_nominal_replan_s_ = now_s;
    if (now_s + 1e-9 < next_nominal_replan_s_) return false;
    if (mark_attempt)
    {
      // Keep the phase despite poll quantization. Skip missed slots, never
      // issue a catch-up burst or run concurrent solver calls on the same map.
      const auto skipped = static_cast<std::int64_t>(std::floor(
          std::max(0.0, now_s - next_nominal_replan_s_ + 1e-9) / period));
      next_nominal_replan_s_ += (skipped + 1) * period;
      last_nominal_replan_s_ = now_s;
      RCLCPP_INFO(node_->get_logger(), "nominal_replan frequency_hz=%.6f start_schedule_s=%.9f clock=%s ros_s=%.9f state=%d skipped_slots=%lld",
                  replan_frequency_, now_s, replan_use_wall_clock_ ? "wall" : "ros", node_->now().seconds(),
                  static_cast<int>(exec_state_), static_cast<long long>(skipped));
    }
    return true;
  }

  void SCANReplanFSM::performNominalReplan()
  {
    if (!nominalReplanDue(true)) return;
    const auto started = std::chrono::steady_clock::now();
    const auto started_ros_ns = node_->now().nanoseconds();
    const auto profile_before=planner_manager_->grid_map_->planning_profile_.values;
    const bool success = planFromCurrentTraj();
    if (direct_io_.planning_result) direct_io_.planning_result(success,started_ros_ns);
    RCLCPP_INFO(node_->get_logger(), "V50_PROFILE %s", planner_manager_->grid_map_->planning_profile_.since(profile_before).c_str());
    const double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - started).count();
    RCLCPP_INFO(node_->get_logger(), "nominal_replan_result success=%d wall_s=%.9f budget_s=%.9f overrun=%d",
                success, elapsed, 1.0 / replan_frequency_, elapsed > 1.0 / replan_frequency_);
    if (success)
    {
      replan_fail_count_ = 0;
      changeFSMExecState(EXEC_TRAJ, "FSM");
    }
    else
    {
      replan_fail_count_++;
      changeFSMExecState(REPLAN_TRAJ, "FSM");
    }
  }

  void SCANReplanFSM::execFSMCallback()
  {
    if (direct_io_.before_work) direct_io_.before_work();
    // v31: start each planning-timer callback from the newest received inputs,
    // the FSM's own body_pose included.
    const int fsm_odometry = takePendingOdometry(
        odom_sub_, node_->get_logger(), [this](nav_msgs::msg::Odometry::ConstSharedPtr msg) { odometryCallback(msg); });
    applyDueOdometry();
    planner_manager_->grid_map_->refreshSensorInputs("exec", fsm_odometry);
    // Drain the reliable path queue at native work boundaries. Emergency exit
    // must complete before the deferred replacement is installed.
    const auto service_mission = [this] {
      takePendingMission<nav_msgs::msg::Path>(path_sub_, 1,
          [this](nav_msgs::msg::Path::ConstSharedPtr msg) { deferred_path_ = msg; });
      if (exec_state_ != EMERGENCY_STOP && have_odom_ && deferred_path_ &&
          planner_manager_->grid_map_->planningInputsReady()) {
        auto path = deferred_path_;
        deferred_path_.reset();
        pathCallback(path);
      }
    };
    service_mission();
    updateLocalTrajTimeFreeze();

    static int fsm_num = 0;
    fsm_num++;
    if (fsm_num == 100)
    {
      printFSMExecState();
      if (!have_odom_)
        cout << "no odom." << endl;
      if (!trigger_)
        cout << "wait for goal." << endl;
      fsm_num = 0;
    }

    GridMap::RawContributorCacheScope callback_cache(*planner_manager_->grid_map_);

    switch (exec_state_)
    {
    case INIT:
    {
      if (!have_odom_)
      {
        return;
      }
      if (!trigger_)
      {
        return;
      }
      changeFSMExecState(WAIT_TARGET, "FSM");
      break;
    }

    case WAIT_TARGET:
    {
      if (!have_target_)
        return;
      else
      {
        changeFSMExecState(GEN_NEW_TRAJ, "FSM");
      }
      break;
    }

    case GEN_NEW_TRAJ:
    {
      if (!nominalReplanDue(true)) break;
      setStartStateFromOdomOrCurrentTraj();

      // Eigen::Vector3d rot_x = odom_orient_.toRotationMatrix().block(0, 0, 3, 1);
      // start_yaw_(0)         = atan2(rot_x(1), rot_x(0));
      // start_yaw_(1) = start_yaw_(2) = 0.0;

      bool flag_random_poly_init;
      if (timesOfConsecutiveStateCalls().first == 1)
        flag_random_poly_init = false;
      else
        flag_random_poly_init = true;

      const auto initial_started=std::chrono::steady_clock::now();
      const auto initial_started_ros_ns=node_->now().nanoseconds();
      const auto profile_before=planner_manager_->grid_map_->planning_profile_.values;
      bool success = callReboundReplan(true, flag_random_poly_init);
      if (direct_io_.planning_result) direct_io_.planning_result(success,initial_started_ros_ns);
      RCLCPP_INFO(node_->get_logger(), "V50_PROFILE %s", planner_manager_->grid_map_->planning_profile_.since(profile_before).c_str());
      const double initial_elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-initial_started).count();
      if(replan_frequency_>0.0)
        RCLCPP_INFO(node_->get_logger(), "nominal_replan_result success=%d wall_s=%.9f budget_s=%.9f overrun=%d",
            success, initial_elapsed, 1.0/replan_frequency_, initial_elapsed>1.0/replan_frequency_);
      if (success)
      {

        replan_fail_count_ = 0;
        changeFSMExecState(EXEC_TRAJ, "FSM");
        flag_escape_emergency_ = true;
      }
      else
      {
        replan_fail_count_++;
        changeFSMExecState(GEN_NEW_TRAJ, "FSM");
      }
      break;
    }

    case REPLAN_TRAJ:
    {
      if (replan_frequency_ > 0.0)
      {
        performNominalReplan();
        break;
      }
      if (!nominalReplanDue(true)) break;

      if (planFromCurrentTraj())
      {
        replan_fail_count_ = 0;
        changeFSMExecState(EXEC_TRAJ, "FSM");
      }
      else
      {
        replan_fail_count_++;
        changeFSMExecState(REPLAN_TRAJ, "FSM");
      }

      break;
    }

    case EXEC_TRAJ:
    {
      /* determine if need to replan */
      LocalTrajData *info = &planner_manager_->local_data_;
      rclcpp::Time time_now = node_->now();
      double t_cur = (time_now - info->start_time_).seconds();
      t_cur = min(info->duration_, t_cur);

      Eigen::Vector3d pos = info->position_traj_.evaluateDeBoorT(t_cur);

      if (isWaypointSequenceMode() &&
          current_wp_ + 1 < (int)active_waypoints_.size() &&
          (end_pt_ - odom_pos_).norm() < 0.5)
      {
        current_wp_++;
        if (planNextWaypoint())
        {
          changeFSMExecState(GEN_NEW_TRAJ, "FSM");
          return;
        }
        replan_fail_count_++;
        changeFSMExecState(GEN_NEW_TRAJ, "FSM");
        return;
      }

      /* && (end_pt_ - pos).norm() < 0.5 */
      if (t_cur > info->duration_ - 1e-2)
      {
        const auto &global_data = planner_manager_->global_data_;
        const bool reference_path_has_next_window =
            navi_mode_ == NAVI_MODE::REFERENCE_PATH &&
            (global_data.last_progress_time_ < global_data.global_duration_ - 1e-3 ||
             (info->position_traj_.evaluateDeBoorT(info->duration_) - end_pt_).norm() > 1e-3);

        // In reference-path mode, a local B-spline covers only one planning
        // horizon.  Finishing that spline does not mean that the complete PCT
        // route has been reached: request the next local window and keep the
        // global target active.
        if (reference_path_has_next_window)
        {
          RCLCPP_INFO(node_->get_logger(),
                      "Local reference window complete (%.2f/%.2fs); continuing along the global path",
                      global_data.last_progress_time_, global_data.global_duration_);
          changeFSMExecState(REPLAN_TRAJ, "FSM");
          return;
        }

        if (isWaypointSequenceMode() && current_wp_ + 1 < (int)active_waypoints_.size())
        {
          current_wp_++;
          if (planNextWaypoint())
          {
            changeFSMExecState(GEN_NEW_TRAJ, "FSM");
            return;
          }
          replan_fail_count_++;
          changeFSMExecState(GEN_NEW_TRAJ, "FSM");
          return;
        }

        if (isWaypointSequenceMode())
        {
          active_waypoints_.clear();
          current_wp_ = 0;
        }

        have_target_ = false;

        changeFSMExecState(WAIT_TARGET, "FSM");
        return;
      }
      else if ((end_pt_ - pos).norm() < no_replan_thresh_)
      {
        // cout << "near end" << endl;
        return;
      }
      else if (replan_frequency_ > 0.0)
      {
        // Periodic scheduling replaces the displacement trigger. The controller
        // continues the accepted curve; safety replanning has its own callback.
        if (nominalReplanDue(false))
        {
          changeFSMExecState(REPLAN_TRAJ, "PERIODIC");
          performNominalReplan();
        }
      }
      else if ((info->start_pos_ - pos).norm() < replan_thresh_)
      {
        // cout << "near start" << endl;
        return;
      }
      else
      {
        changeFSMExecState(REPLAN_TRAJ, "FSM");
      }
      break;
    }

    case EMERGENCY_STOP:
    {

      if (flag_escape_emergency_) // Avoiding repeated calls
      {
        callEmergencyStop(odom_pos_);
      }
      else
      {
        if (enable_fail_safe_ && !need_hover_stop_ && odom_vel_.allFinite() && odom_vel_.head<2>().norm() < 0.15)
          changeFSMExecState(GEN_NEW_TRAJ, "FSM");
        else if (enable_fail_safe_ && need_hover_stop_ && odom_vel_.norm() < 0.1)
        {
          RCLCPP_INFO(node_->get_logger(),
                      "Exiting EMERGENCY_STOP; switching to WAIT_TARGET for a new target");
          need_hover_stop_ = false;
          have_target_ = false;
          trigger_ = false;
          changeFSMExecState(WAIT_TARGET, "EMERGENCY_EXIT");
        }
      }

      flag_escape_emergency_ = false;
      break;
    }
    }

    finishProcess();

    service_mission();

    data_disp_.header.stamp = node_->now();
    data_disp_pub_->publish(data_disp_);
  }

  void SCANReplanFSM::finishProcess()
  {
    if (replan_fail_count_ >= max_replan_fail_count_)
    {
      RCLCPP_WARN(node_->get_logger(),
                  "Replan failed %d times; emergency stop and wait for a new target", replan_fail_count_);
      replan_fail_count_ = 0;
      need_hover_stop_ = true;
      flag_escape_emergency_ = true;
      changeFSMExecState(EMERGENCY_STOP, "finishProcess");
    }
  }

  bool SCANReplanFSM::planFromCurrentTraj()
  {
    LocalTrajData *info = &planner_manager_->local_data_;
    rclcpp::Time time_now = node_->now();
    const double raw_t_cur = (time_now - info->start_time_).seconds();
    const double t_cur = std::min(std::max(raw_t_cur, 0.0), info->duration_);

    if (navi_mode_ == NAVI_MODE::REFERENCE_PATH)
    {
      const bool measured_start = info->start_time_.seconds() < 1e-5 ||
          raw_t_cur >= info->duration_ || replan_fail_count_ >= 3;
      auto sampled_origin = time_now;
      const rclcpp::Time *retry_origin = nullptr;
      if (measured_start) {
        start_pt_ = odom_pos_; start_vel_ = odom_vel_; start_acc_.setZero();
        planner_manager_->invalidateWarmStart();
      } else {
        start_pt_ = info->position_traj_.evaluateDeBoorT(t_cur);
        start_vel_ = info->velocity_traj_.evaluateDeBoorT(t_cur);
        start_acc_ = info->acceleration_traj_.evaluateDeBoorT(t_cur);
        if (planner_manager_->sampledTrajectoryOrigin(
              start_pt_, start_vel_, start_acc_, t_cur, sampled_origin))
          retry_origin = &sampled_origin;
      }
      // The two legacy init flags select the same initializer. One call owns
      // this tick's bounded prefix attempts and fully validated fallback.
      int reference_prefix_budget = kReferencePrefixProposalBudget;
      return callReboundReplan(false, false, &reference_prefix_budget,
                               measured_start ? -1.0 : t_cur, retry_origin);
    }

    start_pt_ = odom_pos_;
    start_vel_ = info->velocity_traj_.evaluateDeBoorT(t_cur);
    start_acc_ = info->acceleration_traj_.evaluateDeBoorT(t_cur);

    const Eigen::Vector2d to_goal = end_pt_.head<2>() - odom_pos_.head<2>();
    if (to_goal.norm() > 1e-3 && start_vel_.head<2>().dot(to_goal) < 0.0)
    {
      start_vel_.setZero();
      start_acc_.setZero();
    }

    if (!planner_manager_->planGlobalTraj(
            start_pt_,
            start_vel_,
            start_acc_,
            end_pt_,
            Eigen::Vector3d::Zero(),
            Eigen::Vector3d::Zero()))
    {
      RCLCPP_ERROR(node_->get_logger(),
                   "[navi_mode=%d] Unable to refresh global trajectory from odom to current target", navi_mode_);
      return false;
    }

    if (!adjustGlobalTargetIfOccupied())
      return false;

    bool success = callReboundReplan(true, false);
    if (!success)
    {
      success = callReboundReplan(true, true);
      if (!success)
        return false;
    }

    return true;
  }

  void SCANReplanFSM::setStartStateFromOdomOrCurrentTraj()
  {
    start_pt_ = odom_pos_;
    start_vel_ = odom_vel_;
    start_acc_.setZero();

    LocalTrajData *info = &planner_manager_->local_data_;
    if (info->start_time_.seconds() < 1e-5 || info->duration_ <= 1e-5)
      return;

    const double raw_t_cur = (node_->now() - info->start_time_).seconds();
    if (raw_t_cur < -1e-3 || raw_t_cur >= info->duration_ || replan_fail_count_ >= 3)
      return;

    const double t_cur = std::min(std::max(raw_t_cur, 0.0), info->duration_);
    start_vel_ = info->velocity_traj_.evaluateDeBoorT(t_cur);
    start_acc_ = info->acceleration_traj_.evaluateDeBoorT(t_cur);

    const Eigen::Vector2d to_goal = end_pt_.head<2>() - odom_pos_.head<2>();
    if (to_goal.norm() > 1e-3 && start_vel_.head<2>().dot(to_goal) < 0.0)
    {
      start_vel_.setZero();
      start_acc_.setZero();
    }
  }

  void SCANReplanFSM::checkCollisionCallback()
  {
    if (direct_io_.before_work) direct_io_.before_work();
    GridMap::RawContributorCacheScope callback_cache(*planner_manager_->grid_map_);
    // v31: check the executing curve against the newest received inputs, the
    // FSM's own body_pose included.
    const int fsm_odometry = takePendingOdometry(
        odom_sub_, node_->get_logger(), [this](nav_msgs::msg::Odometry::ConstSharedPtr msg) { odometryCallback(msg); });
    applyDueOdometry();
    planner_manager_->grid_map_->refreshSensorInputs("safety", fsm_odometry);
    updateLocalTrajTimeFreeze();

    LocalTrajData *info = &planner_manager_->local_data_;
    auto map = planner_manager_->grid_map_;

    if (exec_state_ == WAIT_TARGET || info->start_time_.seconds() < 1e-5) return;

    /* ---------- check trajectory ---------- */
    const double raw_t_cur = (node_->now() - info->start_time_).seconds();
    const auto collision = reactive_stair::checkFullCubicTrajectory(
        info->position_traj_, raw_t_cur, map->getResolution(), GridMap::collision_heading_lookahead_s,
        [&map](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
          return map->collisionTrajectoryYaw(p, ahead, v);
        },
        [&map](const Eigen::Vector3d &p, double yaw) { return map->getInflateOccupancy(p, yaw) != 0; });
    if (collision.clear()) return;
    planner_manager_->invalidateWarmStart();
    feasible_window_.valid = false;
    if (collision.status != reactive_stair::TrajectoryCheckStatus::Collision) {
      // Never evaluate/replan from an invalid old curve or a regressed clock.
      RCLCPP_ERROR(node_->get_logger(), "remaining_spline_invalid status=%d raw_t=%.9f samples=%zu",
                   static_cast<int>(collision.status), raw_t_cur, collision.samples);
      flag_escape_emergency_ = true;
      changeFSMExecState(EMERGENCY_STOP, "INVALID_SPLINE_INPUT");
      return;
    }
    const double t_cur = std::min(collision.duration_s, std::max(0.0, raw_t_cur));
    if (planFromCurrentTraj()) {
      changeFSMExecState(EXEC_TRAJ, "SAFETY");
      return;
    }
    if (collision.first_time_s - t_cur < emergency_time_) {
      RCLCPP_WARN(node_->get_logger(), "Obstacle discovered; emergency stop in %.3fs", collision.first_time_s - t_cur);
      changeFSMExecState(EMERGENCY_STOP, "SAFETY");
    } else {
      changeFSMExecState(REPLAN_TRAJ, "SAFETY");
    }
  }

  int SCANReplanFSM::recoveryTargetOccupancy(const Eigen::Vector3d &candidate, double yaw)
  {
    // Queued inputs can age out during search. Reuse the original ordered drain
    // at this decision boundary; the round's spline-derived start PVA is fixed.
    const int fsm_odometry = takePendingOdometry(
        odom_sub_, node_->get_logger(), [this](const auto &message) { odometryCallback(message); });
    applyDueOdometry();
    planner_manager_->grid_map_->refreshSensorInputs("reference_prefix", fsm_odometry);
    if (!candidate.allFinite() || !std::isfinite(yaw)) return 1;
    return planner_manager_->grid_map_->getInflateOccupancy(candidate, yaw);
  }

  bool SCANReplanFSM::trySteeringPrefix(bool random_initialization, const rclcpp::Time *origin)
  {
    // A later stall on the same route may need another fully checked prefix.
    const auto &info = planner_manager_->local_data_;
    const bool expired = info.start_time_.seconds() < 1e-5 ||
        (node_->now() - info.start_time_).seconds() >= info.duration_;
    const bool recovering = replan_fail_count_ >= 3 || expired;
    if (navi_mode_ != NAVI_MODE::REFERENCE_PATH ||
        (exec_state_ != GEN_NEW_TRAJ && !(exec_state_ == REPLAN_TRAJ && recovering)) ||
        (steering_prefix_generation_ == route_generation_ && !recovering) ||
        !start_pt_.allFinite() || !start_vel_.allFinite() || !start_acc_.allFinite() ||
        !odom_vel_.allFinite() || odom_vel_.norm() >= 0.15 || start_vel_.norm() >= 0.15)
      return false;
    takePendingOdometry(odom_sub_, node_->get_logger(),
        [this](const auto &message) { odometryCallback(message); });
    applyDueOdometry();
    auto map=planner_manager_->grid_map_;
    map->refreshSensorInputs("steering_prefix");
    const double resolution=map->getResolution();
    if (!map->planningInputsReady() || !std::isfinite(resolution) || resolution<=0 ||
        !odom_pos_.allFinite() || !odom_vel_.allFinite() || odom_vel_.norm()>=0.15 ||
        (start_pt_-odom_pos_).norm()>0.5*resolution) return false;
    const double measured_yaw=map->collisionSegmentYaw(odom_pos_,odom_pos_);
    if(!std::isfinite(measured_yaw))return false;
    struct Proposal { double reach; Eigen::Vector3d target; bool reverse; };
    std::vector<Proposal> proposals;
    const double pi=std::acos(-1.0);
    // Preserve the original near-forward proposals first. From a measured
    // stop, also consider a checked turn toward a side/back escape direction.
    for(double offset:{0.,pi/32.,-pi/32.,pi/16.,-pi/16.,pi/8.,-pi/8.,pi/4.,-pi/4.,pi/2.,-pi/2.,pi}) {
      const bool reverse=std::abs(offset-pi)<1e-12;
      const double turn=reverse?0.0:offset;
      const double yaw=measured_yaw+offset;
      const Eigen::Vector3d direction(std::cos(yaw),std::sin(yaw),0);
      const Eigen::Vector3d target=start_pt_+resolution*direction;
      bool rotation_clear=true;
      const int rotation_steps=std::max(8,static_cast<int>(std::ceil(std::abs(turn)/(pi/128.))));
      for(int j=0;j<=rotation_steps;++j) {
        const double intermediate=measured_yaw+turn*j/double(rotation_steps);
        if(map->getInflateOccupancy(start_pt_,intermediate)!=0 ||
           map->getInflateOccupancy(odom_pos_,intermediate)!=0)rotation_clear=false;
      }
      if(!rotation_clear || !planner_manager_->hasLocalTranslation(start_pt_,target) ||
         !map->collisionFreeSegment(start_pt_,target) || map->getInflateOccupancy(target,measured_yaw)!=0)continue;
      double reach=resolution;
      for(int cells=2;cells<=4;++cells) {
        if(!map->collisionFreeSegment(start_pt_,start_pt_+cells*resolution*direction))break;
        reach=cells*resolution;
      }
      if(reach>resolution)proposals.push_back({reach,target,reverse});
    }
    std::stable_sort(proposals.begin(),proposals.end(),[](const Proposal&a,const Proposal&b){return a.reach>b.reach;});
    size_t optimizer_attempts=0;
    for(const auto &proposal:proposals) {
      if(optimizer_attempts++>=5)break; // Keep the original expensive-proposal cap.
      // Refresh evidence, not the immutable start PVA or its original epoch.
      recoveryTargetOccupancy(proposal.target,measured_yaw);
      if(!map->planningInputsReady() || !std::isfinite(map->collisionSegmentYaw(odom_pos_,odom_pos_)))return false;
      const auto prior_local=planner_manager_->local_data_;
      if(!planner_manager_->reboundReplan(start_pt_,start_vel_,start_acc_,proposal.target,
          Eigen::Vector3d::Zero(),true,random_initialization,origin))continue;
      if(proposal.reverse) {
        // The normal tangent-based footprint is pi-symmetric. Also require the
        // complete curve to be clear at the measured heading held by this backup.
        const auto fixed=reactive_stair::checkFullCubicTrajectory(
          planner_manager_->local_data_.position_traj_,0.0,resolution,GridMap::collision_heading_lookahead_s,
          [&](const Eigen::Vector3d&,const Eigen::Vector3d&,const Eigen::Vector3d&){return measured_yaw;},
          [&](const Eigen::Vector3d&p,double yaw){return map->getInflateOccupancy(p,yaw)!=0;});
        if(!fixed.clear()||!map->mapperHealthy()) {
          planner_manager_->local_data_=prior_local;
          planner_manager_->publication_lease_.reset();
          planner_manager_->publication_check_.clear=false;
          planner_manager_->invalidateWarmStart();
          continue;
        }
      }
      steering_prefix_reverse_=proposal.reverse;
      local_target_pt_=proposal.target;
      local_target_vel_.setZero();
      local_target_time_=-1.0; // Off-reference steering is not reference progress.
      feasible_window_.valid=false;
      steering_prefix_generation_=route_generation_;
      planner_manager_->invalidateWarmStart();
      RCLCPP_INFO(node_->get_logger(),"V167_STEERING_PREFIX generation=%ld reverse=%d length=%.9f corridor=%.9f target=[%.9f,%.9f,%.9f]",
        static_cast<long>(steering_prefix_generation_),steering_prefix_reverse_,(proposal.target-start_pt_).norm(),proposal.reach,
        proposal.target.x(),proposal.target.y(),proposal.target.z());
      return true;
    }
    return false;
  }

  bool SCANReplanFSM::callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj, int *reference_prefix_budget, double warm_curve_time, const rclcpp::Time *retry_origin)
  {

    steering_prefix_reverse_=false;
    const bool have_local_target = getLocalTarget();
    if (!have_local_target) {
      planner_manager_->invalidateWarmStart();
      feasible_window_.valid = false;
    }

    planner_manager_->setWarmStartContext(warmStartIdentity(), warmGoalContext(), warm_curve_time);

    bool plan_success =
        have_local_target && planner_manager_->reboundReplan(start_pt_, start_vel_, start_acc_, local_target_pt_, local_target_vel_, (have_new_target_ || flag_use_poly_init), flag_randomPolyTraj, retry_origin);
    have_new_target_ = false;

    const bool reference = navi_mode_ == NAVI_MODE::REFERENCE_PATH;
    int per_round_budget = kReferencePrefixProposalBudget;
    int &remaining = reference_prefix_budget ? *reference_prefix_budget : per_round_budget;
    double candidate_t = local_target_time_;
    RCLCPP_WARN(node_->get_logger(), "[DEBUG-prefix-01] reference=%d remaining=%d local=%.12f projection=%.12f frontier=%.12f", reference, remaining, local_target_time_, local_projection_time_, reference_frontier_time_);
    while (!plan_success && have_local_target && reference && remaining > 0) {
      --remaining;  // Count considered proposals, including rejected endpoints.
      candidate_t = local_projection_time_ + 0.5 * (candidate_t - local_projection_time_);
      if (!std::isfinite(candidate_t) || candidate_t <= local_projection_time_ ||
          candidate_t > reference_frontier_time_) continue;
      const Eigen::Vector3d candidate = planner_manager_->global_data_.getPosition(candidate_t);
      if (!candidate.allFinite() || !planner_manager_->hasLocalTranslation(start_pt_, candidate)) continue;
      const double yaw = estimateYawFromSegment(start_pt_, candidate);
      const int occupancy = recoveryTargetOccupancy(candidate, yaw);
      RCLCPP_WARN(node_->get_logger(), "[DEBUG-prefix-01] candidate t=%.12f xyz=[%.12f,%.12f,%.12f] yaw=%.12f occ=%d", candidate_t,candidate.x(),candidate.y(),candidate.z(),yaw,occupancy);
      if (candidate_t > 0.9 && candidate_t < 1.2) {
        planner_manager_->grid_map_->logInitialSplineCollision(start_pt_, yaw);
        planner_manager_->grid_map_->logInitialSplineCollision(start_pt_ + Eigen::Vector3d(0.05,0,0), yaw);
      }
      if (!std::isfinite(yaw) || occupancy != 0) continue;

      local_target_pt_ = candidate;
      local_target_vel_.setZero();
      local_target_time_ = candidate_t;
      RCLCPP_INFO(node_->get_logger(),
                  "reference_prefix_proposal time=%.12f projected=%.12f remaining=%d xyz=[%.12f,%.12f,%.12f]",
                  candidate_t, local_projection_time_, remaining, candidate.x(), candidate.y(), candidate.z());
      // Every shorter target goes through the complete native planner, with
      // the same start PVA and zero terminal velocity. No seed-only fallback.
      plan_success = planner_manager_->reboundReplan(start_pt_, start_vel_, start_acc_,
          local_target_pt_, local_target_vel_, true, flag_randomPolyTraj, retry_origin);
    }
    const bool steering_prefix = !plan_success && reference &&
        trySteeringPrefix(flag_randomPolyTraj,retry_origin);
    if(steering_prefix)plan_success=true;
    if (plan_success && reference && !steering_prefix) {
      rememberFeasibleWindow();
      // This marks the accepted planning window end, not measured execution.
      planner_manager_->global_data_.last_progress_time_ = local_target_time_;
      RCLCPP_INFO(node_->get_logger(), "reference_window_committed time=%.12f full_duration=%.12f",
                  local_target_time_, planner_manager_->global_data_.global_duration_);
    }

    if (!plan_success) feasible_window_.valid = false;
    cout << "final_plan_success=" << plan_success << endl;

    if (plan_success)
    {

      auto info = &planner_manager_->local_data_;
      last_freeze_traj_id_ = info->traj_id_;
      last_freeze_update_time_ = node_->now();

      /* publish traj */
      scan_planner_msgs::msg::Bspline bspline;
      bspline.order = 3;
      bspline.reverse_motion=steering_prefix_reverse_;
      bspline.start_time = info->start_time_;
      bspline.traj_id = info->traj_id_;

      Eigen::MatrixXd pos_pts = info->position_traj_.getControlPoint();
      bspline.pos_pts.reserve(pos_pts.cols());
      for (int i = 0; i < pos_pts.cols(); ++i)
      {
        geometry_msgs::msg::Point pt;
        pt.x = pos_pts(0, i);
        pt.y = pos_pts(1, i);
        pt.z = pos_pts(2, i);
        bspline.pos_pts.push_back(pt);
      }

      Eigen::VectorXd knots = info->position_traj_.getKnot();
      bspline.knots.reserve(knots.rows());
      for (int i = 0; i < knots.rows(); ++i)
      {
        bspline.knots.push_back(knots(i));
      }

      publishSpline(bspline);
      planner_manager_->publication_lease_.reset();

      visualization_->displayOptimalTraj(info->position_traj_, 0);
    }

    return plan_success;
  }

  bool SCANReplanFSM::callEmergencyStop(Eigen::Vector3d stop_pos)
  {
    planner_manager_->invalidateWarmStart();
    feasible_window_.valid = false;

    planner_manager_->EmergencyStop(stop_pos);
    last_freeze_traj_id_ = planner_manager_->local_data_.traj_id_;
    last_freeze_update_time_ = node_->now();

    auto info = &planner_manager_->local_data_;

    /* publish traj */
    scan_planner_msgs::msg::Bspline bspline;
    bspline.emergency_stop = true;
    bspline.order = 3;
    bspline.start_time = info->start_time_;
    bspline.traj_id = info->traj_id_;

    Eigen::MatrixXd pos_pts = info->position_traj_.getControlPoint();
    bspline.pos_pts.reserve(pos_pts.cols());
    for (int i = 0; i < pos_pts.cols(); ++i)
    {
      geometry_msgs::msg::Point pt;
      pt.x = pos_pts(0, i);
      pt.y = pos_pts(1, i);
      pt.z = pos_pts(2, i);
      bspline.pos_pts.push_back(pt);
    }

    Eigen::VectorXd knots = info->position_traj_.getKnot();
    bspline.knots.reserve(knots.rows());
    for (int i = 0; i < knots.rows(); ++i)
    {
      bspline.knots.push_back(knots(i));
    }

    publishSpline(bspline);

    return true;
  }

  Eigen::Vector3d SCANReplanFSM::warmGoalContext() const
  {
    if (!have_requested_goal_pose_) return end_pt_;
    const auto &p = requested_goal_pose_.position;
    return Eigen::Vector3d(p.x, p.y, p.z);
  }

  std::string SCANReplanFSM::warmStartIdentity() const
  {
    std::ostringstream identity;
    if (navi_mode_ == NAVI_MODE::REFERENCE_PATH && route_generation_ > 0) {
      identity << route_generation_;
      if (have_requested_goal_pose_) {
        const auto &q = requested_goal_pose_.orientation;
        identity << " requested_orientation " << std::setprecision(17)
            << q.x << ' ' << q.y << ' ' << q.z << ' ' << q.w;
      }
    }
    return identity.str();
  }

  bool SCANReplanFSM::canPreserveReferenceBinding() const
  {
    const auto &manager = *planner_manager_;
    auto &curve = planner_manager_->local_data_;
    const auto binding = manager.warmStartBinding();
    const auto now = node_->now();
    if (curve.traj_id_ < 1 || binding.trajectory_id != curve.traj_id_ ||
        now.get_clock_type() != curve.start_time_.get_clock_type()) return false;
    const double age = (now - curve.start_time_).seconds();
    return navi_mode_ == NAVI_MODE::REFERENCE_PATH && have_requested_goal_pose_ &&
        curve.traj_id_ >= 1 && binding.trajectory_id == curve.traj_id_ &&
        binding.context == warmStartIdentity() &&
        (binding.goal.array() == warmGoalContext().array()).all() &&
        binding.map == manager.grid_map_.get() &&
        std::isfinite(age) && age >= 0.0 && std::isfinite(curve.duration_) && age < curve.duration_ &&
        reactive_stair::validSplineLayout(curve.position_traj_.getControlPoint(), curve.position_traj_.getKnot(), 3);
  }

  void SCANReplanFSM::reprojectFeasibleWindow()
  {
    auto &hint = feasible_window_;
    auto &global = planner_manager_->global_data_;
    const double duration = reference_frontier_time_;
    const double step = std::max(0.01, planning_horizon_ / 20.0 / planner_manager_->pp_.max_vel_);
    if (!hint.valid || !hint.world_geometry_valid || hint.generation != route_generation_ ||
        hint.map != planner_manager_->grid_map_.get() || !hint.endpoint_world.allFinite() ||
        !hint.projection_world.allFinite() || !hint.measured_world.allFinite() || !hint.growth_world.allFinite() ||
        !std::isfinite(duration) || duration <= 0.0 || !std::isfinite(step) || step <= 0.0) {
      hint.valid = false;
      return;
    }
    auto project = [&](const Eigen::Vector3d &point, bool refine) {
      double best = 0.0, distance = (global.getPosition(0.0) - point).squaredNorm();
      for (double t = step; t < duration; t += step) {
        const double d = (global.getPosition(t) - point).squaredNorm();
        if (d < distance) { distance = d; best = t; }
      }
      const double end_distance = (global.getPosition(duration) - point).squaredNorm();
      if (end_distance < distance) best = duration;
      if (refine) {
        double left = std::max(0.0, best - step), right = std::min(duration, best + step);
        for (int i = 0; i < 24; ++i) {
          const double a = left + (right-left)/3.0, b = right - (right-left)/3.0;
          if ((global.getPosition(a)-point).squaredNorm() <= (global.getPosition(b)-point).squaredNorm()) right = b;
          else left = a;
        }
        // Include boundaries: a trimmed reference may begin ahead of the old anchor.
        const double candidate = (left+right)/2.0;
        if ((global.getPosition(candidate)-point).squaredNorm() < (global.getPosition(best)-point).squaredNorm()) best=candidate;
      }
      return best;
    };
    const double projection = project(hint.projection_world, false);
    const double endpoint = project(hint.endpoint_world, true);
    const double measured = project(odom_pos_, false);
    const double growth = project(hint.growth_world, false);
    const Eigen::Vector3d mapped = global.getPosition(endpoint);
    // Geometry is only a proposal. Native newest-input/connector/final-curve gates still decide.
    if (!mapped.allFinite() || (mapped-hint.endpoint_world).norm() > planner_manager_->grid_map_->getResolution() ||
        !std::isfinite(endpoint) || endpoint <= projection || !std::isfinite(measured) || !std::isfinite(growth)) {
      hint.valid = false;
      return;
    }
    hint.goal = warmGoalContext(); hint.span = endpoint-projection;
    hint.projection = projection; hint.measured_projection = measured; hint.growth_projection = growth;
    hint.endpoint_world = mapped; hint.projection_world = global.getPosition(projection);
    hint.measured_world = global.getPosition(measured); hint.growth_world = global.getPosition(growth);
    RCLCPP_INFO(node_->get_logger(), "V53_REFRESH_REPROJECT projection=%.12f endpoint=%.12f span=%.12f stamp=%.12f", projection, endpoint, hint.span, hint.stamp);
  }

  void SCANReplanFSM::rememberFeasibleWindow()
  {
    const double span = local_target_time_ - local_projection_time_;
    if (route_generation_ <= 0 || !std::isfinite(span) || span <= 0.0 ||
        !std::isfinite(local_measured_projection_time_) || local_measured_projection_time_ < 0.0) {
      feasible_window_.valid = false;
      return;
    }
    // Keep the growth anchor across equal-span successes; otherwise motion
    // would never accumulate enough to try extending the window.
    const bool keep_growth = feasible_window_.valid && std::abs(feasible_window_.span - span) < 1e-9;
    const double growth = keep_growth ? feasible_window_.growth_projection : local_measured_projection_time_;
    const auto growth_world = keep_growth ? feasible_window_.growth_world :
        planner_manager_->global_data_.getPosition(local_measured_projection_time_);
    feasible_window_.valid = true;
    feasible_window_.generation = route_generation_;
    feasible_window_.map = planner_manager_->grid_map_.get();
    feasible_window_.goal = warmGoalContext();
    feasible_window_.span = span;
    feasible_window_.projection = local_projection_time_;
    feasible_window_.measured_projection = local_measured_projection_time_;
    feasible_window_.growth_projection = growth;
    feasible_window_.stamp = node_->now().seconds();
    feasible_window_.endpoint_world = planner_manager_->global_data_.getPosition(local_target_time_);
    feasible_window_.projection_world = planner_manager_->global_data_.getPosition(local_projection_time_);
    feasible_window_.measured_world = planner_manager_->global_data_.getPosition(local_measured_projection_time_);
    feasible_window_.growth_world = growth_world;
    feasible_window_.world_geometry_valid = feasible_window_.endpoint_world.allFinite() &&
        feasible_window_.projection_world.allFinite() && feasible_window_.measured_world.allFinite() && growth_world.allFinite();
  }

  bool SCANReplanFSM::reuseFeasibleWindow(double projection, double nominal_target,
                                         double step, double &target, Eigen::Vector3d &point)
  {
    auto &hint = feasible_window_;
    if (!hint.valid) return false;
    const double now = node_->now().seconds();
    auto map = planner_manager_->grid_map_;
    const bool same_identity = route_generation_ > 0 && hint.generation == route_generation_;
    if (!same_identity || hint.map != map.get() || !(hint.goal.array() == warmGoalContext().array()).all() ||
        !std::isfinite(hint.span) || hint.span <= 0.0 || !std::isfinite(hint.stamp) ||
        !std::isfinite(hint.projection) || !std::isfinite(hint.measured_projection) ||
        !std::isfinite(hint.growth_projection) || !std::isfinite(local_measured_projection_time_) ||
        !std::isfinite(now) || now < hint.stamp || now - hint.stamp > 1.0 ||
        !std::isfinite(projection) || !std::isfinite(nominal_target) || !std::isfinite(step) || step <= 0.0 ||
        projection + step < hint.projection || projection - hint.projection > hint.span ||
        local_measured_projection_time_ + step < hint.measured_projection ||
        local_measured_projection_time_ - hint.measured_projection > hint.span) {
      hint.valid = false;
      return false;
    }
    double span = hint.span;
    if (local_measured_projection_time_ - hint.growth_projection >= 0.5 * span) span += step;
    const double proposed = std::min(nominal_target, projection + span);
    if (!std::isfinite(proposed) || proposed <= projection || proposed > reference_frontier_time_) {
      hint.valid = false;
      return false;
    }
    // Let the unchanged terminal/neighbor handling select an already shorter
    // nominal target. Never move the final goal or its orientation.
    if (proposed >= nominal_target) return false;
    const Eigen::Vector3d candidate = planner_manager_->global_data_.getPosition(proposed);
    const double yaw = estimateYawFromSegment(start_pt_, candidate);
    if (!candidate.allFinite() || !std::isfinite(yaw) ||
        !planner_manager_->hasLocalTranslation(start_pt_, candidate) ||
        map->getInflateOccupancy(start_pt_, yaw) != 0 ||
        map->getInflateOccupancy(candidate, yaw) != 0) {
      hint.valid = false;
      return false;
    }
    target = proposed;
    point = candidate;
    RCLCPP_INFO(node_->get_logger(),
        "V47_WINDOW_HINT projected=%.12f nominal=%.12f selected=%.12f span=%.12f growth=%d measured=%.12f",
        projection, nominal_target, proposed, span, span > hint.span, local_measured_projection_time_);
    return true;
  }

  bool SCANReplanFSM::getLocalTarget()
  {
    reactive_stair::PlanningProfile::Scope profile(planner_manager_->grid_map_->planning_profile_, reactive_stair::PlanningProfile::Target);
    const double max_vel = planner_manager_->pp_.max_vel_;
    const double max_acc = planner_manager_->pp_.max_acc_;
    const bool reference = navi_mode_ == NAVI_MODE::REFERENCE_PATH;
    if (!reference) feasible_window_.valid = false;
    local_target_time_ = local_projection_time_ = local_measured_projection_time_ = -1.0;
    if (reference) {
      local_target_pt_.setZero();
      local_target_vel_.setZero();
      if (!start_pt_.allFinite() || !start_vel_.allFinite() || !start_acc_.allFinite() ||
          !odom_pos_.allFinite() || !end_pt_.allFinite() ||
          !std::isfinite(max_vel) || max_vel <= 0.0 || !std::isfinite(max_acc) ||
          !std::isfinite(planning_horizon_) || planning_horizon_ <= 0.0 ||
          !adjustGlobalTargetIfOccupied()) {
        feasible_window_.valid = false;
        return false;
      }
    }
    const double duration = reference ? reference_frontier_time_ : planner_manager_->global_data_.global_duration_;
    const Eigen::Vector3d selection_end = reference
        ? (reference_neighbor_target_ ? reference_neighbor_point_ : planner_manager_->global_data_.getPosition(duration))
        : end_pt_;
    double t_step = max_vel > 1e-6 ? planning_horizon_ / 20.0 / max_vel : 0.01;
    t_step = std::max(t_step, 0.01);
    if (reference && !std::isfinite(t_step)) return false;

    double t_proj = 0.0;
    double min_dist_to_start = 9999.0;
    double min_dist_to_odom = std::numeric_limits<double>::infinity();
    for (double t = 0.0; t < duration; t += t_step)
    {
      Eigen::Vector3d pos_t = planner_manager_->global_data_.getPosition(t);
      if (reference && !pos_t.allFinite()) return false;
      if (reference) {
        const double dist_to_odom = (pos_t - odom_pos_).norm();
        if (dist_to_odom < min_dist_to_odom) {
          min_dist_to_odom = dist_to_odom;
          local_measured_projection_time_ = t;
        }
      }
      double dist_to_start = (pos_t - start_pt_).norm();
      if (dist_to_start < min_dist_to_start)
      {
        min_dist_to_start = dist_to_start;
        t_proj = t;
      }
    }

    double target_t = duration;
    double total_dist = 0.0;
    bool target_found = false;
    Eigen::Vector3d prev_pos = planner_manager_->global_data_.getPosition(t_proj);
    local_target_pt_ = selection_end;

    for (double t = t_proj; t < duration; t += t_step)
    {
      Eigen::Vector3d pos_t = planner_manager_->global_data_.getPosition(t);
      if (reference && !pos_t.allFinite()) return false;
      total_dist += (pos_t - prev_pos).norm();
      if (total_dist >= planning_horizon_)
      {
        local_target_pt_ = pos_t;
        target_t = t;
        target_found = true;
        break;
      }
      prev_pos = pos_t;
    }
    if (!reference)
      planner_manager_->global_data_.last_progress_time_ = target_found ? target_t : duration;

    const bool reused_window = reference && reuseFeasibleWindow(
        t_proj, target_t, t_step, target_t, local_target_pt_);

    auto targetOccupancy = [&](const Eigen::Vector3d &pt) {
      if (reference && !pt.allFinite()) return 1;
      const double yaw = estimateYawFromSegment(reference ? start_pt_ : odom_pos_, pt);
      if (reference && !std::isfinite(yaw)) return 1;
      return planner_manager_->grid_map_->getInflateOccupancy(pt, yaw);
    };

    if (targetOccupancy(local_target_pt_) != 0)
    {
      bool found_free_target = false;
      double adjusted_t = target_t;

      for (double dt = 0.0; dt <= duration; dt += t_step)
      {
        double t_forward = target_t + dt;
        if (t_forward <= duration)
        {
          Eigen::Vector3d pt = planner_manager_->global_data_.getPosition(t_forward);
          if (targetOccupancy(pt) == 0)
          {
            local_target_pt_ = pt;
            adjusted_t = t_forward;
            found_free_target = true;
            break;
          }
        }

        double t_backward = target_t - dt;
        if (t_backward >= std::max(0.0, t_proj))
        {
          Eigen::Vector3d pt = planner_manager_->global_data_.getPosition(t_backward);
          if (targetOccupancy(pt) == 0)
          {
            local_target_pt_ = pt;
            adjusted_t = t_backward;
            found_free_target = true;
            break;
          }
        }
      }

      if (found_free_target)
      {
        RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 1000,
                             "Local target was adjusted to a nearby collision-free point");
        target_t = adjusted_t;
      }
      else
      {
        RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 1000,
                             "Local target is in collision and no nearby free target was found");
        if (reference) return false;
      }
    }

    const double braking_distance = max_acc > 1e-6
        ? (max_vel * max_vel) / (2.0 * max_acc)
        : std::numeric_limits<double>::infinity();
    if (reused_window || (selection_end - local_target_pt_).norm() < braking_distance)
    {
      // local_target_vel_ = (end_pt_ - init_pt_).normalized() * planner_manager_->pp_.max_vel_ * (( end_pt_ - local_target_pt_ ).norm() / ((planner_manager_->pp_.max_vel_*planner_manager_->pp_.max_vel_)/(2*planner_manager_->pp_.max_acc_)));
      // cout << "A" << endl;
      local_target_vel_ = Eigen::Vector3d::Zero();
    }
    else
    {
      local_target_vel_ = planner_manager_->global_data_.getVelocity(target_t);
      if (local_target_vel_.norm() > max_vel)
        local_target_vel_ = local_target_vel_.normalized() * max_vel;
      // cout << "AA" << endl;
    }
    if (reference && (!local_target_pt_.allFinite() || !local_target_vel_.allFinite() ||
                      !std::isfinite(target_t) || target_t <= t_proj || target_t > duration ||
                      !planner_manager_->hasLocalTranslation(start_pt_, local_target_pt_))) return false;
    local_target_time_ = target_t;
    local_projection_time_ = t_proj;
    return true;
  }

} // namespace scan_planner

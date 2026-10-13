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
  template <typename T>
  T load_parameter(rclcpp::Node *node, const std::string &name, const T &default_value)
  {
    if (!node->has_parameter(name)) node->declare_parameter<T>(name, default_value);
    return node->get_parameter(name).get_value<T>();
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
} // namespace

namespace scan_planner
{

  void SCANReplanFSM::init(rclcpp::Node *node)
  {
    node_ = node;
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
    planner_manager_->initPlanModules(node_, visualization_);

    /* callback */
    exec_timer_ = node_->create_wall_timer(std::chrono::milliseconds(10),
                                           std::bind(&SCANReplanFSM::execFSMCallback, this));
    safety_timer_ = node_->create_wall_timer(std::chrono::milliseconds(50),
                                             std::bind(&SCANReplanFSM::checkCollisionCallback, this));
    odom_sub_ = node_->create_subscription<nav_msgs::msg::Odometry>(
        "body_pose", rclcpp::SensorDataQoS(),
        std::bind(&SCANReplanFSM::odometryCallback, this, std::placeholders::_1));
    go2_execution_frozen_sub_ = node_->create_subscription<std_msgs::msg::Bool>(
        "planning/go2_execution_frozen", 10,
        std::bind(&SCANReplanFSM::go2ExecutionFrozenCallback, this, std::placeholders::_1));

    bspline_pub_ = node_->create_publisher<scan_planner_msgs::msg::Bspline>("planning/bspline", 10);
    p2b_admission_pub_ = node_->create_publisher<scan_planner_msgs::msg::P2BAdmission>("/p2b/scan_admission", 10);
    p2b_route_sub_ = node_->create_subscription<scan_planner_msgs::msg::P2BRoute>(
        "/p2b/route", rclcpp::QoS(1).reliable(),
        std::bind(&SCANReplanFSM::p2bRouteCallback, this, std::placeholders::_1));
    p2b_cancel_sub_ = node_->create_subscription<scan_planner_msgs::msg::P2BCancel>(
        "/p2b/scan_cancel", rclcpp::QoS(10).reliable(),
        std::bind(&SCANReplanFSM::p2bCancelCallback, this, std::placeholders::_1));
    data_disp_pub_ = node_->create_publisher<scan_planner_msgs::msg::DataDisp>("planning/data_display", 100);
    self_inflation_pub_ = node_->create_publisher<visualization_msgs::msg::Marker>(
        "self_inflation", rclcpp::QoS(1).reliable().transient_local());

    if (navi_mode_ == NAVI_MODE::MANUAL_TARGET)
      goal_sub_ = node_->create_subscription<geometry_msgs::msg::PoseStamped>(
          "move_base_simple/goal", 1,
          std::bind(&SCANReplanFSM::rvizGoalCallback, this, std::placeholders::_1));
    else if (navi_mode_ == NAVI_MODE::REFERENCE_PATH)
      path_sub_ = node_->create_subscription<nav_msgs::msg::Path>(
          "initial_path", rclcpp::QoS(1).reliable().transient_local(),
          std::bind(&SCANReplanFSM::pathCallback, this, std::placeholders::_1));
    else if (navi_mode_ == NAVI_MODE::PRESET_TARGET)
      RCLCPP_INFO(node_->get_logger(), "Preset waypoint mode will start after the first odometry message");
    else
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

  bool SCANReplanFSM::planGlobalTrajByWaypoints(const std::vector<Eigen::Vector3d> &waypoints)
  {
    planner_manager_->invalidateWarmStart();
    feasible_window_.valid = false; // Regenerated geometry has a new time parameterization.
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
        Eigen::Vector3d::Zero());

    if (!success)
    {
      RCLCPP_ERROR(node_->get_logger(), "Unable to generate global trajectory from waypoints");
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
      return false;
    if (!map || duration < 1e-3)
      return true;

    constexpr double sample_dt = 0.05;
    const int sample_num = std::max(1, static_cast<int>(std::ceil(duration / sample_dt)));
    const Eigen::Vector3d final_pt = global_data.global_traj_.evaluate(duration);
    const Eigen::Vector3d final_prev = global_data.global_traj_.evaluate(duration * (sample_num - 1) / sample_num);
    if (reference && (!final_pt.allFinite() || !final_prev.allFinite())) return false;
    const double final_yaw = estimateYawFromSegment(final_prev, final_pt);
    if (reference && !std::isfinite(final_yaw)) return false;
    const int final_occ = map->getInflateOccupancy(final_pt, final_yaw);
    if (reference ? final_occ == 0 : final_occ <= 0) {
      if (reference) reference_frontier_time_ = duration;
      return true;
    }

    if (reference) {
      const auto path = planner_manager_->findGoalNeighborhoodPath(start_pt_, final_pt, goal_neighbor_tolerance_);
      if (!path.empty()) {
        if (path.size() > 1 && (path.back() - final_pt).norm() <= goal_neighbor_tolerance_ &&
            planner_manager_->hasLocalTranslation(start_pt_, path.back())) {
          reference_neighbor_point_ = path.back();
          reference_frontier_time_ = duration;
          reference_neighbor_target_ = true;
          RCLCPP_INFO(node_->get_logger(), "reference_goal_neighbor xyz=[%.12f,%.12f,%.12f] displacement=%.12f reached_path_points=%zu final_goal_unchanged=1",
                      path.back().x(), path.back().y(), path.back().z(), (path.back()-final_pt).norm(), path.size());
          return true;
        }
      }
    }

    for (int i = sample_num; i >= 0; --i)
    {
      const double t = duration * i / sample_num;
      const double prev_t = duration * std::max(0, i - 1) / sample_num;
      const Eigen::Vector3d pt = global_data.global_traj_.evaluate(t);
      const Eigen::Vector3d prev_pt = global_data.global_traj_.evaluate(prev_t);

      if (reference && (!pt.allFinite() || !prev_pt.allFinite())) return false;
      const double yaw = estimateYawFromSegment(prev_pt, pt);
      if (reference && !std::isfinite(yaw)) return false;
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
    return false;
  }


  void SCANReplanFSM::p2bRouteCallback(scan_planner_msgs::msg::P2BRoute::ConstSharedPtr msg)
  {
    if (!msg) return;
    P2BIdentity candidate;
    candidate.run_id = msg->run_id;
    candidate.epoch = msg->epoch;
    candidate.request_id = msg->request_id;
    candidate.goal_id = msg->goal_id;
    candidate.route_id = msg->route_id;
    candidate.command_id = msg->command_id;
    candidate.generation = msg->generation;
    candidate.map_epoch = msg->map_epoch;
    candidate.map_revision = msg->map_revision;
    auto publish_candidate = [&](const std::string &status, const std::string &message, bool hold_confirmed=false, bool measured_stillness_confirmed=false) {
      if (!p2b_admission_pub_) return;
      scan_planner_msgs::msg::P2BAdmission out;
      out.run_id = candidate.run_id;
      out.epoch = candidate.epoch;
      out.request_id = candidate.request_id;
      out.goal_id = candidate.goal_id;
      out.route_id = candidate.route_id;
      out.command_id = candidate.command_id;
      out.generation = candidate.generation;
      out.map_epoch = candidate.map_epoch;
      out.map_revision = candidate.map_revision;
      out.consumer = "fsm";
      out.status = status;
      out.message = message;
      out.hold_confirmed = hold_confirmed;
      out.measured_stillness_confirmed = measured_stillness_confirmed;
      out.traj_id = planner_manager_ ? planner_manager_->local_data_.traj_id_ : 0;
      p2b_admission_pub_->publish(out);
    };
    if (candidate.run_id.empty() || candidate.route_id.empty() || candidate.command_id.empty() || candidate.generation <= 0)
    {
      publish_candidate("rejected", "missing_p2b_identity");
      return;
    }
    if (candidate.generation <= p2b_cancelled_generation_high_water_)
    {
      publish_candidate("rejected", "generation_cancelled_before_route");
      return;
    }
    if (candidate.generation < p2b_route_generation_high_water_)
    {
      publish_candidate("rejected", "stale_route_generation");
      return;
    }
    if (!have_odom_)
    {
      publish_candidate("rejected", "no_odometry_for_p2b_route");
      return;
    }
    if (msg->path.poses.empty())
    {
      publish_candidate("rejected", "empty_p2b_route");
      return;
    }
    std::vector<Eigen::Vector3d> waypoints;
    std::string path_error;
    if (!prepareReferenceWaypoints(msg->path, body_height_, reference_path_min_distance_, waypoints, &path_error, reference_path_simplify_tolerance_))
    {
      publish_candidate("rejected", path_error);
      return;
    }
    const bool previous_have_p2b_identity = have_p2b_identity_;
    const P2BIdentity previous_identity = active_p2b_identity_;
    active_p2b_identity_ = candidate;
    have_p2b_identity_ = true;
    trigger_ = true;
    end_pt_ = waypoints.back();
    const bool success = planGlobalTrajByWaypoints(waypoints);
    if (success)
    {
      p2b_route_generation_high_water_ = std::max(p2b_route_generation_high_water_, candidate.generation);
      if (exec_state_ == WAIT_TARGET) changeFSMExecState(GEN_NEW_TRAJ, "P2B_ROUTE");
      else if (exec_state_ == EXEC_TRAJ) changeFSMExecState(REPLAN_TRAJ, "P2B_ROUTE");
      publishP2BAdmission("accepted", "p2b_route_accepted_by_scan_fsm");
    }
    else
    {
      publish_candidate("rejected", "scan_global_traj_failed");
      active_p2b_identity_ = previous_identity;
      have_p2b_identity_ = previous_have_p2b_identity;
    }
  }

  bool SCANReplanFSM::p2bIdentityMatches(const scan_planner_msgs::msg::P2BCancel &msg) const
  {
    return have_p2b_identity_ && msg.run_id == active_p2b_identity_.run_id && msg.epoch == active_p2b_identity_.epoch && msg.request_id == active_p2b_identity_.request_id && msg.goal_id == active_p2b_identity_.goal_id && msg.route_id == active_p2b_identity_.route_id && msg.command_id == active_p2b_identity_.command_id && msg.generation == active_p2b_identity_.generation;
  }

  void SCANReplanFSM::p2bCancelCallback(scan_planner_msgs::msg::P2BCancel::ConstSharedPtr msg)
  {
    if (!msg) return;
    auto publish_cancel = [&](const std::string &status, const std::string &message, bool hold_confirmed=false, bool measured_stillness_confirmed=false) {
      if (!p2b_admission_pub_) return;
      scan_planner_msgs::msg::P2BAdmission out;
      out.run_id = msg->run_id;
      out.epoch = msg->epoch;
      out.request_id = msg->request_id;
      out.goal_id = msg->goal_id;
      out.route_id = msg->route_id;
      out.command_id = msg->command_id;
      out.generation = msg->generation;
      out.map_epoch = msg->map_epoch;
      out.map_revision = msg->map_revision;
      out.consumer = "fsm";
      out.status = status;
      out.message = message;
      out.hold_confirmed = hold_confirmed;
      out.measured_stillness_confirmed = measured_stillness_confirmed;
      out.traj_id = planner_manager_ ? planner_manager_->local_data_.traj_id_ : 0;
      p2b_admission_pub_->publish(out);
    };
    if (!p2bIdentityMatches(*msg))
    {
      if (msg->generation >= p2b_route_generation_high_water_ && msg->generation > p2b_cancelled_generation_high_water_)
      {
        p2b_cancelled_generation_high_water_ = msg->generation;
        publish_cancel("stopped", msg->reason.empty() ? "idle_cancel_hold" : msg->reason, true, false);
      }
      return;
    }
    p2b_cancelled_generation_high_water_ = std::max(p2b_cancelled_generation_high_water_, msg->generation);
    need_hover_stop_ = true;
    have_target_ = false;
    trigger_ = false;
    active_waypoints_.clear();
    current_wp_ = 0;
    callEmergencyStop(odom_pos_);
    changeFSMExecState(EMERGENCY_STOP, "P2B_CANCEL");
    publishP2BAdmission("stopped", msg->reason.empty() ? "p2b_cancel_hold" : msg->reason, true, false);
  }

  void SCANReplanFSM::publishP2BAdmission(const std::string &status, const std::string &message, bool hold_confirmed, bool measured_stillness_confirmed)
  {
    if (!have_p2b_identity_ || !p2b_admission_pub_) return;
    scan_planner_msgs::msg::P2BAdmission out;
    out.run_id = active_p2b_identity_.run_id;
    out.epoch = active_p2b_identity_.epoch;
    out.request_id = active_p2b_identity_.request_id;
    out.goal_id = active_p2b_identity_.goal_id;
    out.route_id = active_p2b_identity_.route_id;
    out.command_id = active_p2b_identity_.command_id;
    out.generation = active_p2b_identity_.generation;
    out.map_epoch = active_p2b_identity_.map_epoch;
    out.map_revision = active_p2b_identity_.map_revision;
    out.consumer = "fsm";
    out.status = status;
    out.message = message;
    out.hold_confirmed = hold_confirmed;
    out.measured_stillness_confirmed = measured_stillness_confirmed;
    out.traj_id = planner_manager_ ? planner_manager_->local_data_.traj_id_ : 0;
    p2b_admission_pub_->publish(out);
  }

  void SCANReplanFSM::attachP2BIdentity(scan_planner_msgs::msg::Bspline &bspline) const
  {
    if (!have_p2b_identity_) return;
    bspline.run_id = active_p2b_identity_.run_id;
    bspline.epoch = active_p2b_identity_.epoch;
    bspline.request_id = active_p2b_identity_.request_id;
    bspline.goal_id = active_p2b_identity_.goal_id;
    bspline.route_id = active_p2b_identity_.route_id;
    bspline.command_id = active_p2b_identity_.command_id;
    bspline.generation = active_p2b_identity_.generation;
    bspline.map_epoch = active_p2b_identity_.map_epoch;
    bspline.map_revision = active_p2b_identity_.map_revision;
  }

  void SCANReplanFSM::pathCallback(nav_msgs::msg::Path::ConstSharedPtr msg)
  {
    if (p2b_explicit_mode_)
    {
      RCLCPP_WARN(node_->get_logger(), "Ignoring legacy initial_path in explicit P2B typed-route mode");
      return;
    }
    if (!msg || msg->poses.empty())
    {
      RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 1000,
                           "Received empty initial_path; ignoring");
      return;
    }

    if (!have_odom_)
    {
      RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 1000,
                           "No odometry yet; ignoring initial_path");
      return;
    }

    std::vector<Eigen::Vector3d> waypoints;
    std::string path_error;
    if (!prepareReferenceWaypoints(*msg, body_height_, reference_path_min_distance_,
                                   waypoints, &path_error,
                                   reference_path_simplify_tolerance_))
    {
      RCLCPP_WARN(node_->get_logger(), "Ignoring initial_path: %s", path_error.c_str());
      return;
    }

    RCLCPP_INFO(node_->get_logger(),
                "Reference path reduced from %zu poses to %zu trajectory waypoints",
                msg->poses.size(), waypoints.size());

    trigger_ = true;
    end_pt_ = waypoints.back();
    bool success = planGlobalTrajByWaypoints(waypoints);

    if (success)
    {
      /*** FSM ***/
      if (exec_state_ == WAIT_TARGET)
      {
        changeFSMExecState(GEN_NEW_TRAJ, "TRIG");
      }
      else if (exec_state_ == EXEC_TRAJ)
      {
        changeFSMExecState(REPLAN_TRAJ, "TRIG");
      }

      RCLCPP_INFO(node_->get_logger(), "Reference path accepted");
    }
    else
    {
      RCLCPP_ERROR(node_->get_logger(), "Unable to generate global trajectory from reference path");
    }
  }

  void SCANReplanFSM::odometryCallback(nav_msgs::msg::Odometry::ConstSharedPtr msg)
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

  void SCANReplanFSM::go2ExecutionFrozenCallback(std_msgs::msg::Bool::ConstSharedPtr msg)
  {
    go2_execution_frozen_ = msg->data;
  }

  void SCANReplanFSM::updateLocalTrajTimeFreeze()
  {
    const rclcpp::Time now = node_->now();
    double dt = (now - last_freeze_update_time_).seconds();
    last_freeze_update_time_ = now;

    if (dt <= 0.0 || dt > 0.2)
      return;

    LocalTrajData *info = &planner_manager_->local_data_;
    if (go2_execution_frozen_ && info->start_time_.seconds() > 1e-5)
      info->start_time_ += rclcpp::Duration::from_seconds(dt);
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

  std::string SCANReplanFSM::executionIdentity() const
  {
    if (navi_mode_ != NAVI_MODE::REFERENCE_PATH || !have_p2b_identity_) return {};
    const auto &id = active_p2b_identity_;
    std::ostringstream out;
    out << std::quoted(id.run_id) << ' ' << id.epoch << ' '
        << std::quoted(id.request_id) << ' ' << std::quoted(id.goal_id) << ' '
        << std::quoted(id.route_id) << ' ' << std::quoted(id.command_id) << ' '
        << id.generation << ' ' << std::quoted(id.map_epoch) << ' ' << id.map_revision;
    return out.str();
  }

  bool SCANReplanFSM::validateTimeoutContinuation()
  {
    auto map = planner_manager_->grid_map_;
    auto &info = planner_manager_->local_data_;
    const auto &owner = published_curve_owner_;
    if (go2_execution_frozen_ || !have_target_ || owner.identity.empty() ||
        owner.identity != executionIdentity() || owner.map != map.get() ||
        owner.traj_id != info.traj_id_ || owner.start_ns != info.start_time_.nanoseconds() ||
        !(owner.goal.array() == end_pt_.array()).all()) return false;
    map->checkPlanningDeadline("continuation_identity");
    const int applied = takePendingOdometry(odom_sub_, node_->get_logger(),
        [this](nav_msgs::msg::Odometry::ConstSharedPtr msg) { odometryCallback(msg); });
    map->refreshSensorInputs("timeout_continuation", applied);
    const double age = (node_->now() - info.start_time_).seconds();
    const double duration = info.position_traj_.getTimeSum();
    if (!std::isfinite(age) || age < 0.0 || !std::isfinite(duration) || age >= duration ||
        std::abs(duration - info.duration_) > 1e-6) return false;
    const auto check = reactive_stair::checkFullCubicTrajectory(
        info.position_traj_, age, map->getResolution(), GridMap::collision_heading_lookahead_s,
        [&map](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
          return map->collisionTrajectoryYaw(p, ahead, v);
        }, [&map](const Eigen::Vector3d &p, double yaw) { return map->getInflateOccupancy(p, yaw) != 0; });
    map->checkPlanningDeadline("continuation_complete");
    const double final_age = (node_->now() - info.start_time_).seconds();
    return check.clear() && final_age >= age && final_age < duration;
  }

  bool SCANReplanFSM::runBudgetedReplan(bool initial, bool random, PlanningDeadline::Clock::time_point started)
  {
    PlanningDeadline deadline(started);
    auto map = planner_manager_->grid_map_;
    GridMap::PlanningDeadlineScope budget_scope(*map, &deadline);
    // The manager can finish a candidate before message preparation times out.
    // Keep the actually published curve and progress transactional until publish.
    const auto old_local = planner_manager_->local_data_;
    const auto old_global = planner_manager_->global_data_;
    const auto old_window = feasible_window_;
    const bool old_new_target = have_new_target_;
    last_solve_continued_ = last_solve_stopped_ = false;
    bool success = false;
    const char *timeout_site = "none";
    try {
      deadline.check("round_start");
      if (initial) {
        setStartStateFromOdomOrCurrentTraj();
        success = callReboundReplan(true, random);
      } else success = planFromCurrentTraj();
      // Successful publication is the transaction boundary; do not unwind it.
      if (!success) deadline.check("round_failed");
    } catch (const PlanningTimeout &timeout) {
      timeout_site = timeout.site;
      planner_manager_->local_data_ = old_local;
      planner_manager_->global_data_ = old_global;
      feasible_window_ = old_window;
      have_new_target_ = old_new_target;
      planner_manager_->invalidateWarmStart();
      try {
        deadline.recovery();
        last_solve_continued_ = validateTimeoutContinuation();
      } catch (const PlanningTimeout &) { last_solve_continued_ = false; }
      if (!last_solve_continued_) {
        // Stop publication is never suppressed by an exhausted compute budget.
        // Backend controller hold and measured stillness remain separate gates.
        GridMap::PlanningDeadlineScope stop_scope(*map, nullptr);
        publishP2BAdmission("rejected", "native_solve_timeout");
        need_hover_stop_ = true;
        replan_fail_count_ = 0;
        callEmergencyStop(odom_pos_);
        flag_escape_emergency_ = false;
        last_solve_stopped_ = true;
        changeFSMExecState(EMERGENCY_STOP, "SOLVE_TIMEOUT");
      }
    }
    RCLCPP_INFO(node_->get_logger(),
        "V49_BUDGET_RESULT new_plan=%d continued=%d stopped=%d timeout_site=%s wall_ms=%.6f limit_ms=25.0 overrun=%d ros_s=%.9f",
        success, last_solve_continued_, last_solve_stopped_, timeout_site,
        deadline.elapsedMs(), deadline.elapsedMs() > 25.0, node_->now().seconds());
    return success;
  }

  void SCANReplanFSM::performNominalReplan()
  {
    if (go2_execution_frozen_ || !nominalReplanDue(true)) return;
    const auto started = std::chrono::steady_clock::now();
    const bool success = runBudgetedReplan();
    const double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - started).count();
    RCLCPP_INFO(node_->get_logger(), "nominal_replan_result success=%d wall_s=%.9f budget_s=%.9f overrun=%d",
                success, elapsed, 1.0 / replan_frequency_, elapsed > 1.0 / replan_frequency_);
    if (last_solve_stopped_) return;
    if (success || last_solve_continued_)
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
    // v31: start each planning-timer callback from the newest received inputs,
    // the FSM's own body_pose included.
    const int fsm_odometry = takePendingOdometry(
        odom_sub_, node_->get_logger(), [this](nav_msgs::msg::Odometry::ConstSharedPtr msg) { odometryCallback(msg); });
    planner_manager_->grid_map_->refreshSensorInputs("exec", fsm_odometry);
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

      // Eigen::Vector3d rot_x = odom_orient_.toRotationMatrix().block(0, 0, 3, 1);
      // start_yaw_(0)         = atan2(rot_x(1), rot_x(0));
      // start_yaw_(1) = start_yaw_(2) = 0.0;

      bool flag_random_poly_init;
      if (timesOfConsecutiveStateCalls().first == 1)
        flag_random_poly_init = false;
      else
        flag_random_poly_init = true;

      const auto initial_started = std::chrono::steady_clock::now();
      bool success = runBudgetedReplan(true, flag_random_poly_init);
      const double initial_elapsed = std::chrono::duration<double>(
          std::chrono::steady_clock::now() - initial_started).count();
      if (replan_frequency_ > 0.0)
        RCLCPP_INFO(node_->get_logger(), "nominal_replan_result success=%d wall_s=%.9f budget_s=%.9f overrun=%d",
            success, initial_elapsed, 1.0 / replan_frequency_, initial_elapsed > 1.0 / replan_frequency_);
      if (last_solve_stopped_) break;
      if (success || last_solve_continued_)
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

      const bool success = runBudgetedReplan();
      if (last_solve_stopped_) break;
      if (success || last_solve_continued_)
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
        if (!go2_execution_frozen_ && nominalReplanDue(false))
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
        if (enable_fail_safe_ && !need_hover_stop_ && odom_vel_.norm() < 0.1)
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

    data_disp_.header.stamp = node_->now();
    data_disp_pub_->publish(data_disp_);
  }

  void SCANReplanFSM::finishProcess()
  {
    if (replan_fail_count_ >= max_replan_fail_count_)
    {
      RCLCPP_WARN(node_->get_logger(),
                  "Replan failed %d times; emergency stop and wait for a new target", replan_fail_count_);
      publishP2BAdmission("rejected", "native_replan_exhausted");
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
    double t_cur = (time_now - info->start_time_).seconds();
    t_cur = std::min(std::max(t_cur, 0.0), info->duration_);

    //cout << "info->velocity_traj_=" << info->velocity_traj_.get_control_points() << endl;

    if (navi_mode_ == NAVI_MODE::REFERENCE_PATH)
    {
      start_pt_ = info->position_traj_.evaluateDeBoorT(t_cur);
      start_vel_ = info->velocity_traj_.evaluateDeBoorT(t_cur);
      start_acc_ = info->acceleration_traj_.evaluateDeBoorT(t_cur);

      // One shared prefix budget across all original initialization modes.
      int reference_prefix_budget = 3;
      bool success = callReboundReplan(false, false, &reference_prefix_budget, t_cur);
      if (!success)
      {
        success = callReboundReplan(true, false, &reference_prefix_budget, t_cur);
        if (!success)
        {
          success = callReboundReplan(true, true, &reference_prefix_budget, t_cur);
          if (!success)
            return false;
        }
      }

      return true;
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
    if (raw_t_cur < -1e-3 || raw_t_cur > info->duration_ + 0.2)
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
    GridMap::RawContributorCacheScope callback_cache(*planner_manager_->grid_map_);
    // v31: check the executing curve against the newest received inputs, the
    // FSM's own body_pose included.
    const int fsm_odometry = takePendingOdometry(
        odom_sub_, node_->get_logger(), [this](nav_msgs::msg::Odometry::ConstSharedPtr msg) { odometryCallback(msg); });
    planner_manager_->grid_map_->refreshSensorInputs("safety", fsm_odometry);
    updateLocalTrajTimeFreeze();

    LocalTrajData *info = &planner_manager_->local_data_;
    auto map = planner_manager_->grid_map_;

    if (exec_state_ == WAIT_TARGET || info->start_time_.seconds() < 1e-5)
      return;

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
    const bool success = runBudgetedReplan();
    if (last_solve_stopped_) return;
    if (success || last_solve_continued_) {
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

  bool SCANReplanFSM::callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj, int *reference_prefix_budget, double warm_curve_time)
  {

    if (planner_manager_->grid_map_->planning_deadline_) planner_manager_->grid_map_->planning_deadline_->compute();
    if (!getLocalTarget()) {
      planner_manager_->invalidateWarmStart();
      feasible_window_.valid = false;
      return false;
    }

    std::ostringstream warm_identity;
    if (navi_mode_ == NAVI_MODE::REFERENCE_PATH && have_p2b_identity_) {
      const auto &id = active_p2b_identity_;
      warm_identity << std::quoted(id.run_id) << ' ' << id.epoch << ' '
          << std::quoted(id.request_id) << ' ' << std::quoted(id.goal_id) << ' '
          << std::quoted(id.route_id) << ' ' << std::quoted(id.command_id) << ' '
          << id.generation << ' ' << std::quoted(id.map_epoch) << ' ' << id.map_revision;
    }
    planner_manager_->setWarmStartContext(warm_identity.str(), end_pt_, warm_curve_time);

    bool plan_success =
        planner_manager_->reboundReplan(start_pt_, start_vel_, start_acc_, local_target_pt_, local_target_vel_, (have_new_target_ || flag_use_poly_init), flag_randomPolyTraj);
    have_new_target_ = false;

    const bool reference = navi_mode_ == NAVI_MODE::REFERENCE_PATH;
    int per_round_budget = 3;
    int &remaining = reference_prefix_budget ? *reference_prefix_budget : per_round_budget;
    double candidate_t = local_target_time_;
    RCLCPP_WARN(node_->get_logger(), "[DEBUG-prefix-01] reference=%d remaining=%d local=%.12f projection=%.12f frontier=%.12f", reference, remaining, local_target_time_, local_projection_time_, reference_frontier_time_);
    while (!plan_success && reference && remaining > 0) {
      --remaining;  // Count considered proposals, including rejected endpoints.
      candidate_t = local_projection_time_ + 0.5 * (candidate_t - local_projection_time_);
      if (!std::isfinite(candidate_t) || candidate_t <= local_projection_time_ ||
          candidate_t > reference_frontier_time_) continue;
      const Eigen::Vector3d candidate = planner_manager_->global_data_.getPosition(candidate_t);
      if (!candidate.allFinite() || !planner_manager_->hasLocalTranslation(start_pt_, candidate)) continue;
      const double yaw = estimateYawFromSegment(start_pt_, candidate);
      RCLCPP_WARN(node_->get_logger(), "[DEBUG-prefix-01] candidate t=%.12f xyz=[%.12f,%.12f,%.12f] yaw=%.12f occ=%d", candidate_t,candidate.x(),candidate.y(),candidate.z(),yaw,planner_manager_->grid_map_->getInflateOccupancy(candidate,yaw));
      if (candidate_t > 0.9 && candidate_t < 1.2) {
        planner_manager_->grid_map_->logInitialSplineCollision(start_pt_, yaw);
        planner_manager_->grid_map_->logInitialSplineCollision(start_pt_ + Eigen::Vector3d(0.05,0,0), yaw);
      }
      if (!std::isfinite(yaw) || planner_manager_->grid_map_->getInflateOccupancy(candidate, yaw) != 0) continue;

      local_target_pt_ = candidate;
      local_target_vel_.setZero();
      local_target_time_ = candidate_t;
      RCLCPP_INFO(node_->get_logger(),
                  "reference_prefix_proposal time=%.12f projected=%.12f remaining=%d xyz=[%.12f,%.12f,%.12f]",
                  candidate_t, local_projection_time_, remaining, candidate.x(), candidate.y(), candidate.z());
      // Every shorter target goes through the complete native planner, with
      // the same start PVA and zero terminal velocity. No seed-only fallback.
      plan_success = planner_manager_->reboundReplan(start_pt_, start_vel_, start_acc_,
          local_target_pt_, local_target_vel_, true, flag_randomPolyTraj);
    }
    if (plan_success && reference) {
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

      /* publish traj */
      scan_planner_msgs::msg::Bspline bspline;
      bspline.order = 3;
      bspline.start_time = info->start_time_;
      bspline.traj_id = info->traj_id_;
      attachP2BIdentity(bspline);

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

      PublishedCurveOwner owner;
      owner.identity = executionIdentity();
      owner.goal = end_pt_;
      owner.map = planner_manager_->grid_map_.get();
      owner.traj_id = info->traj_id_;
      owner.start_ns = info->start_time_.nanoseconds();
      planner_manager_->grid_map_->checkPlanningDeadline("before_trajectory_publish");
      bspline_pub_->publish(bspline);
      published_curve_owner_ = std::move(owner);

      visualization_->displayOptimalTraj(info->position_traj_, 0);
    }

    return plan_success;
  }

  bool SCANReplanFSM::callEmergencyStop(Eigen::Vector3d stop_pos)
  {
    published_curve_owner_ = PublishedCurveOwner{};
    planner_manager_->invalidateWarmStart();
    feasible_window_.valid = false;

    planner_manager_->EmergencyStop(stop_pos);

    auto info = &planner_manager_->local_data_;

    /* publish traj */
    scan_planner_msgs::msg::Bspline bspline;
    bspline.emergency_stop = true;
    bspline.order = 3;
    bspline.start_time = info->start_time_;
    bspline.traj_id = info->traj_id_;
      attachP2BIdentity(bspline);

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

    bspline_pub_->publish(bspline);

    return true;
  }

  void SCANReplanFSM::rememberFeasibleWindow()
  {
    const double span = local_target_time_ - local_projection_time_;
    if (!have_p2b_identity_ || !std::isfinite(span) || span <= 0.0 ||
        !std::isfinite(local_measured_projection_time_) || local_measured_projection_time_ < 0.0) {
      feasible_window_.valid = false;
      return;
    }
    // Keep the growth anchor across equal-span successes; otherwise motion
    // would never accumulate enough to try extending the window.
    const double growth = feasible_window_.valid &&
        std::abs(feasible_window_.span - span) < 1e-9
        ? feasible_window_.growth_projection : local_measured_projection_time_;
    feasible_window_.valid = true;
    feasible_window_.identity = active_p2b_identity_;
    feasible_window_.map = planner_manager_->grid_map_.get();
    feasible_window_.goal = end_pt_;
    feasible_window_.span = span;
    feasible_window_.projection = local_projection_time_;
    feasible_window_.measured_projection = local_measured_projection_time_;
    feasible_window_.growth_projection = growth;
    feasible_window_.stamp = node_->now().seconds();
  }

  bool SCANReplanFSM::reuseFeasibleWindow(double projection, double nominal_target,
                                         double step, double &target, Eigen::Vector3d &point)
  {
    auto &hint = feasible_window_;
    if (!hint.valid) return false;
    const auto &a = hint.identity;
    const auto &b = active_p2b_identity_;
    const double now = node_->now().seconds();
    auto map = planner_manager_->grid_map_;
    const bool same_identity = have_p2b_identity_ &&
        a.run_id == b.run_id && a.epoch == b.epoch && a.request_id == b.request_id &&
        a.goal_id == b.goal_id && a.route_id == b.route_id && a.command_id == b.command_id &&
        a.generation == b.generation && a.map_epoch == b.map_epoch && a.map_revision == b.map_revision;
    if (!same_identity || hint.map != map.get() || !(hint.goal.array() == end_pt_.array()).all() ||
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
      planner_manager_->grid_map_->checkPlanningDeadline("target_selection");
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
      planner_manager_->grid_map_->checkPlanningDeadline("target_selection");
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
      planner_manager_->grid_map_->checkPlanningDeadline("target_selection");
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

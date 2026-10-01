#ifndef _SCAN_REPLAN_FSM_H_
#define _SCAN_REPLAN_FSM_H_

#include <Eigen/Eigen>
#include <algorithm>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <iostream>
#include <nav_msgs/msg/odometry.hpp>
#include <nav_msgs/msg/path.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/bool.hpp>
#include <vector>
#include <visualization_msgs/msg/marker.hpp>

#include <bspline_opt/bspline_optimizer.h>
#include <plan_env/grid_map.h>
#include <scan_planner_msgs/msg/bspline.hpp>
#include <scan_planner_msgs/msg/data_disp.hpp>
#include <scan_planner_msgs/msg/p2_b_admission.hpp>
#include <scan_planner_msgs/msg/p2_b_cancel.hpp>
#include <scan_planner_msgs/msg/p2_b_route.hpp>
#include <plan_manage/planner_manager.h>
#include <traj_utils/planning_visualization.h>

using std::vector;

namespace scan_planner
{

  struct P2BIdentity
  {
    std::string run_id;
    int64_t epoch{0};
    std::string request_id;
    std::string goal_id;
    std::string route_id;
    std::string command_id;
    int64_t generation{0};
    std::string map_epoch;
    int64_t map_revision{0};
  };

  class SCANReplanFSM
  {

  private:
    /* ---------- flag ---------- */
    enum FSM_EXEC_STATE
    {
      INIT,
      WAIT_TARGET,
      GEN_NEW_TRAJ,
      REPLAN_TRAJ,
      EXEC_TRAJ,
      EMERGENCY_STOP
    };
    enum NAVI_MODE
    {
      MANUAL_TARGET = 1,
      PRESET_TARGET = 2,
      REFERENCE_PATH = 3,
    };

    /* planning utils */
    SCANPlannerManager::Ptr planner_manager_;
    PlanningVisualization::Ptr visualization_;
    scan_planner_msgs::msg::DataDisp data_disp_;

    /* parameters */
    int navi_mode_; // 1 manual select, 2 hard code
    double no_replan_thresh_, replan_thresh_;
    double replan_frequency_{0.0}; // Zero preserves legacy distance scheduling.
    double last_nominal_replan_s_{-1.0}; // Selected clock; attempt start, not completion.
    double next_nominal_replan_s_{-1.0};
    double last_replan_clock_s_{-1.0};
    bool replan_use_wall_clock_{true};
    std::vector<Eigen::Vector3d> preset_waypoints_;
    int waypoint_num_;
    double planning_horizon_;
    double emergency_time_;
    double rviz_goal_height_;
    double self_inflation_z_up_, self_inflation_z_down_;
    double self_double_cylinder_radius_, self_double_cylinder_offset_;
    double body_height_;
    double reference_path_min_distance_, reference_path_simplify_tolerance_;
    std::string self_inflation_frame_id_;

    /* planning data */
    bool trigger_, have_target_, have_odom_, have_new_target_;
    bool preset_started_{false};
    bool rviz_height_ready_;
    bool go2_execution_frozen_;
    bool p2b_explicit_mode_{true};
    bool have_p2b_identity_{false};
    P2BIdentity active_p2b_identity_;
    int64_t p2b_route_generation_high_water_{0};
    int64_t p2b_cancelled_generation_high_water_{0};
    bool enable_fail_safe_, need_hover_stop_;
    FSM_EXEC_STATE exec_state_;
    int continuously_called_times_{0};
    int replan_fail_count_{0};
    int max_replan_fail_count_{1000};
    rclcpp::Time last_freeze_update_time_;

    Eigen::Vector3d odom_pos_, odom_vel_, odom_acc_; // odometry state
    Eigen::Quaterniond odom_orient_;

    Eigen::Vector3d init_pt_, start_pt_, start_vel_, start_acc_, start_yaw_; // start state
    Eigen::Vector3d end_pt_, end_vel_;                                       // goal state
    Eigen::Vector3d local_target_pt_, local_target_vel_;                     // local target state
    // Reference proposals do not change the admitted route or its goal.
    double reference_frontier_time_{-1.0};
    bool reference_neighbor_target_{false};
    double goal_neighbor_tolerance_{0.5};
    Eigen::Vector3d reference_neighbor_point_{Eigen::Vector3d::Zero()};
    double local_target_time_{-1.0}, local_projection_time_{-1.0};
    std::vector<Eigen::Vector3d> active_waypoints_;
    int current_wp_;

    bool flag_escape_emergency_;

    /* ROS utils */
    rclcpp::Node *node_{nullptr};
    rclcpp::TimerBase::SharedPtr exec_timer_, safety_timer_;
    rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr goal_sub_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr path_sub_;
    rclcpp::Subscription<scan_planner_msgs::msg::P2BRoute>::SharedPtr p2b_route_sub_;
    rclcpp::Subscription<scan_planner_msgs::msg::P2BCancel>::SharedPtr p2b_cancel_sub_;
    rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr go2_execution_frozen_sub_;
    rclcpp::Publisher<scan_planner_msgs::msg::Bspline>::SharedPtr bspline_pub_;
    rclcpp::Publisher<scan_planner_msgs::msg::DataDisp>::SharedPtr data_disp_pub_;
    rclcpp::Publisher<scan_planner_msgs::msg::P2BAdmission>::SharedPtr p2b_admission_pub_;
    rclcpp::Publisher<visualization_msgs::msg::Marker>::SharedPtr self_inflation_pub_;

    /* helper functions */
    bool callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj, int *reference_prefix_budget = nullptr); // front-end and back-end method
    bool callEmergencyStop(Eigen::Vector3d stop_pos);                          // front-end and back-end method
    bool planFromCurrentTraj();
    void setStartStateFromOdomOrCurrentTraj();

    /* return value: std::pair< Times of the same state be continuously called, current continuously called state > */
    void changeFSMExecState(FSM_EXEC_STATE new_state, string pos_call);
    std::pair<int, SCANReplanFSM::FSM_EXEC_STATE> timesOfConsecutiveStateCalls();
    void printFSMExecState();

    void planGlobalTrajbyGivenWps();
    bool planGlobalTrajByWaypoints(const std::vector<Eigen::Vector3d> &waypoints);
    bool planNextWaypoint();
    bool isWaypointSequenceMode() const;
    bool adjustGlobalTargetIfOccupied();
    bool getLocalTarget();
    void finishProcess();
    void publishSelfInflationMarker();
    double getOdomYaw() const;
    double estimateYawFromSegment(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const;
    void updateLocalTrajTimeFreeze();

    /* ROS functions */
    bool nominalReplanDue(bool mark_attempt);
    void performNominalReplan();
    void execFSMCallback();
    void checkCollisionCallback();
    void rvizGoalCallback(geometry_msgs::msg::PoseStamped::ConstSharedPtr msg);
    void waypointCallback(nav_msgs::msg::Path::ConstSharedPtr msg);
    void pathCallback(nav_msgs::msg::Path::ConstSharedPtr msg);
    void p2bRouteCallback(scan_planner_msgs::msg::P2BRoute::ConstSharedPtr msg);
    void p2bCancelCallback(scan_planner_msgs::msg::P2BCancel::ConstSharedPtr msg);
    bool p2bIdentityMatches(const scan_planner_msgs::msg::P2BCancel &msg) const;
    void publishP2BAdmission(const std::string &status, const std::string &message, bool hold_confirmed=false, bool measured_stillness_confirmed=false);
    void attachP2BIdentity(scan_planner_msgs::msg::Bspline &bspline) const;
    void odometryCallback(nav_msgs::msg::Odometry::ConstSharedPtr msg);
    void go2ExecutionFrozenCallback(std_msgs::msg::Bool::ConstSharedPtr msg);

    bool checkCollision();

  public:
    SCANReplanFSM(/* args */)
    {
    }
    ~SCANReplanFSM()
    {
    }

    void init(rclcpp::Node *node);

    EIGEN_MAKE_ALIGNED_OPERATOR_NEW
  };

} // namespace scan_planner

#endif

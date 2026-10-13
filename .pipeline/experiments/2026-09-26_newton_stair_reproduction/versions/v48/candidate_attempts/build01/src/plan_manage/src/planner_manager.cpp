#include <cmath>
#include <iomanip>
#include <sstream>
#include <bspline_opt/timed_cubic_initialization.h>
#include <plan_manage/seed_polyline_sampling.h>
#include <bspline_opt/full_trajectory_collision.h>
// #include <fstream>
#include <plan_manage/planner_manager.h>
#include <plan_manage/minimum_cruise.h>
#include <plan_manage/polyline_trajectory_utils.h>
#include <chrono>
#include <thread>
#include <limits>

namespace scan_planner
{
  // SECTION interfaces for setup and query

  SCANPlannerManager::SCANPlannerManager() {}

  SCANPlannerManager::~SCANPlannerManager() { std::cout << "des manager" << std::endl; }

  void SCANPlannerManager::initPlanModules(rclcpp::Node *node, PlanningVisualization::Ptr vis)
  {
    node_ = node;
    /* read algorithm parameters */
    const auto get_double = [node](const std::string &name, double default_value) {
      if (!node->has_parameter(name)) node->declare_parameter<double>(name, default_value);
      return node->get_parameter(name).as_double();
    };
    pp_.max_vel_ = get_double("manager.max_vel", -1.0);
    pp_.max_acc_ = get_double("manager.max_acc", -1.0);
    pp_.max_jerk_ = get_double("manager.max_jerk", -1.0);
    min_cruise_speed_ = get_double("manager.min_cruise_speed", 0.0);
    if (!std::isfinite(min_cruise_speed_) || min_cruise_speed_ < 0.0 ||
        (min_cruise_speed_ > 0.0 &&
         (!std::isfinite(pp_.max_vel_) || min_cruise_speed_ > pp_.max_vel_ ||
          !std::isfinite(pp_.max_acc_) || pp_.max_acc_ <= 0.0 ||
          !std::isfinite(pp_.max_jerk_) || pp_.max_jerk_ <= 0.0)))
      throw std::runtime_error("Invalid minimum cruise speed or nominal dynamic limits");
    RCLCPP_INFO(node_->get_logger(), "minimum_planned_cruise_speed=%.3f m/s; boundary ramps and stops exempt",
                min_cruise_speed_);

    pp_.vel_tolerance_ = get_double("optimization.vel_tolerance", 1.0);
    pp_.acc_tolerance_ = get_double("optimization.acc_tolerance", 1.0);
    pp_.feasibility_tolerance_ = get_double("manager.feasibility_tolerance", 0.0);
    pp_.ctrl_pt_dist = get_double("manager.control_points_distance", -1.0);
    pp_.planning_horizon_ = get_double("manager.planning_horizon", 5.0);
    if (!node->has_parameter("manager.resolution_aware_progress"))
      node->declare_parameter<bool>("manager.resolution_aware_progress", false);
    resolution_aware_progress_ = node->get_parameter("manager.resolution_aware_progress").as_bool();
    RCLCPP_INFO(node->get_logger(), "local_progress_mode=%s",
                resolution_aware_progress_ ? "map_resolution" : "legacy_0.2m");

    local_data_.traj_id_ = 0;
    grid_map_.reset(new GridMap);
    grid_map_->initMap(node_);

    bspline_optimizer_rebound_.reset(new BsplineOptimizer);
    bspline_optimizer_rebound_->setParam(node_);
    bspline_optimizer_rebound_->setEnvironment(grid_map_);
    bspline_optimizer_rebound_->a_star_.reset(new AStar);
    bspline_optimizer_rebound_->a_star_->initGridMap(grid_map_, Eigen::Vector3i(100, 100, 100));

    if (!node_->has_parameter("manager.use_upstream_search_plane"))
      node_->declare_parameter<bool>("manager.use_upstream_search_plane", false);
    bspline_optimizer_rebound_->a_star_->use_upstream_search_plane =
        node_->get_parameter("manager.use_upstream_search_plane").as_bool();
    if (!node_->has_parameter("manager.goal_approach_max_iterations"))
      node_->declare_parameter<int>("manager.goal_approach_max_iterations", 1000);
    const int approach_limit = node_->get_parameter("manager.goal_approach_max_iterations").as_int();
    if (approach_limit < 1 || approach_limit > 1000) throw std::runtime_error("Invalid goal approach limit");
    bspline_optimizer_rebound_->a_star_->goal_approach_max_iterations = approach_limit;
    visualization_ = vis;
  }

  // !SECTION

  bool SCANPlannerManager::hasLocalTranslation(const Eigen::Vector3d &start,
                                               const Eigen::Vector3d &target) const
  {
    if (!start.allFinite() || !target.allFinite()) return false;
    if (!resolution_aware_progress_) return (target - start).norm() >= 0.2;
    if (!grid_map_ || !grid_map_->isInMap(start) || !grid_map_->isInMap(target)) return false;
    const double resolution = grid_map_->getResolution();
    if (!std::isfinite(resolution) || resolution <= 0.0) return false;
    // Nav2 Smac 3c3db59 distinguishes same-cell and translated goals. Require
    // a full resolution as well so a tiny cross-boundary move is not progress.
    const double translation_cells = (target - start).head<2>().norm() / resolution;
    if (translation_cells + 1e-9 < 1.0) return false;
    Eigen::Vector3i start_cell, target_cell;
    grid_map_->posToIndex(start, start_cell);
    grid_map_->posToIndex(target, target_cell);
    return start_cell.x() != target_cell.x() || start_cell.y() != target_cell.y();
  }

  // SECTION rebond replanning

  void SCANPlannerManager::invalidateWarmStart()
  {
    accepted_warm_traj_id_ = -1;
    accepted_warm_context_.clear();
    accepted_warm_map_ = nullptr;
  }

  void SCANPlannerManager::setWarmStartContext(const std::string &identity,
      const Eigen::Vector3d &goal, double curve_time)
  {
    if (identity.empty() || !goal.allFinite() ||
        identity != accepted_warm_context_ || !(goal.array() == accepted_warm_goal_.array()).all())
      invalidateWarmStart();
    warm_context_ = identity;
    warm_goal_ = goal;
    warm_curve_time_ = curve_time;
  }

  bool SCANPlannerManager::makeWarmStartSeed(const Eigen::Vector3d &start,
      const Eigen::Vector3d &velocity, const Eigen::Vector3d &acceleration,
      const Eigen::Vector3d &target, vector<Eigen::Vector3d> &path, std::string &reason)
  {
    path.clear();
    auto reject = [&](const char *why) { reason = why; invalidateWarmStart(); return false; };
    if (warm_context_.empty() || accepted_warm_context_ != warm_context_ ||
        accepted_warm_traj_id_ < 1 || accepted_warm_traj_id_ != local_data_.traj_id_ ||
        accepted_warm_map_ != grid_map_.get() ||
        !(accepted_warm_goal_.array() == warm_goal_.array()).all()) return reject("identity_or_owner");
    auto curve = local_data_.position_traj_;
    const auto points = curve.getControlPoint();
    if (points.rows() != 3 || points.cols() < 4 ||
        !reactive_stair::validSplineLayout(points, curve.getKnot(), 3)) return reject("curve_layout");
    const double duration = curve.getTimeSum();
    const double age = (node_->now() - local_data_.start_time_).seconds();
    if (!std::isfinite(duration) || duration <= 0.0 || !std::isfinite(age) || age < 0.0 || age >= duration ||
        !std::isfinite(warm_curve_time_) || warm_curve_time_ < 0.0 || warm_curve_time_ >= duration ||
        warm_curve_time_ > age + 1e-6 || std::abs(local_data_.duration_ - duration) > 1e-6)
      return reject("curve_time");
    auto derivative = curve.getDerivative();
    auto second = derivative.getDerivative();
    if (!reactive_stair::validSplineLayout(derivative.getControlPoint(), derivative.getKnot(), 2) ||
        !reactive_stair::validSplineLayout(second.getControlPoint(), second.getKnot(), 1) ||
        !start.allFinite() || !velocity.allFinite() || !acceleration.allFinite() || !target.allFinite() ||
        (curve.evaluateDeBoorT(warm_curve_time_) - start).norm() > 1e-6 ||
        (derivative.evaluateDeBoorT(warm_curve_time_) - velocity).norm() > 1e-6 ||
        (second.evaluateDeBoorT(warm_curve_time_) - acceleration).norm() > 1e-6)
      return reject("start_pva");

    grid_map_->refreshSensorInputs("warm_seed_check");
    const auto check = reactive_stair::checkFullCubicTrajectory(curve, warm_curve_time_,
        grid_map_->getResolution(), GridMap::collision_heading_lookahead_s,
        [this](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
          return grid_map_->collisionTrajectoryYaw(p, ahead, v);
        }, [this](const Eigen::Vector3d &p, double yaw) { return grid_map_->getInflateOccupancy(p, yaw) != 0; });
    if (!check.clear()) return reject("remaining_curve_not_clear");

    // Upstream 348e8a5 remaining-curve sampling/resampling, without its unchecked
    // polynomial extension or linear-Z rewrite. The original endpoint/PVA stay exact.
    const size_t divisions = std::max<size_t>(1, check.samples - 1);
    vector<Eigen::Vector3d> samples;
    samples.reserve(divisions + 1);
    size_t closest = 0;
    double distance = std::numeric_limits<double>::infinity();
    for (size_t i = 0; i <= divisions; ++i) {
      const double t = i == divisions ? duration : warm_curve_time_ +
          (duration - warm_curve_time_) * static_cast<double>(i) / divisions;
      const Eigen::Vector3d sample = curve.evaluateDeBoorT(t);
      const double d = (sample - target).squaredNorm();
      if (d < distance) { distance = d; closest = i; }
      samples.push_back(sample);
    }
    if (closest == 0) return reject("no_remaining_progress");
    path.push_back(start);
    for (size_t i = 1; i <= closest; ++i)
      if ((samples[i] - path.back()).norm() > 1e-9) path.push_back(samples[i]);
    if ((target - path.back()).norm() > 1e-6) {
      if (!grid_map_->collisionFreeSegment(path.back(), target)) return reject("target_connector");
      path.push_back(target);
    } else path.back() = target;
    if (path.size() < 2 || !hasLocalTranslation(start, target)) return reject("seed_progress");
    // The reused portion is the already checked cubic, not an executed polyline.
    // Its resampled/refitted guess still undergoes every unchanged final gate.
    reason = "accepted";
    return true;
  }

  bool SCANPlannerManager::reboundReplan(Eigen::Vector3d start_pt, Eigen::Vector3d start_vel,
                                        Eigen::Vector3d start_acc, Eigen::Vector3d local_target_pt,
                                        Eigen::Vector3d local_target_vel, bool flag_polyInit, bool flag_randomPolyTraj)
  {
    GridMap::RawContributorCacheScope raw_cache_scope(*grid_map_);
    bool attempted = false;
    const int failures_before = continuous_failures_count_;
    bool used_warm = false;
    if (reboundReplanAttempt(start_pt, start_vel, start_acc, local_target_pt,
        local_target_vel, flag_polyInit, flag_randomPolyTraj, attempted, true, &used_warm)) {
      if (used_warm) RCLCPP_INFO(node_->get_logger(), "V48_WARM_RESULT accepted=1 graph_fallback=0");
      return true;
    }
    if (used_warm) {
      // A warm optimizer/refit rejection is not a failed original graph solve.
      // Retry the complete parent search/recovery chain from the same input PVA.
      invalidateWarmStart();
      continuous_failures_count_ = failures_before;
      RCLCPP_INFO(node_->get_logger(), "V48_WARM_RESULT accepted=0 graph_fallback=1");
      if (reboundReplanAttempt(start_pt, start_vel, start_acc, local_target_pt,
          local_target_vel, flag_polyInit, flag_randomPolyTraj, attempted)) return true;
    }
    if (!attempted || !bspline_optimizer_rebound_->optimizesHeight()) {
      invalidateWarmStart();
      return false;
    }
    // Keep the configured three-axis behavior first. SCAN's existing fixed-Z
    // mode can retain a feasible stair seed when smoothing lowers its height.
    struct RestoreHeightMode {
      BsplineOptimizer &optimizer;
      bool enabled;
      ~RestoreHeightMode() { optimizer.setOptimizeHeight(enabled); }
    } restore{*bspline_optimizer_rebound_, bspline_optimizer_rebound_->optimizesHeight()};
    bspline_optimizer_rebound_->setOptimizeHeight(false);
    continuous_failures_count_ = failures_before;
    RCLCPP_INFO(node_->get_logger(), "fixed_height_recovery_attempt; full planning gates retained");
    const bool accepted = reboundReplanAttempt(start_pt, start_vel, start_acc, local_target_pt,
        local_target_vel, flag_polyInit, flag_randomPolyTraj, attempted);
    RCLCPP_INFO(node_->get_logger(), "fixed_height_recovery_result accepted=%d", accepted);
    if (!accepted) invalidateWarmStart();
    return accepted;
  }

  bool SCANPlannerManager::reboundReplanAttempt(Eigen::Vector3d start_pt, Eigen::Vector3d start_vel,
                                        Eigen::Vector3d start_acc, Eigen::Vector3d local_target_pt,
                                        Eigen::Vector3d local_target_vel, bool flag_polyInit, bool flag_randomPolyTraj,
                                        bool &optimization_attempted, bool allow_warm_start,
                                        bool *used_warm_start)
  {
    optimization_attempted = false;
    if (used_warm_start) *used_warm_start = false;
    // v31: each replan attempt starts from the newest received inputs.
    grid_map_->refreshSensorInputs("replan_start");

    static int count = 0;
    std::cout << endl
              << "[rebo replan]: -------------------------------------" << count++ << std::endl;
    cout.precision(3);
    cout << "start: " << start_pt.transpose() << ", " << start_vel.transpose() << "\ngoal:" << local_target_pt.transpose() << ", " << local_target_vel.transpose()
         << endl;

    if (!hasLocalTranslation(start_pt, local_target_pt))
    {
      cout << "Close to goal" << endl;
      continuous_failures_count_++;
      return false;
    }

    auto t_start = std::chrono::steady_clock::now();
    double t_init = 0.0, t_opt = 0.0, t_refine = 0.0;

    /*** STEP 1: INIT ***/
    double ts = (start_pt - local_target_pt).norm() > 0.1 ? pp_.ctrl_pt_dist / pp_.max_vel_ * 1.2 : pp_.ctrl_pt_dist / pp_.max_vel_ * 5; // pp_.ctrl_pt_dist / pp_.max_vel_ is too tense, and will surely exceed the acc/vel limits
    vector<Eigen::Vector3d> point_set, start_end_derivatives;
    // Native graph initialization below owns the points, interval and PVA.
    // Do not evaluate a discarded legacy seed from an expired local curve.

    std::vector<Eigen::Vector3d> seed_path;
    std::string warm_reason;
    const auto warm_started = std::chrono::steady_clock::now();
    const bool warm = allow_warm_start && makeWarmStartSeed(start_pt, start_vel, start_acc,
        local_target_pt, seed_path, warm_reason);
    if (allow_warm_start)
      RCLCPP_INFO(node_->get_logger(), "V48_WARM_SEED selected=%d reason=%s nodes=%zu wall_ms=%.3f",
          warm, warm_reason.c_str(), seed_path.size(), std::chrono::duration<double, std::milli>(
          std::chrono::steady_clock::now() - warm_started).count());
    if (used_warm_start) *used_warm_start = warm;
    if (!warm) {
    // A stair seed must come from the same current collision model as its
    // optimizer and final safety check. A single endpoint-height line is not
    // a supported stair profile. No fallback bypasses a failed graph search.
    auto seed_search = bspline_optimizer_rebound_->a_star_;
    const auto seed_status = seed_search->AstarSearch(grid_map_->getResolution(), start_pt, local_target_pt, true);
    if (seed_status != ASTAR_RET::SUCCESS) {
      RCLCPP_WARN(node_->get_logger(), "reactive_stair_seed_search_failed status=%d", static_cast<int>(seed_status));
      continuous_failures_count_++;
      return false;
    }
    seed_path = seed_search->getPath();
    if (seed_path.size() < 2 || (seed_path.front() - start_pt).norm() > 1e-6 ||
        (seed_path.back() - local_target_pt).norm() > 1e-6) {
      RCLCPP_WARN(node_->get_logger(), "reactive_stair_seed_endpoint_mismatch");
      continuous_failures_count_++;
      return false;
    }
    // Search already checked the exact terminal connection. Do not overwrite
    // endpoints here: changing the last edge can change its footprint heading.
    for (size_t i = 1; i < seed_path.size(); ++i) {
      int blocked_sample = -1;
      if (!grid_map_->collisionFreeSegment(seed_path[i - 1], seed_path[i], &blocked_sample)) {
        RCLCPP_WARN(node_->get_logger(), "reactive_stair_seed_edge_blocked edge=%zu sample=%d", i, blocked_sample);
        continuous_failures_count_++;
        return false;
      }
    }
    // OMPL 1.7.0 eabb4d0 reduceVertices: simplify only after checkMotion.
    // Source/license: references/upstream/2026-09-27_ompl_seed_shortcut.
    // The original native search and every returned edge have already passed.
    // A failed direct connector keeps that original graph path unchanged.
    if (seed_path.size() > 2 &&
        grid_map_->collisionFreeSegment(seed_path.front(), seed_path.back())) {
      RCLCPP_INFO(node_->get_logger(), "verified_direct_seed_shortcut original_nodes=%zu", seed_path.size());
      const Eigen::Vector3d first = seed_path.front(), last = seed_path.back();
      seed_path = {first, last};
    }
    }
    // SCAN-Planner 348e8a5 planner_manager.cpp:210-231 (Apache-2.0):
    // use its control-point arc-length sampler, not the local quintic quota sampler.
    vector<double> pseudo_arc_length(1, 0.0);
    for (size_t i = 1; i < seed_path.size(); ++i)
      pseudo_arc_length.push_back(pseudo_arc_length.back() + (seed_path[i] - seed_path[i-1]).norm());
    double cps_dist = pp_.ctrl_pt_dist * 1.5;
    if (!std::isfinite(cps_dist) || cps_dist <= 0.0 ||
        !std::isfinite(pp_.max_vel_) || pp_.max_vel_ <= 0.0) return false;
    do {
      cps_dist /= 1.5;
      point_set.clear();
      double sample_length = 0.0;
      size_t id = 0;
      while (id <= pseudo_arc_length.size() - 2 && sample_length <= pseudo_arc_length.back()) {
        if (sample_length >= pseudo_arc_length[id] && sample_length < pseudo_arc_length[id + 1]) {
          point_set.push_back((sample_length - pseudo_arc_length[id]) / (pseudo_arc_length[id + 1] - pseudo_arc_length[id]) * seed_path[id + 1] +
              (pseudo_arc_length[id + 1] - sample_length) / (pseudo_arc_length[id + 1] - pseudo_arc_length[id]) * seed_path[id]);
          sample_length += cps_dist;
        } else ++id;
      }
      point_set.push_back(local_target_pt);
    } while (point_set.size() < 7);
    ts = cps_dist / pp_.max_vel_ * 1.2;
    RCLCPP_INFO(node_->get_logger(), "upstream_arclength_seed nodes=%zu samples=%zu spacing=%.12f interval=%.12f",
                seed_path.size(), point_set.size(), cps_dist, ts);
    if (warm && point_set.size() > pp_.planning_horizon_ / pp_.ctrl_pt_dist * 3) {
      continuous_failures_count_++;
      return false;
    }
    start_end_derivatives = {start_vel, local_target_vel, start_acc, Eigen::Vector3d::Zero()};
    RCLCPP_INFO(node_->get_logger(), "reactive_stair_seed_checked nodes=%zu samples=%zu", seed_path.size(), point_set.size());

    Eigen::MatrixXd ctrl_pts;
    // Diagnostic capture preserves the exact initializer input, before fitting.
    std::ostringstream seed_capture;
    seed_capture << std::setprecision(17) << "{\"interval\":" << ts
      << ",\"velocity_limit\":" << pp_.max_vel_ << ",\"acceleration_limit\":" << pp_.max_acc_
      << ",\"tolerance\":" << pp_.feasibility_tolerance_ << ",\"points\":[";
    for (size_t i = 0; i < point_set.size(); ++i) {
      if (i) seed_capture << ",";
      seed_capture << "[" << point_set[i].x() << "," << point_set[i].y() << "," << point_set[i].z() << "]";
    }
    seed_capture << "],\"derivatives\":[";
    for (size_t i = 0; i < start_end_derivatives.size(); ++i) {
      if (i) seed_capture << ",";
      const auto &d = start_end_derivatives[i];
      seed_capture << "[" << d.x() << "," << d.y() << "," << d.z() << "]";
    }
    seed_capture << "]}";
    RCLCPP_INFO(node_->get_logger(), "spline_seed_capture %s", seed_capture.str().c_str());
    if (!reactive_stair::fitCubicBoundaryPva(ts, point_set, start_end_derivatives, ctrl_pts)) {
      RCLCPP_WARN(node_->get_logger(), "spline_boundary_fit_failed");
      continuous_failures_count_++;
      return false;
    }
    RCLCPP_INFO(node_->get_logger(), "spline_geometry_initialized samples=%zu interval=%.12f duration=%.12f",
                point_set.size(), ts, ts * (point_set.size() - 1));

    vector<vector<Eigen::Vector3d>> a_star_paths;
    a_star_paths = bspline_optimizer_rebound_->initControlPoints(ctrl_pts, true);

    t_init = std::chrono::duration<double>(std::chrono::steady_clock::now() - t_start).count();

    static int vis_id = 0;
    visualization_->displayInitPathList(point_set, 0.2, 0);
    visualization_->displayAStarList(a_star_paths, vis_id);

    t_start = std::chrono::steady_clock::now();

    /*** STEP 2: OPTIMIZE ***/
    optimization_attempted = true;
    bool flag_step_1_success = bspline_optimizer_rebound_->BsplineOptimizeTrajRebound(ctrl_pts, ts);
    cout << "first_optimize_step_success=" << flag_step_1_success << endl;
    if (!flag_step_1_success)
    {
      // visualization_->displayOptimalList( ctrl_pts, vis_id );
      continuous_failures_count_++;
      return false;
    }
    //visualization_->displayOptimalList( ctrl_pts, vis_id );

    t_opt = std::chrono::duration<double>(std::chrono::steady_clock::now() - t_start).count();
    t_start = std::chrono::steady_clock::now();

    /*** STEP 3: REFINE(RE-ALLOCATE TIME) IF NECESSARY ***/
    UniformBspline pos = UniformBspline(ctrl_pts, 3, ts);
    const auto capture_curve = [&](const char *stage) {
      std::ostringstream record;
      record << std::setprecision(17) << "{\"stage\":\"" << stage << "\",\"controls\":[";
      const auto controls = pos.getControlPoint();
      const auto knots = pos.getKnot();
      for (int i = 0; i < controls.cols(); ++i) {
        if (i) record << ",";
        record << "[" << controls(0,i) << "," << controls(1,i) << "," << controls(2,i) << "]";
      }
      record << "],\"knots\":[";
      for (int i = 0; i < knots.size(); ++i) { if (i) record << ","; record << knots[i]; }
      record << "]}";
      RCLCPP_INFO(node_->get_logger(), "spline_curve_capture %s", record.str().c_str());
    };
    capture_curve("optimized");

    pos.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);

    bool flag_step_2_success = true;
    bool native_feasible = false;
    for (int adjustment = 0; adjustment <= 3; ++adjustment) {
      // Constructing a refined curve resets its physical-limit fields.
      pos.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);
      double ratio = 0.0;
      native_feasible = pos.checkFeasibility(ratio, false);
      if (native_feasible || adjustment == 3) break;
      if (!std::isfinite(ratio) || ratio <= 1.0) {
        flag_step_2_success = false;
        break;
      }
      Eigen::MatrixXd optimal_control_points;
      flag_step_2_success = refineTrajAlgo(pos, start_end_derivatives, ratio, ts, optimal_control_points);
      if (!flag_step_2_success) break;
      pos = UniformBspline(optimal_control_points, 3, ts);
      capture_curve("refined");
      RCLCPP_INFO(node_->get_logger(), "post_opt_time_adjustment iteration=%d ratio=%.12f duration=%.12f",
                  adjustment + 1, ratio, pos.getTimeSum());
    }
    flag_step_2_success = flag_step_2_success && native_feasible;

    if (flag_step_2_success && min_cruise_speed_ > 0.0) {
      flag_step_2_success = enforceMinimumCruise(pos, start_end_derivatives, ts);
      if (flag_step_2_success) capture_curve("minimum_cruise_checked");
    }

    // A later native soft refit may change PVA. Reject that drift rather than
    // claiming initialization constraints survived a subsequent retiming.
    if (flag_step_2_success && !reactive_stair::matchesBoundaryPva(
        pos, start_pt, local_target_pt, start_end_derivatives)) {
      RCLCPP_WARN(node_->get_logger(), "final_spline_boundary_pva_rejected");
      flag_step_2_success = false;
    }
    if (!flag_step_2_success || !checkDynamicFeasibility(pos))
    {
      printf("\033[34mThis refined trajectory is unsafe or dynamically infeasible. Skip publishing it.\n\033[0m");
      continuous_failures_count_++;
      return false;
    }

    t_refine = std::chrono::duration<double>(std::chrono::steady_clock::now() - t_start).count();

    // v31: judge the final curve against the newest received inputs.
    grid_map_->refreshSensorInputs("final_check");
    const auto collision_started = std::chrono::steady_clock::now();
    const auto collision = reactive_stair::checkFullCubicTrajectory(
        pos, 0.0, grid_map_->getResolution(), GridMap::collision_heading_lookahead_s,
        [this](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
          return grid_map_->collisionTrajectoryYaw(p, ahead, v);
        },
        [this](const Eigen::Vector3d &p, double yaw) { return grid_map_->getInflateOccupancy(p, yaw) != 0; });
    const double collision_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - collision_started).count();
    if (!collision.clear()) {
      RCLCPP_WARN(node_->get_logger(), "final_spline_rejected status=%d t=%.9f duration=%.9f samples=%zu wall_ms=%.3f",
                  static_cast<int>(collision.status), collision.first_time_s, collision.duration_s, collision.samples, collision_ms);
      continuous_failures_count_++;
      return false;
    }
    RCLCPP_INFO(node_->get_logger(), "full_spline_sampled_clear duration=%.9f samples=%zu wall_ms=%.3f",
                collision.duration_s, collision.samples, collision_ms);

    // save planned results
    updateTrajInfo(pos, node_->now());
    if (!warm_context_.empty() && warm_goal_.allFinite()) {
      accepted_warm_context_ = warm_context_;
      accepted_warm_goal_ = warm_goal_;
      accepted_warm_traj_id_ = local_data_.traj_id_;
      accepted_warm_map_ = grid_map_.get();
    }

    cout << "total time:\033[42m" << (t_init + t_opt + t_refine)
         << "\033[0m,optimize:" << (t_init + t_opt) << ",refine:" << t_refine << endl;

    // success. YoY
    continuous_failures_count_ = 0;
    return true;
  }

  std::vector<Eigen::Vector3d> SCANPlannerManager::findGoalNeighborhoodPath(
      const Eigen::Vector3d &start, const Eigen::Vector3d &goal, double tolerance) {
    if (!grid_map_ || !bspline_optimizer_rebound_ || !bspline_optimizer_rebound_->a_star_) return {};
    const auto search = bspline_optimizer_rebound_->a_star_;
    if (search->AstarSearch(grid_map_->getResolution(), start, goal, true, tolerance) != ASTAR_RET::SUCCESS) return {};
    return search->getPath();
  }

  bool SCANPlannerManager::EmergencyStop(Eigen::Vector3d stop_pos)
  {
    invalidateWarmStart();
    Eigen::MatrixXd control_points(3, 6);
    for (int i = 0; i < 6; i++)
    {
      control_points.col(i) = stop_pos;
    }

    updateTrajInfo(UniformBspline(control_points, 3, 1.0), node_->now());

    return true;
  }

  bool SCANPlannerManager::planGlobalTrajWaypoints(const Eigen::Vector3d &start_pos, const Eigen::Vector3d &start_vel, const Eigen::Vector3d &start_acc,
                                                  const std::vector<Eigen::Vector3d> &waypoints, const Eigen::Vector3d &end_vel, const Eigen::Vector3d &end_acc)
  {
    invalidateWarmStart();
    if (waypoints.empty())
      return false;

    vector<Eigen::Vector3d> points;
    points.push_back(start_pos);
    points.insert(points.end(), waypoints.begin(), waypoints.end());
    PolynomialTraj gl_traj;
    std::string error;
    if (!makePiecewiseLinearTrajectory(points, pp_.max_vel_, gl_traj, &error))
    {
      RCLCPP_ERROR(node_->get_logger(), "Unable to build polyline reference trajectory: %s", error.c_str());
      return false;
    }

    (void)start_vel;
    (void)start_acc;
    (void)end_vel;
    (void)end_acc;

    auto time_now = node_->now();
    global_data_.setGlobalTraj(gl_traj, time_now);

    return true;
  }

  bool SCANPlannerManager::planGlobalTraj(const Eigen::Vector3d &start_pos, const Eigen::Vector3d &start_vel, const Eigen::Vector3d &start_acc,
                                         const Eigen::Vector3d &end_pos, const Eigen::Vector3d &end_vel, const Eigen::Vector3d &end_acc)
  {
    invalidateWarmStart();

    // generate global reference trajectory

    vector<Eigen::Vector3d> points;
    points.push_back(start_pos);
    points.push_back(end_pos);

    // insert intermediate points if too far
    vector<Eigen::Vector3d> inter_points;
    const double dist_thresh = 4.0;

    for (size_t i = 0; i < points.size() - 1; ++i)
    {
      inter_points.push_back(points.at(i));
      double dist = (points.at(i + 1) - points.at(i)).norm();

      if (dist > dist_thresh)
      {
        int id_num = floor(dist / dist_thresh) + 1;

        for (int j = 1; j < id_num; ++j)
        {
          Eigen::Vector3d inter_pt =
              points.at(i) * (1.0 - double(j) / id_num) + points.at(i + 1) * double(j) / id_num;
          inter_points.push_back(inter_pt);
        }
      }
    }

    inter_points.push_back(points.back());

    // write position matrix
    int pt_num = inter_points.size();
    Eigen::MatrixXd pos(3, pt_num);
    for (int i = 0; i < pt_num; ++i)
      pos.col(i) = inter_points[i];

    Eigen::Vector3d zero(0, 0, 0);
    Eigen::VectorXd time(pt_num - 1);
    for (int i = 0; i < pt_num - 1; ++i)
    {
      time(i) = (pos.col(i + 1) - pos.col(i)).norm() / (pp_.max_vel_);
    }

    time(0) *= 2.0;
    time(time.rows() - 1) *= 2.0;

    PolynomialTraj gl_traj;
    if (pos.cols() >= 3)
      gl_traj = PolynomialTraj::minSnapTraj(pos, start_vel, end_vel, start_acc, end_acc, time);
    else if (pos.cols() == 2)
      gl_traj = PolynomialTraj::one_segment_traj_gen(start_pos, start_vel, start_acc, end_pos, end_vel, end_acc, time(0));
    else
      return false;

    auto time_now = node_->now();
    global_data_.setGlobalTraj(gl_traj, time_now);

    return true;
  }

  bool SCANPlannerManager::refineTrajAlgo(UniformBspline &traj, vector<Eigen::Vector3d> &start_end_derivative, double ratio, double &ts, Eigen::MatrixXd &optimal_control_points)
  {
    double t_inc;

    Eigen::MatrixXd ctrl_pts; // = traj.getControlPoint()

    // std::cout << "ratio: " << ratio << std::endl;
    if (!reparamBspline(traj, start_end_derivative, ratio, ctrl_pts, ts, t_inc)) return false;

    traj = UniformBspline(ctrl_pts, 3, ts);

    double t_step = traj.getTimeSum() / (ctrl_pts.cols() - 3);
    bspline_optimizer_rebound_->ref_pts_.clear();
    for (double t = 0; t < traj.getTimeSum() + 1e-4; t += t_step)
      bspline_optimizer_rebound_->ref_pts_.push_back(traj.evaluateDeBoorT(t));

    bool success = bspline_optimizer_rebound_->BsplineOptimizeTrajRefine(ctrl_pts, ts, optimal_control_points);

    return success;
  }

  void SCANPlannerManager::updateTrajInfo(const UniformBspline &position_traj, const rclcpp::Time time_now)
  {
    local_data_.start_time_ = time_now;
    local_data_.position_traj_ = position_traj;
    local_data_.velocity_traj_ = local_data_.position_traj_.getDerivative();
    local_data_.acceleration_traj_ = local_data_.velocity_traj_.getDerivative();
    local_data_.start_pos_ = local_data_.position_traj_.evaluateDeBoorT(0.0);
    local_data_.duration_ = local_data_.position_traj_.getTimeSum();
    local_data_.traj_id_ += 1;
  }

  bool SCANPlannerManager::checkDynamicFeasibility(UniformBspline position_traj)
  {
    UniformBspline vel_traj = position_traj.getDerivative();
    UniformBspline acc_traj = vel_traj.getDerivative();
    const double duration = position_traj.getTimeSum();
    const double sample_dt = std::max(0.01, std::min(0.05, duration / 50.0));
    const double vel_limit = pp_.max_vel_ + pp_.vel_tolerance_;
    const double acc_limit = pp_.max_acc_ + pp_.acc_tolerance_;

    for (double t = 0.0; t < duration + 1e-6; t += sample_dt)
    {
      const double tc = std::min(t, duration);
      Eigen::Vector3d vel = vel_traj.evaluateDeBoorT(tc);
      if (vel.norm() > vel_limit)
      {
        RCLCPP_WARN(node_->get_logger(),
                    "Dynamic feasibility failed: velocity at t=%.3f is %.3f > %.3f",
                    tc, vel.norm(), vel_limit);
        return false;
      }

      Eigen::Vector3d acc = acc_traj.evaluateDeBoorT(tc);
      if (acc.norm() > acc_limit)
      {
        RCLCPP_WARN(node_->get_logger(),
                    "Dynamic feasibility failed: acceleration at t=%.3f is %.3f > %.3f",
                    tc, acc.norm(), acc_limit);
        return false;
      }
    }

    return true;
  }

  bool SCANPlannerManager::enforceMinimumCruise(
      UniformBspline &curve, vector<Eigen::Vector3d> &boundary, double &interval)
  {
    if (min_cruise_speed_ == 0.0) return true;
    for (int attempt = 0; attempt <= 3; ++attempt) {
      const auto report = measureMinimumCruise(curve, min_cruise_speed_, pp_.max_acc_, pp_.max_jerk_);
      RCLCPP_INFO(node_->get_logger(),
          "minimum_cruise_check attempt=%d valid=%d passed=%d samples=%d min=%.9f requested=%.9f length=%.9f entry=%.9f exit=%.9f dt=%.9f",
          attempt, report.valid, report.passed, report.cruise_samples, report.minimum_speed,
          min_cruise_speed_, report.path_length, report.entry_distance, report.exit_distance, report.sample_dt);
      if (!report.valid) return false;
      if (report.passed) return true;
      if (attempt == 3 || report.minimum_speed <= 1e-6) break;
      // Reuse SCAN's native knot reallocation, boundary-PVA fit and refinement.
      // Limit each compression step; no downstream command-floor override.
      const double ratio = std::clamp(0.98 * report.minimum_speed / min_cruise_speed_, 0.7, 0.98);
      Eigen::MatrixXd controls;
      if (!refineTrajAlgo(curve, boundary, ratio, interval, controls)) return false;
      curve = UniformBspline(controls, 3, interval);
      curve.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);
      double feasibility_ratio = 0.0;
      if (!curve.checkFeasibility(feasibility_ratio, false) || !checkDynamicFeasibility(curve)) {
        RCLCPP_WARN(node_->get_logger(), "minimum_cruise_dynamic_limit_rejected");
        return false;
      }
    }
    RCLCPP_WARN(node_->get_logger(), "minimum_cruise_unreachable; no slower cruise published");
    return false;
  }

  bool SCANPlannerManager::reparamBspline(UniformBspline &bspline, vector<Eigen::Vector3d> &start_end_derivative, double ratio,
                                         Eigen::MatrixXd &ctrl_pts, double &dt, double &time_inc)
  {
    double time_origin = bspline.getTimeSum();
    int seg_num = bspline.getControlPoint().cols() - 3;
    // double length = bspline.getLength(0.1);
    // int seg_num = ceil(length / pp_.ctrl_pt_dist);

    bspline.lengthenTime(ratio);
    double duration = bspline.getTimeSum();
    dt = duration / double(seg_num);
    time_inc = duration - time_origin;

    vector<Eigen::Vector3d> point_set;
    for (double time = 0.0; time <= duration + 1e-4; time += dt)
    {
      point_set.push_back(bspline.evaluateDeBoorT(time));
    }
    return reactive_stair::fitCubicBoundaryPva(dt, point_set, start_end_derivative, ctrl_pts);
  }

} // namespace scan_planner

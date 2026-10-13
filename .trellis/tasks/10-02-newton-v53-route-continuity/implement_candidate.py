from pathlib import Path
N=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/scan75_reference_continuity_v53/src/plan_manage')
p=N/'include/plan_manage/scan_replan_fsm.h';s=p.read_text()
s=s.replace('    P2BIdentity active_p2b_identity_;','    P2BIdentity active_p2b_identity_;\n    bool have_requested_goal_pose_{false};\n    geometry_msgs::msg::Pose requested_goal_pose_;\n    Eigen::Vector3d warmGoalContext() const;\n    std::string warmStartIdentity() const;\n    bool canPreserveReferenceBinding() const;\n    void reprojectFeasibleWindow();')
s=s.replace('      P2BIdentity identity;','      P2BIdentity identity;\n      bool world_geometry_valid{false};\n      Eigen::Vector3d endpoint_world{Eigen::Vector3d::Zero()};\n      Eigen::Vector3d projection_world{Eigen::Vector3d::Zero()};\n      Eigen::Vector3d measured_world{Eigen::Vector3d::Zero()};\n      Eigen::Vector3d growth_world{Eigen::Vector3d::Zero()};')
s=s.replace('const std::vector<Eigen::Vector3d> &waypoints);','const std::vector<Eigen::Vector3d> &waypoints, bool preserve_binding = false);',1);p.write_text(s)
p=N/'src/scan_replan_fsm.cpp';s=p.read_text()
s=s.replace('  // v31: take the FSM', '''  bool sameOwner(const scan_planner::P2BIdentity &a, const scan_planner::P2BIdentity &b)
  {
    return a.run_id == b.run_id && a.epoch == b.epoch && a.request_id == b.request_id &&
        a.goal_id == b.goal_id && a.route_id == b.route_id && a.command_id == b.command_id &&
        a.generation == b.generation && a.map_epoch == b.map_epoch && a.map_revision == b.map_revision;
  }

  bool qualifiedGoal(const scan_planner_msgs::msg::P2BRoute &route)
  {
    const auto &p = route.goal_pose.position;
    const auto &q = route.goal_pose.orientation;
    const double norm2 = q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w;
    return route.has_goal_pose && std::isfinite(p.x) && std::isfinite(p.y) &&
        std::isfinite(p.z) && std::isfinite(norm2) && std::abs(norm2 - 1.0) <= 1e-6;
  }

  // v31: take the FSM''',1)
s=s.replace('  bool SCANReplanFSM::planGlobalTrajByWaypoints(const std::vector<Eigen::Vector3d> &waypoints)','  bool SCANReplanFSM::planGlobalTrajByWaypoints(const std::vector<Eigen::Vector3d> &waypoints, bool preserve_binding)')
s=s.replace('    planner_manager_->invalidateWarmStart();\n    feasible_window_.valid = false; // Regenerated geometry has a new time parameterization.','''    if (!preserve_binding) {
      planner_manager_->invalidateWarmStart();
      feasible_window_.valid = false;
    } // Compatible callbacks reproject geometry after successful regeneration.''',1)
start=s.index('    const bool previous_have_p2b_identity =',s.index('void SCANReplanFSM::p2bRouteCallback'))
end=s.index('\n  void SCANReplanFSM::p2bCancelCallback',start)
# Keep original callback ending, replace transaction body only.
old=s[start:end];tail=old[old.index('    const bool previous_have_p2b_identity ='):]
assert tail.rstrip().endswith('}')
s=s[:start]+'''    const bool previous_have_p2b_identity = have_p2b_identity_;
    const P2BIdentity previous_identity = active_p2b_identity_;
    const bool previous_goal_valid = have_requested_goal_pose_;
    const auto previous_goal = requested_goal_pose_;
    const auto previous_global = planner_manager_->global_data_;
    const auto previous_window = feasible_window_;
    const auto previous_end = end_pt_, previous_end_vel = end_vel_;
    const auto previous_neighbor = reference_neighbor_point_;
    const double previous_frontier = reference_frontier_time_;
    const bool previous_neighbor_target = reference_neighbor_target_;
    const bool previous_trigger = trigger_, previous_target = have_target_, previous_new = have_new_target_;
    const auto previous_context = planner_manager_->accepted_warm_context_;
    const auto previous_warm_goal = planner_manager_->accepted_warm_goal_;
    const int previous_warm_id = planner_manager_->accepted_warm_traj_id_;
    const auto previous_warm_map = planner_manager_->accepted_warm_map_;
    const bool goal_valid = qualifiedGoal(*msg);
    const bool compatible = previous_have_p2b_identity && sameOwner(previous_identity, candidate) &&
        previous_goal_valid && goal_valid && previous_goal == msg->goal_pose && canPreserveReferenceBinding();
    active_p2b_identity_ = candidate;
    have_p2b_identity_ = true;
    have_requested_goal_pose_ = goal_valid;
    requested_goal_pose_ = msg->goal_pose;
    trigger_ = true;
    end_pt_ = waypoints.back();
    const bool success = planGlobalTrajByWaypoints(waypoints, compatible);
    if (success)
    {
      if (compatible) reprojectFeasibleWindow();
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
      requested_goal_pose_ = previous_goal;
      have_requested_goal_pose_ = previous_goal_valid;
      planner_manager_->global_data_ = previous_global;
      feasible_window_ = previous_window;
      end_pt_ = previous_end; end_vel_ = previous_end_vel;
      reference_frontier_time_ = previous_frontier;
      reference_neighbor_point_ = previous_neighbor;
      reference_neighbor_target_ = previous_neighbor_target;
      trigger_ = previous_trigger; have_target_ = previous_target; have_new_target_ = previous_new;
      planner_manager_->accepted_warm_context_ = previous_context;
      planner_manager_->accepted_warm_goal_ = previous_warm_goal;
      planner_manager_->accepted_warm_traj_id_ = previous_warm_id;
      planner_manager_->accepted_warm_map_ = previous_warm_map;
    }
  }
''' + s[end:]
# Full owner context is unchanged for legacy messages; qualified requested orientation is exact.
a=s.index('    std::ostringstream warm_identity;',s.index('bool SCANReplanFSM::callReboundReplan'))
b=s.index('\n\n    bool plan_success',a)
s=s[:a]+'''    planner_manager_->setWarmStartContext(warmStartIdentity(), warmGoalContext(), warm_curve_time);'''+s[b:]
a=s.index('  void SCANReplanFSM::rememberFeasibleWindow()')
s=s[:a]+'''  Eigen::Vector3d SCANReplanFSM::warmGoalContext() const
  {
    if (!have_requested_goal_pose_) return end_pt_;
    const auto &p = requested_goal_pose_.position;
    return Eigen::Vector3d(p.x, p.y, p.z);
  }

  std::string SCANReplanFSM::warmStartIdentity() const
  {
    std::ostringstream identity;
    if (navi_mode_ == NAVI_MODE::REFERENCE_PATH && have_p2b_identity_) {
      const auto &id = active_p2b_identity_;
      identity << std::quoted(id.run_id) << ' ' << id.epoch << ' '
          << std::quoted(id.request_id) << ' ' << std::quoted(id.goal_id) << ' '
          << std::quoted(id.route_id) << ' ' << std::quoted(id.command_id) << ' '
          << id.generation << ' ' << std::quoted(id.map_epoch) << ' ' << id.map_revision;
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
    const auto &curve = manager.local_data_;
    const double age = (node_->now() - curve.start_time_).seconds();
    return navi_mode_ == NAVI_MODE::REFERENCE_PATH && have_requested_goal_pose_ &&
        curve.traj_id_ >= 1 && manager.accepted_warm_traj_id_ == curve.traj_id_ &&
        manager.accepted_warm_context_ == warmStartIdentity() &&
        (manager.accepted_warm_goal_.array() == warmGoalContext().array()).all() &&
        manager.accepted_warm_map_ == manager.grid_map_.get() &&
        std::isfinite(age) && age >= 0.0 && std::isfinite(curve.duration_) && age < curve.duration_ &&
        reactive_stair::validSplineLayout(curve.position_traj_.getControlPoint(), curve.position_traj_.getKnot(), 3);
  }

  void SCANReplanFSM::reprojectFeasibleWindow()
  {
    auto &hint = feasible_window_;
    auto &global = planner_manager_->global_data_;
    const double duration = reference_frontier_time_;
    const double step = std::max(0.01, planning_horizon_ / 20.0 / planner_manager_->pp_.max_vel_);
    if (!hint.valid || !hint.world_geometry_valid || !sameOwner(hint.identity, active_p2b_identity_) ||
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

'''+s[a:]
s=s.replace('    const double growth = feasible_window_.valid &&\n        std::abs(feasible_window_.span - span) < 1e-9\n        ? feasible_window_.growth_projection : local_measured_projection_time_;','''    const bool keep_growth = feasible_window_.valid && std::abs(feasible_window_.span - span) < 1e-9;
    const double growth = keep_growth ? feasible_window_.growth_projection : local_measured_projection_time_;
    const auto growth_world = keep_growth ? feasible_window_.growth_world :
        planner_manager_->global_data_.getPosition(local_measured_projection_time_);''')
s=s.replace('    feasible_window_.goal = end_pt_;','    feasible_window_.goal = warmGoalContext();',1)
s=s.replace('    feasible_window_.stamp = node_->now().seconds();','''    feasible_window_.stamp = node_->now().seconds();
    feasible_window_.endpoint_world = planner_manager_->global_data_.getPosition(local_target_time_);
    feasible_window_.projection_world = planner_manager_->global_data_.getPosition(local_projection_time_);
    feasible_window_.measured_world = planner_manager_->global_data_.getPosition(local_measured_projection_time_);
    feasible_window_.growth_world = growth_world;
    feasible_window_.world_geometry_valid = feasible_window_.endpoint_world.allFinite() &&
        feasible_window_.projection_world.allFinite() && feasible_window_.measured_world.allFinite() && growth_world.allFinite();''',1)
s=s.replace('!(hint.goal.array() == end_pt_.array()).all()','!(hint.goal.array() == warmGoalContext().array()).all()',1)
p.write_text(s)

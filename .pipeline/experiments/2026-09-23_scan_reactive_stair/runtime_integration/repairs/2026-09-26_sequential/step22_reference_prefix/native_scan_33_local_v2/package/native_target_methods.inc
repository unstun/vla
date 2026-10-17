  bool SCANReplanFSM::adjustGlobalTargetIfOccupied()
  {
    auto map = planner_manager_->grid_map_;
    auto &global_data = planner_manager_->global_data_;
    const double duration = global_data.global_duration_;
    const bool reference = navi_mode_ == NAVI_MODE::REFERENCE_PATH;
    reference_frontier_time_ = -1.0;
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

  bool SCANReplanFSM::getLocalTarget()
  {
    const double max_vel = planner_manager_->pp_.max_vel_;
    const double max_acc = planner_manager_->pp_.max_acc_;
    const bool reference = navi_mode_ == NAVI_MODE::REFERENCE_PATH;
    local_target_time_ = local_projection_time_ = -1.0;
    if (reference) {
      local_target_pt_.setZero();
      local_target_vel_.setZero();
      if (!start_pt_.allFinite() || !start_vel_.allFinite() || !start_acc_.allFinite() ||
          !odom_pos_.allFinite() || !end_pt_.allFinite() ||
          !std::isfinite(max_vel) || max_vel <= 0.0 || !std::isfinite(max_acc) ||
          !std::isfinite(planning_horizon_) || planning_horizon_ <= 0.0 ||
          !adjustGlobalTargetIfOccupied()) return false;
    }
    const double duration = reference ? reference_frontier_time_ : planner_manager_->global_data_.global_duration_;
    const Eigen::Vector3d selection_end = reference ? planner_manager_->global_data_.getPosition(duration) : end_pt_;
    double t_step = max_vel > 1e-6 ? planning_horizon_ / 20.0 / max_vel : 0.01;
    t_step = std::max(t_step, 0.01);
    if (reference && !std::isfinite(t_step)) return false;

    double t_proj = 0.0;
    double min_dist_to_start = 9999.0;
    for (double t = 0.0; t < duration; t += t_step)
    {
      Eigen::Vector3d pos_t = planner_manager_->global_data_.getPosition(t);
      if (reference && !pos_t.allFinite()) return false;
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

    auto targetOccupancy = [&](const Eigen::Vector3d &pt) {
      if (reference && !pt.allFinite()) return 1;
      const double yaw = estimateYawFromSegment(odom_pos_, pt);
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
    if ((selection_end - local_target_pt_).norm() < braking_distance)
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
                      (local_target_pt_ - start_pt_).norm() < 0.2)) return false;
    local_target_time_ = target_t;
    local_projection_time_ = t_proj;
    return true;
  }

  bool SCANReplanFSM::callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj, int *reference_prefix_budget)
  {

    if (!getLocalTarget()) return false;

    bool plan_success =
        planner_manager_->reboundReplan(start_pt_, start_vel_, start_acc_, local_target_pt_, local_target_vel_, (have_new_target_ || flag_use_poly_init), flag_randomPolyTraj);
    have_new_target_ = false;

    const bool reference = navi_mode_ == NAVI_MODE::REFERENCE_PATH;
    int per_round_budget = 3;
    int &remaining = reference_prefix_budget ? *reference_prefix_budget : per_round_budget;
    double candidate_t = local_target_time_;
    while (!plan_success && reference && remaining > 0) {
      --remaining;  // Count considered proposals, including rejected endpoints.
      candidate_t = local_projection_time_ + 0.5 * (candidate_t - local_projection_time_);
      if (!std::isfinite(candidate_t) || candidate_t <= local_projection_time_ ||
          candidate_t > reference_frontier_time_) continue;
      const Eigen::Vector3d candidate = planner_manager_->global_data_.getPosition(candidate_t);
      if (!candidate.allFinite() || (candidate - start_pt_).norm() < 0.2) continue;
      const double yaw = estimateYawFromSegment(odom_pos_, candidate);
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
      // This marks the accepted planning window end, not measured execution.
      planner_manager_->global_data_.last_progress_time_ = local_target_time_;
      RCLCPP_INFO(node_->get_logger(), "reference_window_committed time=%.12f full_duration=%.12f",
                  local_target_time_, planner_manager_->global_data_.global_duration_);
    }

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

      bspline_pub_->publish(bspline);

      visualization_->displayOptimalTraj(info->position_traj_, 0);
    }

    return plan_success;
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
      bool success = callReboundReplan(false, false, &reference_prefix_budget);
      if (!success)
      {
        success = callReboundReplan(true, false, &reference_prefix_budget);
        if (!success)
        {
          success = callReboundReplan(true, true, &reference_prefix_budget);
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

void SCANReplanFSM::expireLocal() {

        const auto &global_data = planner_manager_->global_data_;
        const bool reference_path_has_next_window =
            navi_mode_ == NAVI_MODE::REFERENCE_PATH &&
            global_data.last_progress_time_ < global_data.global_duration_ - 1e-3;

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

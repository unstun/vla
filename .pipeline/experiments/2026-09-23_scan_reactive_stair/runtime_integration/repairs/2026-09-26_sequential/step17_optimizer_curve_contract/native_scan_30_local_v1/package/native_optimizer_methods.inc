  bool BsplineOptimizer::rebound_optimize()
  {
    iter_num_ = 0;
    int start_id = order_;
    int end_id = this->cps_.size - order_;
    variable_num_ = 3 * (end_id - start_id);
    double final_cost;

    auto t0 = std::chrono::steady_clock::now();
    auto t1 = t0;
    auto t2 = t0;
    const auto valid_constraint_count = [&]() {
      size_t count = 0;
      for (int i = 0; i < cps_.size; ++i) {
        if (!reactive_stair::validReboundSlot(cps_, i) || cps_.base_point[i].size() != cps_.direction[i].size()) continue;
        for (size_t j = 0; j < cps_.base_point[i].size(); ++j)
          if (cps_.base_point[i][j].allFinite() && cps_.direction[i][j].allFinite() &&
              std::abs(cps_.direction[i][j].norm() - 1.0) <= 1e-6) ++count;
      }
      return count;
    };
    int restart_nums = 0, rebound_times = 0;
    ;
    bool flag_force_return, flag_occ, success;
    new_lambda2_ = lambda2_;
    constexpr int MAX_RESART_NUMS_SET = 3;
    do
    {
      /* ---------- prepare ---------- */
      min_cost_ = std::numeric_limits<double>::max();
      iter_num_ = 0;
      flag_force_return = false;
      flag_occ = false;
      success = false;

      double q[variable_num_];
      memcpy(q, cps_.points.data() + 3 * start_id, variable_num_ * sizeof(q[0]));

      lbfgs::lbfgs_parameter_t lbfgs_params;
      lbfgs::lbfgs_load_default_parameters(&lbfgs_params);
      lbfgs_params.mem_size = 16;
      lbfgs_params.max_iterations = 200;
      lbfgs_params.g_epsilon = 0.01;

      /* ---------- optimize ---------- */
      t1 = std::chrono::steady_clock::now();
      int result = lbfgs::lbfgs_optimize(variable_num_, q, &final_cost, BsplineOptimizer::costFunctionRebound, NULL, BsplineOptimizer::earlyExit, this, &lbfgs_params);
      t2 = std::chrono::steady_clock::now();
      double time_ms = std::chrono::duration<double, std::milli>(t2 - t1).count();
      double total_time_ms = std::chrono::duration<double, std::milli>(t2 - t0).count();

      /* ---------- success temporary, check collision again ---------- */
      if (result == lbfgs::LBFGS_CONVERGENCE ||
          result == lbfgs::LBFGSERR_MAXIMUMITERATION ||
          result == lbfgs::LBFGS_ALREADY_MINIMIZED ||
          result == lbfgs::LBFGS_STOP)
      {
        //ROS_WARN("Solver error in planning!, return = %s", lbfgs::lbfgs_strerror(result));
        flag_force_return = false;

        UniformBspline traj = UniformBspline(cps_.points, 3, bspline_interval_);
        const auto collision = reactive_stair::checkFullCubicTrajectory(
            traj, 0.0, grid_map_->getResolution(), GridMap::collision_heading_lookahead_s,
            [this](const Eigen::Vector3d& p, const Eigen::Vector3d& ahead, const Eigen::Vector3d& v) {
              return grid_map_->collisionTrajectoryYaw(p, ahead, v);
            }, [this](const Eigen::Vector3d& p, double yaw) { return grid_map_->getInflateOccupancy(p, yaw) != 0; });
        RCLCPP_INFO(rclcpp::get_logger("bspline_opt"),
                    "optimizer_full_curve stage=rebound status=%d first_t=%.12f duration=%.12f samples=%zu control_sqnorm=%.17g",
                    static_cast<int>(collision.status), collision.first_time_s, collision.duration_s,
                    collision.samples, cps_.points.squaredNorm());
        if (!collision.clear() && collision.status != reactive_stair::TrajectoryCheckStatus::Collision)
          return false; // Invalid geometry/time or exhausted sample budget is not a repairable collision.
        flag_occ = !collision.clear();
        if (flag_occ) {
          const double t = collision.first_time_s;
          const Eigen::Vector3d pos = traj.evaluateDeBoorT(t);
          const Eigen::Vector3d ahead = traj.evaluateDeBoorT(std::min(t + GridMap::collision_heading_lookahead_s, collision.duration_s));
          const double spline_yaw = grid_map_->collisionTrajectoryYaw(pos, ahead, traj.getDerivative().evaluateDeBoorT(t));
            static bool diagnosed_initial_collision = false;
            if (t <= bspline_interval_ && !diagnosed_initial_collision) {
              grid_map_->logInitialSplineCollision(pos, spline_yaw);
              diagnosed_initial_collision = true;
            }
            if (t <= bspline_interval_) // First 3 control points in obstacles!
            {
              cout << cps_.points.col(1).transpose() << "\n"
                   << cps_.points.col(2).transpose() << "\n"
                   << cps_.points.col(3).transpose() << "\n"
                   << cps_.points.col(4).transpose() << endl;
              RCLCPP_WARN(rclcpp::get_logger("bspline_opt"),
                          "First three control points are in obstacles; t=%f", t);
              return false;
            }

        }

        if (!flag_occ)
        {
          printf("\033[32miter(+1)=%d,time(ms)=%5.3f,total_t(ms)=%5.3f,cost=%5.3f\n\033[0m", iter_num_, time_ms, total_time_ms, final_cost);
          success = true;
        }
        else // restart
        {
          restart_nums++;
          const size_t constraints_before = valid_constraint_count();
          initControlPoints(cps_.points, false);
          RCLCPP_INFO(rclcpp::get_logger("bspline_opt"),
                      "optimizer_collision_retry attempt=%d valid_constraints_before=%zu valid_constraints_after=%zu",
                      restart_nums, constraints_before, valid_constraint_count());
          new_lambda2_ *= 2;

          printf("\033[32miter(+1)=%d,time(ms)=%5.3f,keep optimizing\n\033[0m", iter_num_, time_ms);
        }
      }
      else if (result == lbfgs::LBFGSERR_CANCELED)
      {
        flag_force_return = true;
        rebound_times++;
        cout << "iter=" << iter_num_ << ",time(ms)=" << time_ms << ",rebound." << endl;
      }
      else
      {
        RCLCPP_WARN(rclcpp::get_logger("bspline_opt"),
                    "Solver error. Return=%d, %s; skip this plan", result, lbfgs::lbfgs_strerror(result));
        // while (ros::ok());
      }

    } while ((flag_occ && restart_nums < MAX_RESART_NUMS_SET) ||
             (flag_force_return && force_stop_type_ == STOP_FOR_REBOUND && rebound_times <= 20));

    return success;
  }

  bool BsplineOptimizer::refine_optimize()
  {
    iter_num_ = 0;
    int start_id = order_;
    int end_id = this->cps_.points.cols() - order_;
    variable_num_ = 3 * (end_id - start_id);

    double q[variable_num_];
    double final_cost;

    memcpy(q, cps_.points.data() + 3 * start_id, variable_num_ * sizeof(q[0]));

    double origin_lambda4 = lambda4_;
    bool flag_safe = true;
    int iter_count = 0;
    do
    {
      lbfgs::lbfgs_parameter_t lbfgs_params;
      lbfgs::lbfgs_load_default_parameters(&lbfgs_params);
      lbfgs_params.mem_size = 16;
      lbfgs_params.max_iterations = 200;
      lbfgs_params.g_epsilon = 0.001;

      int result = lbfgs::lbfgs_optimize(variable_num_, q, &final_cost, BsplineOptimizer::costFunctionRefine, NULL, NULL, this, &lbfgs_params);
      if (result == lbfgs::LBFGS_CONVERGENCE ||
          result == lbfgs::LBFGSERR_MAXIMUMITERATION ||
          result == lbfgs::LBFGS_ALREADY_MINIMIZED ||
          result == lbfgs::LBFGS_STOP)
      {
        //pass
      }
      else
      {
        RCLCPP_ERROR(rclcpp::get_logger("bspline_opt"),
                     "Solver error while refining: return=%d, %s", result, lbfgs::lbfgs_strerror(result));
      }

      UniformBspline traj = UniformBspline(cps_.points, 3, bspline_interval_);
      const auto collision = reactive_stair::checkFullCubicTrajectory(
          traj, 0.0, grid_map_->getResolution(), GridMap::collision_heading_lookahead_s,
          [this](const Eigen::Vector3d& p, const Eigen::Vector3d& ahead, const Eigen::Vector3d& v) {
            return grid_map_->collisionTrajectoryYaw(p, ahead, v);
          }, [this](const Eigen::Vector3d& p, double yaw) { return grid_map_->getInflateOccupancy(p, yaw) != 0; });
      flag_safe = collision.clear();
      RCLCPP_INFO(rclcpp::get_logger("bspline_opt"),
                  "optimizer_full_curve stage=refine status=%d first_t=%.12f duration=%.12f samples=%zu control_sqnorm=%.17g",
                  static_cast<int>(collision.status), collision.first_time_s, collision.duration_s,
                  collision.samples, cps_.points.squaredNorm());

      if (!flag_safe)
        lambda4_ *= 2;

      iter_count++;
    } while (!flag_safe && iter_count <= 0);

    lambda4_ = origin_lambda4;

    //cout << "iter_num_=" << iter_num_ << endl;

    return flag_safe;
  }


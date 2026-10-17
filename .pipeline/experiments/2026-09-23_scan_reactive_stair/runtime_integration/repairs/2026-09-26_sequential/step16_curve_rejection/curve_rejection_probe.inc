      static bool rejection_probe_emitted = false;
      if (!rejection_probe_emitted) {
        rejection_probe_emitted = true;
        // Original full-curve check has already rejected publication. All
        // following paired queries and dumps are diagnostic only.
        const auto observe = [&](const char* label, UniformBspline curve) {
          const auto started = std::chrono::steady_clock::now();
          const auto check = reactive_stair::checkFullCubicTrajectory(
              curve, 0.0, grid_map_->getResolution(), GridMap::collision_heading_lookahead_s,
              [this](const Eigen::Vector3d& p, const Eigen::Vector3d& next, const Eigen::Vector3d& v) {
                return grid_map_->collisionTrajectoryYaw(p, next, v);
              }, [this](const Eigen::Vector3d& p, double yaw) { return grid_map_->getInflateOccupancy(p, yaw) != 0; });
          const double check_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - started).count();
          RCLCPP_WARN(node_->get_logger(), "REJECT_PROBE curve=%s status=%d first_t=%.12f duration=%.12f samples=%zu check_wall_ms=%.6f",
                      label, static_cast<int>(check.status), check.first_time_s, check.duration_s, check.samples, check_ms);
          if (check.status != reactive_stair::TrajectoryCheckStatus::Clear &&
              check.status != reactive_stair::TrajectoryCheckStatus::Collision) return;
          auto velocity = curve.getDerivative();
          auto acceleration = velocity.getDerivative();
          curve.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);
          double time_ratio = 0.0;
          const bool feasible = curve.checkFeasibility(time_ratio, false);
          const auto p0 = curve.evaluateDeBoorT(0.0), v0 = velocity.evaluateDeBoorT(0.0), a0 = acceleration.evaluateDeBoorT(0.0);
          RCLCPP_WARN(node_->get_logger(), "REJECT_PROBE dynamics=%s feasible=%d native_ratio=%.12f velocity_component_bound=%.12f acceleration_component_bound=%.12f start_position_error=%.12f start_velocity_error=%.12f start_acceleration_error=%.12f",
                      label, feasible, time_ratio, velocity.getControlPoint().cwiseAbs().maxCoeff(),
                      acceleration.getControlPoint().cwiseAbs().maxCoeff(),
                      (p0 - start_pt).norm(), (v0 - start_vel).norm(), (a0 - start_acc).norm());
          if (check.status != reactive_stair::TrajectoryCheckStatus::Collision) return;
          const auto p = curve.evaluateDeBoorT(check.first_time_s);
          const auto ahead = curve.evaluateDeBoorT(std::min(check.first_time_s + GridMap::collision_heading_lookahead_s, check.duration_s));
          const double curve_yaw = grid_map_->collisionTrajectoryYaw(p, ahead, velocity.evaluateDeBoorT(check.first_time_s));
          size_t parent = seed_path.size();
          double nearest_distance = std::numeric_limits<double>::infinity();
          Eigen::Vector3d nearest = Eigen::Vector3d::Zero();
          for (size_t i = 1; i < seed_path.size(); ++i) {
            const auto delta = seed_path[i] - seed_path[i - 1];
            if (delta.squaredNorm() <= 0.0) continue;
            const double u = std::min(1.0, std::max(0.0, (p - seed_path[i - 1]).dot(delta) / delta.squaredNorm()));
            const Eigen::Vector3d candidate = seed_path[i - 1] + u * delta;
            if ((candidate - p).norm() < nearest_distance) {
              nearest_distance = (candidate - p).norm(); nearest = candidate; parent = i;
            }
          }
          if (parent == seed_path.size()) return;
          const double parent_yaw = grid_map_->collisionSegmentYaw(seed_path[parent - 1], seed_path[parent]);
          const int same_position_parent_yaw = grid_map_->getInflateOccupancy(p, parent_yaw);
          const int projected_position_curve_yaw = grid_map_->getInflateOccupancy(nearest, curve_yaw);
          const int projected_position_parent_yaw = grid_map_->getInflateOccupancy(nearest, parent_yaw);
          RCLCPP_WARN(node_->get_logger(), "REJECT_PROBE paired=%s parent_edge=%zu distance=%.12f p=(%.12f,%.12f,%.12f) projected=(%.12f,%.12f,%.12f) curve_yaw=%.12f parent_yaw=%.12f same_position_parent_occupied=%d projected_curve_occupied=%d projected_parent_occupied=%d",
                      label, parent, nearest_distance, p.x(), p.y(), p.z(), nearest.x(), nearest.y(), nearest.z(),
                      curve_yaw, parent_yaw, same_position_parent_yaw, projected_position_curve_yaw, projected_position_parent_yaw);
          RCLCPP_WARN(node_->get_logger(), "REJECT_PROBE footprint=%s variant=curve_position_curve_heading", label);
          grid_map_->logInitialSplineCollision(p, curve_yaw);
          RCLCPP_WARN(node_->get_logger(), "REJECT_PROBE footprint=%s variant=curve_position_parent_heading", label);
          grid_map_->logInitialSplineCollision(p, parent_yaw);
        };
        const auto dump = [&](const char* label, UniformBspline curve) {
          const auto points = curve.getControlPoint();
          for (int i = 0; i < points.cols(); ++i)
            std::printf("REJECT_CONTROL,%s,%d,%.17g,%.17g,%.17g\n", label, i, points(0,i), points(1,i), points(2,i));
          const auto knots = curve.getKnot();
          for (int i = 0; i < knots.size(); ++i)
            std::printf("REJECT_KNOT,%s,%d,%.17g\n", label, i, knots[i]);
        };
        for (size_t i = 0; i < seed_path.size(); ++i)
          std::printf("REJECT_SEED,%zu,%.17g,%.17g,%.17g\n", i, seed_path[i].x(), seed_path[i].y(), seed_path[i].z());
        for (size_t i = 0; i < point_set.size(); ++i)
          std::printf("REJECT_SAMPLE,%zu,%.17g,%.17g,%.17g\n", i, point_set[i].x(), point_set[i].y(), point_set[i].z());
        UniformBspline initial(rejection_initial_controls, 3, rejection_initial_interval);
        observe("timed_initial", initial);
        observe("final", pos);
        dump("timed_initial", initial);
        dump("final", pos);
      }

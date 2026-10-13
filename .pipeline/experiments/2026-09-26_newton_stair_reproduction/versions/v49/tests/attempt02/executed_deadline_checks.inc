// Run against the same measured map and the fully accepted native curve.
if (std::getenv("V49_DEADLINE_CONTRACT")) {
  using scan_planner::PlanningDeadline;
  using scan_planner::PlanningTimeout;
  using Clock = PlanningDeadline::Clock;
  int checks = 0;
  auto require = [&](bool ok, const char *name) {
    if (!ok) throw std::runtime_error(std::string("V49_DEADLINE_FAIL ") + name);
    std::cout << "V49_DEADLINE_CHECK " << name << " PASS" << std::endl; ++checks;
  };
  auto expired = [&](auto operation) {
    try { operation(); } catch (const PlanningTimeout &) { return true; }
    return false;
  };
  PlanningDeadline old(Clock::now()-std::chrono::milliseconds(26));
  require(expired([&]{old.check("test");}),"compute_deadline");
  require(expired([&]{old.recovery();}),"exhausted_reserve");
  PlanningDeadline reserve(Clock::now()-std::chrono::milliseconds(21));
  require(expired([&]{reserve.compute();}),"retry_cannot_reset_deadline");
  reserve.recovery(); require(!expired([&]{reserve.check("reserve");}),"remaining_reserve_available");
  require(expired([&]{reserve.compute();}),"recovery_cannot_extend_compute");
  PlanningDeadline final_budget;
  final_budget.finalSafety();
  require(!expired([&]{final_budget.check("final");}),"final_safety_has_reserve");
  require(expired([&]{old.finalSafety();}),"expired_final_check_rejects");
  auto &manager = *fsm.planner_manager_;
  auto source = manager.local_data_;
  auto global = manager.global_data_;
  const auto owner = fsm.published_curve_owner_;
  const auto identity = fsm.active_p2b_identity_;
  const auto goal = fsm.end_pt_;
  const auto window = fsm.feasible_window_;
  const auto state = fsm.exec_state_;
  const bool hover = fsm.need_hover_stop_, escape = fsm.flag_escape_emergency_;
  auto restore = [&] {
    manager.local_data_ = source; manager.global_data_ = global;
    fsm.published_curve_owner_ = owner; fsm.active_p2b_identity_ = identity;
    fsm.end_pt_ = goal; fsm.feasible_window_ = window; fsm.have_target_ = true;
    fsm.exec_state_ = state; fsm.need_hover_stop_=hover; fsm.flag_escape_emergency_=escape;
  };
  require(source.traj_id_ == owner.traj_id && !owner.identity.empty(),"fixture_has_published_owner");
  const auto p = source.position_traj_.evaluateDeBoorT(0.0);
  const auto q = source.position_traj_.evaluateDeBoorT(source.duration_);
  {
    GridMap::PlanningDeadlineScope scope(*map,&old);
    require(expired([&]{map->getInflateOccupancy(p,0.0);}),"occupancy_cancels");
    require(expired([&]{map->refreshSensorInputs("test");}),"refresh_does_not_consume_after_timeout");
    require(expired([&]{manager.bspline_optimizer_rebound_->a_star_->AstarSearch(map->getResolution(),p,q,true);}),"native_search_cancels");
    auto *opt = manager.bspline_optimizer_rebound_.get();
    double x[1]={0},g[1]={0};
    require(expired([&]{opt->costFunctionRebound(opt,x,g,1);}),"rebound_objective_cancels");
    require(expired([&]{opt->costFunctionRefine(opt,x,g,1);}),"refine_objective_cancels");
    require(expired([&]{opt->earlyExit(opt,x,g,0,0,0,0,1,1,1);}),"line_search_cancels");
    require(expired([&]{manager.reboundReplan(p,Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero(),q,Eigen::Vector3d::Zero(),true,false);}),"manager_cancels_before_fallback");
  }
  require(map->planning_deadline_==nullptr,"deadline_scope_unwinds");
  restore(); require(fsm.validateTimeoutContinuation(),"fresh_full_remaining_curve_passes");
  restore(); fsm.active_p2b_identity_.command_id += "changed";
  require(!fsm.validateTimeoutContinuation(),"wrong_command_rejected");
  restore(); fsm.active_p2b_identity_.map_revision++;
  require(!fsm.validateTimeoutContinuation(),"wrong_map_revision_rejected");
  restore(); fsm.published_curve_owner_.map=nullptr;
  require(!fsm.validateTimeoutContinuation(),"wrong_map_instance_rejected");
  restore(); fsm.end_pt_.z()+=0.1;
  require(!fsm.validateTimeoutContinuation(),"changed_goal_rejected");
  restore(); manager.local_data_.traj_id_++;
  require(!fsm.validateTimeoutContinuation(),"wrong_trajectory_rejected");
  restore(); manager.local_data_.start_time_=node->now()-rclcpp::Duration::from_seconds(source.duration_+.1);
  fsm.published_curve_owner_.start_ns=manager.local_data_.start_time_.nanoseconds();
  require(!fsm.validateTimeoutContinuation(),"expired_curve_rejected");
  restore(); manager.local_data_.start_time_=node->now()+rclcpp::Duration::from_seconds(.1);
  fsm.published_curve_owner_.start_ns=manager.local_data_.start_time_.nanoseconds();
  require(!fsm.validateTimeoutContinuation(),"regressed_clock_rejected");
  restore(); const double cloud_stamp=map->reactive_cloud_stamp_s_;map->reactive_cloud_stamp_s_=0;
  require(!fsm.validateTimeoutContinuation(),"stale_scan_rejected");map->reactive_cloud_stamp_s_=cloud_stamp;
  restore(); const auto surface_id=map->reactive_ground_.source_id;map->reactive_ground_.source_id="invalid";
  require(!fsm.validateTimeoutContinuation(),"changed_stair_support_rejected");map->reactive_ground_.source_id=surface_id;
  restore(); const auto bounds=map->mp_.map_max_boundary_;map->mp_.map_max_boundary_=p-Eigen::Vector3d::Ones();
  require(!fsm.validateTimeoutContinuation(),"new_blocked_curve_rejected");map->mp_.map_max_boundary_=bounds;
  restore();
  size_t splines=0,stops=0,rejections=0; bool wrong_owner=false;
  auto sub=node->create_subscription<scan_planner_msgs::msg::Bspline>("planning/bspline",10,
      [&](scan_planner_msgs::msg::Bspline::SharedPtr msg) { ++splines; stops+=msg->emergency_stop;
        wrong_owner |= msg->command_id!=identity.command_id || msg->generation!=identity.generation; });
  auto admission=node->create_subscription<scan_planner_msgs::msg::P2BAdmission>("/p2b/scan_admission",10,
      [&](scan_planner_msgs::msg::P2BAdmission::SharedPtr msg) {
        if(msg->status=="rejected" && msg->message=="native_solve_timeout") ++rejections; });
  spin(80); splines=stops=rejections=0;
  {
    GridMap::RawContributorCacheScope cache(*map);
    require(fsm.validateTimeoutContinuation(),"current_callback_populates_raw_cache");
    const bool ok=fsm.runBudgetedReplan(false,false,Clock::now()-std::chrono::microseconds(20050));
    require(!ok && fsm.last_solve_continued_ && !fsm.last_solve_stopped_,"timeout_continues_only_fresh_safe_curve");
  }
  spin(30);
  require(splines==0,"continuation_does_not_republish_or_restamp");
  require(manager.local_data_.traj_id_==source.traj_id_ && manager.local_data_.start_time_==source.start_time_ &&
      (manager.local_data_.position_traj_.getControlPoint().array()==source.position_traj_.getControlPoint().array()).all(),"timeout_keeps_exact_old_curve");
  require(manager.global_data_.last_progress_time_==global.last_progress_time_,"timeout_keeps_progress");
  restore();
  require(!fsm.runBudgetedReplan(false,false,Clock::now()-std::chrono::milliseconds(26)) &&
      fsm.last_solve_stopped_ && !fsm.last_solve_continued_,"exhausted_reserve_immediately_stops");
  spin(30);
  require(splines==1 && stops==1 && !wrong_owner,"only_original_same_owner_stop_published");
  require(rejections==1,"timeout_closes_command_gate");
  require(fsm.exec_state_==scan_planner::SCANReplanFSM::EMERGENCY_STOP && fsm.need_hover_stop_ &&
      !fsm.flag_escape_emergency_,"stop_state_cannot_be_overwritten_by_retry");
  restore();
  // Exercise the actual recorded cold chain with the production budget.
  auto begun=Clock::now(); bool accepted=fsm.runBudgetedReplan(false,false);
  std::cout << "V49_RECORDED_BUDGET accepted="<<accepted<<" continued="<<fsm.last_solve_continued_
      <<" stopped="<<fsm.last_solve_stopped_<<" wall_ms="
      <<std::chrono::duration<double,std::milli>(Clock::now()-begun).count()<<std::endl;
  require(accepted || fsm.last_solve_continued_ || fsm.last_solve_stopped_,"recorded_chain_has_complete_outcome");
  restore();
  std::cout << "V49_DEADLINE_PASSED checks=" << checks << std::endl;
}

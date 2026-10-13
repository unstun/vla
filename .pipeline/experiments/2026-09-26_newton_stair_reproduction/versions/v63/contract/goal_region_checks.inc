if (std::getenv("V50_REGION_CONTRACT")) {
  int checks=0;
  auto require=[&](bool ok,const char *name) {
    if(!ok)throw std::runtime_error(std::string("V50_REGION_FAIL ")+name);
    std::cout<<"V50_REGION_CHECK "<<name<<" PASS"<<std::endl;++checks;
  };
  auto &manager=*fsm.planner_manager_;
  auto search=manager.bspline_optimizer_rebound_->a_star_;
  auto accepted=manager.local_data_;
  const auto original_global=manager.global_data_;
  const auto original_hint=fsm.feasible_window_;
  const auto original_goal=fsm.end_pt_;
  const auto original_bounds=map->mp_.map_max_boundary_;
  const auto start=accepted.position_traj_.evaluateDeBoorT(0.0);
  const auto target=accepted.position_traj_.evaluateDeBoorT(accepted.duration_);
  auto equal_path=[](const auto &a,const auto &b) {
    if(a.size()!=b.size())return false;
    for(size_t i=0;i<a.size();++i)if((a[i].array()!=b[i].array()).any())return false;
    return true;
  };
  search->goal_region_precheck_enabled=false;
  auto parent=manager.findGoalNeighborhoodPath(start,target,1.0);
  search->goal_region_precheck_enabled=true;
  auto candidate=manager.findGoalNeighborhoodPath(start,target,1.0);
  require(!parent.empty()&&equal_path(parent,candidate),"reachable_goal_keeps_exact_native_path");
  const Eigen::Vector3d high_goal=start+Eigen::Vector3d(1.0,0,3.0);
  map->mp_.map_max_boundary_.z()=high_goal.z()-1.0; // body upper clearance proves the entire ball impossible.
  for(int repetition=0;repetition<3;++repetition)for(bool optimized:{false,true}) {
    search->goal_region_precheck_enabled=optimized;
    GridMap::RawContributorCacheScope cache(*map);
    const auto before=map->planning_profile_.values;
    const auto began=std::chrono::steady_clock::now();
    const auto result=manager.findGoalNeighborhoodPath(start,high_goal,1.0);
    const double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-began).count();
    require(result.empty(),"geometrically_impossible_goal_returns_original_empty_path");
    std::cout<<"V50_REGION_PAIR optimized="<<optimized<<" repetition="<<repetition<<" wall_ms="<<ms
             <<" profile="<<map->planning_profile_.since(before)<<std::endl;
  }
  require(search->goal_region_rejections>=3,"negative_certificate_executed");
  require(search->getPath().empty(),"no_stale_path_after_certificate");
  map->mp_.map_max_boundary_=original_bounds;
  auto reopened=manager.findGoalNeighborhoodPath(start,target,1.0);
  require(equal_path(parent,reopened),"map_restoration_rechecks_geometry_without_cached_rejection");
  require((fsm.end_pt_.array()==original_goal.array()).all(),"final_goal_unchanged");
  require(manager.local_data_.traj_id_==accepted.traj_id_ && manager.local_data_.start_time_==accepted.start_time_,"executing_curve_not_changed_or_restamped");
  manager.local_data_=accepted;manager.global_data_=original_global;fsm.feasible_window_=original_hint;
  std::cout<<"V50_REGION_CONTRACT_PASSED checks="<<checks<<std::endl;
}

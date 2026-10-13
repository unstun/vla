from pathlib import Path
N=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/scan75_reference_continuity_v53/src/plan_manage')
p=N/'include/plan_manage/planner_manager.h';s=p.read_text().replace('    void invalidateWarmStart();','''    void invalidateWarmStart();
    // Reference refresh transactions preserve eligibility, never a safety verdict.
    struct WarmStartBinding {
      std::string context;
      Eigen::Vector3d goal;
      int trajectory_id;
      const GridMap *map;
    };
    WarmStartBinding warmStartBinding() const;
    void restoreWarmStartBinding(const WarmStartBinding &binding);''')
s=s.replace('const std::vector<Eigen::Vector3d> &waypoints, const Eigen::Vector3d &end_vel, const Eigen::Vector3d &end_acc);','const std::vector<Eigen::Vector3d> &waypoints, const Eigen::Vector3d &end_vel, const Eigen::Vector3d &end_acc, bool preserve_binding = false);',1);p.write_text(s)
p=N/'src/planner_manager.cpp';s=p.read_text().replace('  void SCANPlannerManager::invalidateWarmStart()','''  SCANPlannerManager::WarmStartBinding SCANPlannerManager::warmStartBinding() const
  {
    return {accepted_warm_context_, accepted_warm_goal_, accepted_warm_traj_id_, accepted_warm_map_};
  }

  void SCANPlannerManager::restoreWarmStartBinding(const WarmStartBinding &binding)
  {
    accepted_warm_context_ = binding.context;
    accepted_warm_goal_ = binding.goal;
    accepted_warm_traj_id_ = binding.trajectory_id;
    accepted_warm_map_ = binding.map;
  }

  void SCANPlannerManager::invalidateWarmStart()''',1)
a=s.index('  bool SCANPlannerManager::planGlobalTrajWaypoints');b=s.index('  bool SCANPlannerManager::planGlobalTraj(',a)
chunk=s[a:b].replace('const Eigen::Vector3d &end_acc)','const Eigen::Vector3d &end_acc, bool preserve_binding)',1).replace('    invalidateWarmStart();','    if (!preserve_binding) invalidateWarmStart();',1);s=s[:a]+chunk+s[b:];p.write_text(s)
p=N/'src/scan_replan_fsm.cpp';s=p.read_text();a=s.index('bool SCANReplanFSM::planGlobalTrajByWaypoints');b=s.index('bool SCANReplanFSM::planNextWaypoint',a)
chunk=s[a:b].replace('        Eigen::Vector3d::Zero());','        Eigen::Vector3d::Zero(), preserve_binding);',1);s=s[:a]+chunk+s[b:]
a=s.index('    const auto previous_context =');b=s.index('    const bool goal_valid =',a)
s=s[:a]+'    const auto previous_binding = planner_manager_->warmStartBinding();\n'+s[b:]
a=s.index('      planner_manager_->accepted_warm_context_ = previous_context;');b=s.index('\n    }',a)
s=s[:a]+'      planner_manager_->restoreWarmStartBinding(previous_binding);'+s[b:]
s=s.replace('    const auto &curve = manager.local_data_;','    auto &curve = planner_manager_->local_data_;\n    const auto binding = manager.warmStartBinding();',1)
s=s.replace('manager.accepted_warm_traj_id_','binding.trajectory_id').replace('manager.accepted_warm_context_','binding.context').replace('manager.accepted_warm_goal_','binding.goal').replace('manager.accepted_warm_map_','binding.map')
p.write_text(s)
# Harness: reconstruct the accepted owner's qualified context and world anchors, parent SFINAE fallback.
p=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v53/corner/corner_replay.cpp');s=p.read_text();a=s.index('\nstd::string xyz')
s=s[:a]+'''
template<class T> auto context(T &fsm, int) -> decltype(fsm.warmStartIdentity()) {return fsm.warmStartIdentity();}
template<class T> std::string context(T &fsm, long) {return owner(fsm.active_p2b_identity_);}
template<class T> auto goalContext(T &fsm, int) -> decltype(fsm.warmGoalContext()) {return fsm.warmGoalContext();}
template<class T> Eigen::Vector3d goalContext(T &fsm, long) {return fsm.end_pt_;}
template<class T> auto worldWindow(T &fsm, int) -> decltype(fsm.feasible_window_.world_geometry_valid, void()) {
 auto &w=fsm.feasible_window_;auto &g=fsm.planner_manager_->global_data_;
 w.world_geometry_valid=true;w.endpoint_world=g.getPosition(w.projection+w.span);
 w.projection_world=g.getPosition(w.projection);w.measured_world=g.getPosition(w.measured_projection);w.growth_world=g.getPosition(w.growth_projection);
}
template<class T> void worldWindow(T &, long) {}
''' +s[a:]
s=s.replace('manager.accepted_warm_context_=owner(m);manager.accepted_warm_goal_=fsm.end_pt_;','manager.accepted_warm_context_=context(fsm,0);manager.accepted_warm_goal_=goalContext(fsm,0);')
s=s.replace('w.goal=fsm.end_pt_;','w.goal=goalContext(fsm,0);').replace('w.stamp=42.338359833;}','w.stamp=42.338359833;worldWindow(fsm,0);}')
s=s.replace('manager.accepted_warm_context_=owner(fsm.active_p2b_identity_);manager.accepted_warm_goal_=goal;','manager.accepted_warm_context_=context(fsm,0);manager.accepted_warm_goal_=goalContext(fsm,0);').replace('manager.setWarmStartContext(owner(fsm.active_p2b_identity_),goal,t);','manager.setWarmStartContext(context(fsm,0),goalContext(fsm,0),t);')
p.write_text(s)

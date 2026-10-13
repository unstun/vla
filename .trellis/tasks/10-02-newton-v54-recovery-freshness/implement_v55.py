from pathlib import Path
import difflib,hashlib,json
B=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction');N=B/'runtime/scan77_recovery_freshness_v55';P=B/'runtime/scan76_warm_clock_guard_v54';V=B/'versions/v55'
p=N/'src/plan_manage/include/plan_manage/scan_replan_fsm.h';s=p.read_text().replace('    bool callEmergencyStop','    int recoveryTargetOccupancy(const Eigen::Vector3d &candidate, double yaw);\n    bool callEmergencyStop',1);p.write_text(s)
p=N/'src/plan_manage/src/scan_replan_fsm.cpp';s=p.read_text();a=s.index('  bool SCANReplanFSM::callReboundReplan(');s=s[:a]+'''  int SCANReplanFSM::recoveryTargetOccupancy(const Eigen::Vector3d &candidate, double yaw)
  {
    // Queued inputs can age out during search. Reuse the original ordered drain
    // at this decision boundary; the round's spline-derived start PVA is fixed.
    const int fsm_odometry = takePendingOdometry(
        odom_sub_, node_->get_logger(), [this](const auto &message) { odometryCallback(message); });
    planner_manager_->grid_map_->refreshSensorInputs("reference_prefix", fsm_odometry);
    if (!candidate.allFinite() || !std::isfinite(yaw)) return 1;
    return planner_manager_->grid_map_->getInflateOccupancy(candidate, yaw);
  }

'''+s[a:]
a=s.index('      const double yaw = estimateYawFromSegment(start_pt_, candidate);',s.index('bool SCANReplanFSM::callReboundReplan'));b=s.index('      local_target_pt_ = candidate;',a)
chunk=s[a:b];chunk=chunk.replace('      RCLCPP_WARN(', '      const int occupancy = recoveryTargetOccupancy(candidate, yaw);\n      RCLCPP_WARN(',1).replace('planner_manager_->grid_map_->getInflateOccupancy(candidate,yaw)','occupancy').replace('planner_manager_->grid_map_->getInflateOccupancy(candidate, yaw) != 0','occupancy != 0');s=s[:a]+chunk+s[b:];p.write_text(s)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();manifest={str(p.relative_to(N)):sha(p) for p in (N/'src').rglob('*') if p.is_file()};(N/'source_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');patch='';changed=[]
for name in manifest:
 if (N/name).read_bytes()!=(P/name).read_bytes():
  changed.append(name);patch+=''.join(difflib.unified_diff((P/name).read_text().splitlines(True),(N/name).read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(V/'changes.patch').write_text(patch);p=V/'preparation.json';r=json.loads(p.read_text());r.update(source_sha256=manifest,changed_native_files=changed);p.write_text(json.dumps(r,indent=2)+'\n')
p=V/'contract/CMakeLists.txt';s=p.read_text();s+='\nadd_executable(freshness_probe freshness_probe.cpp\n /workspace/src/plan_manage/src/scan_replan_fsm.cpp\n /workspace/src/plan_manage/src/planner_manager.cpp)\ntarget_include_directories(freshness_probe PRIVATE /workspace/src/plan_manage/include)\ntarget_compile_options(freshness_probe PRIVATE -fno-access-control)\nament_target_dependencies(freshness_probe ${dependencies})\ntarget_link_libraries(freshness_probe Eigen3::Eigen)\n';p.write_text(s)
p=V/'contract/inside.sh';s=p.read_text();a=s.index('/attempt/probe_build/native_probe');s=s[:a]+'/attempt/probe_build/freshness_probe --ros-args --params-file /version/building_planner.yaml --params-file /version/controller.yaml > /attempt/freshness_probe.log 2>&1\n'+s[a:];p.write_text(s)
p=V/'remote_test.py';s=p.read_text().replace('"startup_refresh_passed":','"freshness_passed":(out/"freshness_probe.log").exists() and "V55_FRESHNESS_PASSED" in (out/"freshness_probe.log").read_text(),\n        "startup_refresh_passed":').replace('and result["startup_refresh_passed"]','and result["freshness_passed"] and result["startup_refresh_passed"]');p.write_text(s)
print(json.dumps({'version':'v55','changed_native_files':changed}))

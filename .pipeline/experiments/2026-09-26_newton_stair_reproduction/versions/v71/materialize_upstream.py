"""Materialize pinned upstream planning with existing identity/stop transport."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
UPSTREAM = ROOT / 'references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_base'
CURRENT = BASE / 'runtime/scan82_optimizer_failure_v63'
OUTPUT = BASE / 'runtime/scan83_upstream_probe_v71'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return path.read_bytes().decode().replace('\r\n', '\n')


def replace_once(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new, 1)


def main():
    assert not (HERE/'manifest.json').exists(), 'Frozen source cannot be regenerated'
    if OUTPUT.exists():
        old = json.loads((OUTPUT/'source_sha256.json').read_text())
        assert all(sha(OUTPUT/name)==value for name,value in old.items())
        assert {str(p.relative_to(OUTPUT)) for p in OUTPUT.rglob('*') if p.is_file()} == set(old) | {'source_sha256.json'}
        shutil.rmtree(OUTPUT)  # Verified generated preparation source only.
    assert not OUTPUT.exists(), 'Preserve earlier preparation and frozen source'
    shutil.copytree(UPSTREAM / 'src', OUTPUT / 'src')
    acquisition = json.loads((UPSTREAM.parents[1]/'native_planner_manifest.original.json').read_text())
    for row in acquisition['files']:
        local = row['local_path'].split('integration/pct_scan_upstream_ws/',1)[1]
        assert sha(UPSTREAM/local)==row['upstream_sha256'], local
    for name in ('LICENSE','NOTICE','THIRD_PARTY_NOTICES.md'):
        shutil.copyfile(UPSTREAM/name,OUTPUT/name)
    # The current controller and message envelopes preserve the existing backend
    # contract. They are not claimed as upstream planning implementation.
    shutil.copytree(CURRENT / 'src/scan_planner_msgs', OUTPUT / 'src/scan_planner_msgs', dirs_exist_ok=True)
    shutil.copyfile(CURRENT / 'src/plan_manage/src/closed_loop_controller.cpp',
                    OUTPUT / 'src/plan_manage/src/closed_loop_controller.cpp')
    header_path = OUTPUT / 'src/plan_manage/include/plan_manage/scan_replan_fsm.h'
    header = read(header_path)
    current_header = read(CURRENT / header_path.relative_to(OUTPUT))
    identity = current_header[current_header.index('  struct P2BIdentity'):current_header.index('  class SCANReplanFSM')]
    header = replace_once(header, '  class SCANReplanFSM', identity + '  class SCANReplanFSM')
    header = replace_once(header, '#include <scan_planner_msgs/msg/data_disp.hpp>',
        '#include <scan_planner_msgs/msg/data_disp.hpp>\n'
        '#include <scan_planner_msgs/msg/p2_b_route.hpp>\n'
        '#include <scan_planner_msgs/msg/p2_b_cancel.hpp>\n'
        '#include <scan_planner_msgs/msg/p2_b_admission.hpp>\n'
        '#include <chrono>\n#include <cstdint>')
    header = replace_once(header, '    /* ROS utils */', '''    // v71 transport and observation only; no additional planning recovery.
    P2BIdentity active_p2b_identity_;
    bool have_p2b_identity_{false};
    int64_t p2b_route_generation_high_water_{0}, p2b_cancelled_generation_high_water_{0};
    rclcpp::Subscription<scan_planner_msgs::msg::P2BRoute>::SharedPtr p2b_route_sub_;
    rclcpp::Subscription<scan_planner_msgs::msg::P2BCancel>::SharedPtr p2b_cancel_sub_;
    rclcpp::Publisher<scan_planner_msgs::msg::P2BAdmission>::SharedPtr p2b_admission_pub_;
    void p2bRouteCallback(scan_planner_msgs::msg::P2BRoute::ConstSharedPtr msg);
    void p2bCancelCallback(scan_planner_msgs::msg::P2BCancel::ConstSharedPtr msg);
    bool p2bIdentityMatches(const scan_planner_msgs::msg::P2BCancel &msg) const;
    void publishP2BAdmission(const std::string &status, const std::string &message,
                            bool hold_confirmed=false, bool measured_stillness_confirmed=false);
    void attachP2BIdentity(scan_planner_msgs::msg::Bspline &bspline) const;
    int upstream_round_attempts_{0};
    uint64_t upstream_round_sequence_{0};
    bool observedReplan();
    bool observedNewTrajectory(bool random);
    /* ROS utils */''')
    header_path.write_text(header)
    fsm_path = OUTPUT / 'src/plan_manage/src/scan_replan_fsm.cpp'
    fsm = read(fsm_path)
    current = read(CURRENT / fsm_path.relative_to(OUTPUT))
    # Keep the original route callback itself; P2B just carries its input and
    # acknowledges actual completion on the native executor.
    route = '''  void SCANReplanFSM::p2bRouteCallback(scan_planner_msgs::msg::P2BRoute::ConstSharedPtr msg)
  {
    if (!msg) return;
    P2BIdentity candidate{msg->run_id, msg->epoch, msg->request_id, msg->goal_id,
        msg->route_id, msg->command_id, msg->generation, msg->map_epoch, msg->map_revision};
    const auto previous = active_p2b_identity_;
    const bool previous_have = have_p2b_identity_;
    active_p2b_identity_ = candidate; have_p2b_identity_ = true;
    if (candidate.run_id.empty() || candidate.route_id.empty() || candidate.command_id.empty() ||
        candidate.generation <= 0 || candidate.generation <= p2b_cancelled_generation_high_water_ ||
        candidate.generation < p2b_route_generation_high_water_ || !have_odom_ || msg->path.poses.empty()) {
      publishP2BAdmission("rejected", "upstream_transport_invalid_route");
      active_p2b_identity_ = previous; have_p2b_identity_ = previous_have; return;
    }
    for (const auto &pose : msg->path.poses) {
      const auto &p = pose.pose.position;
      if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z)) {
        publishP2BAdmission("rejected", "nonfinite_upstream_route");
        active_p2b_identity_ = previous; have_p2b_identity_ = previous_have; return;
      }
    }
    const auto saved_global = planner_manager_->global_data_;
    const auto saved_end = end_pt_;
    const bool saved_target = have_target_, saved_trigger = trigger_, saved_new = have_new_target_;
    have_target_ = false;
    pathCallback(std::make_shared<nav_msgs::msg::Path>(msg->path));
    if (have_target_) {
      p2b_route_generation_high_water_ = std::max(p2b_route_generation_high_water_, candidate.generation);
      publishP2BAdmission("accepted", "upstream_path_callback_accepted");
    } else {
      publishP2BAdmission("rejected", "upstream_path_callback_failed");
      active_p2b_identity_ = previous; have_p2b_identity_ = previous_have;
      planner_manager_->global_data_ = saved_global; end_pt_ = saved_end;
      have_target_ = saved_target; trigger_ = saved_trigger; have_new_target_ = saved_new;
    }
  }

'''
    # These four functions are copied verbatim from the existing interface. No
    # alternative stop acknowledgment or deadline is introduced.
    transport = current[current.index('  bool SCANReplanFSM::p2bIdentityMatches'):current.index('  void SCANReplanFSM::pathCallback')]
    fsm = replace_once(fsm, '  void SCANReplanFSM::pathCallback', route + transport + '  void SCANReplanFSM::pathCallback')
    init_anchor = '    bspline_pub_ = node_->create_publisher<scan_planner_msgs::msg::Bspline>("planning/bspline", 10);'
    init_transport = current[current.index('    p2b_admission_pub_ ='):current.index('    data_disp_pub_ =')]
    fsm = replace_once(fsm, init_anchor, init_anchor + '\n' + init_transport)
    # Every published curve keeps the backend's identity. Geometry/PVA are the
    # exact original output; emergency flag preserves the existing controller.
    assert fsm.count('bspline.traj_id = info->traj_id_;') == 2
    fsm = fsm.replace('bspline.traj_id = info->traj_id_;', 'bspline.traj_id = info->traj_id_;\n      attachP2BIdentity(bspline);')
    start = fsm.index('  bool SCANReplanFSM::callEmergencyStop')
    fsm = fsm[:start] + replace_once(fsm[start:], '    bspline.order = 3;', '    bspline.emergency_stop = true;\n    bspline.order = 3;')
    # Observe the complete original three-mode synchronous chain and each
    # individual call. The timers/conditions/algorithm remain upstream.
    assert fsm.count('if (planFromCurrentTraj())') == 2
    fsm = fsm.replace('if (planFromCurrentTraj())', 'if (observedReplan())')
    fsm = replace_once(fsm, 'bool success = callReboundReplan(true, flag_random_poly_init);',
        'bool success = observedNewTrajectory(flag_random_poly_init);')
    observer = '''  bool SCANReplanFSM::observedReplan()
  {
    const auto start = std::chrono::steady_clock::now();
    const auto sequence = ++upstream_round_sequence_;
    upstream_round_attempts_ = 0;
    const double simulation = node_->now().seconds();
    const bool success = planFromCurrentTraj();
    const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now()-start).count();
    RCLCPP_INFO(node_->get_logger(), "V71_UPSTREAM_ROUND sequence=%llu sim=%.9f start_wall=%.9f wall_ms=%.9f attempts=%d success=%d",
        static_cast<unsigned long long>(sequence), simulation,
        std::chrono::duration<double>(start.time_since_epoch()).count(), ms, upstream_round_attempts_, success);
    return success;
  }

  bool SCANReplanFSM::observedNewTrajectory(bool random)
  {
    const auto start = std::chrono::steady_clock::now();
    const auto sequence = ++upstream_round_sequence_;
    upstream_round_attempts_ = 0;
    const double simulation = node_->now().seconds();
    const bool success = callReboundReplan(true, random);
    const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now()-start).count();
    RCLCPP_INFO(node_->get_logger(), "V71_UPSTREAM_ROUND sequence=%llu sim=%.9f start_wall=%.9f wall_ms=%.9f attempts=%d success=%d",
        static_cast<unsigned long long>(sequence), simulation,
        std::chrono::duration<double>(start.time_since_epoch()).count(), ms, upstream_round_attempts_, success);
    return success;
  }

'''
    fsm = replace_once(fsm, '  bool SCANReplanFSM::planFromCurrentTraj()', observer + '  bool SCANReplanFSM::planFromCurrentTraj()')
    call = '  bool SCANReplanFSM::callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj)\n  {'
    fsm = replace_once(fsm, call, call + '\n    ++upstream_round_attempts_;')
    fsm_path.write_text(fsm)
    # Canonical message/controller/build changes are explicitly separated from
    # the timing/transport-only changes to upstream planning.
    records = {str(p.relative_to(OUTPUT)): sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'source_sha256.json').write_text(json.dumps(records,indent=2)+'\n')
    canonical = {str(p.relative_to(UPSTREAM)):sha(p) for p in UPSTREAM.rglob('*') if p.is_file()}
    changed = [name for name,h in canonical.items() if records.get(name)!=h]
    added = [name for name in records if name not in canonical]
    assert set(changed) == {'src/plan_manage/include/plan_manage/scan_replan_fsm.h',
        'src/plan_manage/src/scan_replan_fsm.cpp', 'src/plan_manage/src/closed_loop_controller.cpp',
        'src/scan_planner_msgs/CMakeLists.txt', 'src/scan_planner_msgs/package.xml', 'src/scan_planner_msgs/msg/Bspline.msg'}
    core_exact = ['src/plan_manage/src/planner_manager.cpp', 'src/plan_manage/include/plan_manage/planner_manager.h',
        'src/bspline_opt/src/bspline_optimizer.cpp', 'src/path_searching/src/dyn_a_star.cpp',
        'src/plan_env/src/grid_map.cpp', 'src/bspline_opt/src/uniform_bspline.cpp']
    assert all(records[name]==canonical[name] for name in core_exact)
    diff = ''.join(''.join(difflib.unified_diff(read(UPSTREAM/name).splitlines(True),
        read(OUTPUT/name).splitlines(True), fromfile='upstream/'+name,tofile='v71/'+name)) for name in changed)
    (HERE/'upstream_adaptations.patch').write_text(diff)
    (HERE/'upstream_identity.json').write_text(json.dumps({
        'repository':'https://github.com/yagami-light7/PCT-SCAN-ROS2',
        'commit':'1cf45a1c12ca785ce533293302be09d51daf0ccb',
        'canonical_source_sha256':canonical,'changed_paths':sorted(changed),'added_paths':sorted(added),
        'planning_core_byte_exact':core_exact,'current_controller_sha256':sha(CURRENT/'src/plan_manage/src/closed_loop_controller.cpp'),
        'native_root':str(OUTPUT.relative_to(ROOT)),
        'claim':'Upstream ROS2 planning core with original target/retry/FSM behavior; existing identity/controller/stop transport, timing observation only.'
    },indent=2)+'\n')
    print(json.dumps({'source_files':len(records),'changed':sorted(changed),'added':len(added)}))


if __name__ == '__main__':
    main()

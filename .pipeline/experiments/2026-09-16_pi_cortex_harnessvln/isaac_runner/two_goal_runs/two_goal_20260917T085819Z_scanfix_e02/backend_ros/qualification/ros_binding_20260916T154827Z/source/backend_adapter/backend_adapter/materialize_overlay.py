"""Hash-gated materializer for the P2B SCAN/Foxy overlay."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
from typing import Dict

EXPECTED = {
    "plan_manage/include/plan_manage/scan_replan_fsm.h": "b97e789e87db1e4e4c51848a418e651e90ff46ec231d943b99f93cea7ca06ed6",
    "plan_manage/src/scan_replan_fsm.cpp": "bb5fa854031ecb9a94fc9b3aeff0a225a48ff3bb81cefdc9f345659afcf285eb",
    "plan_manage/src/closed_loop_controller.cpp": "32d3e2c75f3dc2177c496c30bd483d28791ba17685fe7c8a41b6ad909631fcd7",
    "scan_planner_msgs/CMakeLists.txt": "fde831fa5746fcf8121eec9f960617f5bc8433bdea06cb9683643a1835c10863",
    "scan_planner_msgs/package.xml": "ac8cffb52a76590efbdd8f43b7d3cbabfe73932968135ca2aec53c4eb42c2fb1",
    "scan_planner_msgs/msg/Bspline.msg": "60040920d4c09184baa540fad8babbec6b3e4e81c7d80522d4bedd048e162fbc",
}

IDENTITY_FIELDS = """string run_id
int64 epoch
string request_id
string goal_id
string route_id
string command_id
int64 generation
string map_epoch
int64 map_revision
"""


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def replace_once(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError("pattern_missing:%s" % path)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError("pattern_missing:%s" % path)
    path.write_text(text.replace(old, new), encoding="utf-8")


def _is_relative_to(path: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def copy_source(source: pathlib.Path, output: pathlib.Path) -> None:
    if not source.is_dir():
        raise RuntimeError("source_not_directory:%s" % source)
    source_r = source.resolve()
    output_r = output.resolve()
    if output_r == source_r or _is_relative_to(output_r, source_r) or _is_relative_to(source_r, output_r):
        raise RuntimeError("unsafe_overlay_output_path")
    if output.exists():
        raise RuntimeError("overlay_output_already_exists:%s" % output)
    shutil.copytree(str(source), str(output))


def verify_expected(root: pathlib.Path) -> Dict[str, str]:
    hashes = {}
    for rel, expected in EXPECTED.items():
        path = root / rel
        if not path.is_file():
            raise RuntimeError("missing_expected_source:%s" % rel)
        digest = sha256(path)
        hashes[rel] = digest
        if digest != expected:
            raise RuntimeError("hash_mismatch:%s:%s:%s" % (rel, digest, expected))
    return hashes


def append_messages(root: pathlib.Path) -> None:
    msg_dir = root / "scan_planner_msgs/msg"
    (msg_dir / "P2BRoute.msg").write_text(IDENTITY_FIELDS + "nav_msgs/Path path\n", encoding="utf-8")
    (msg_dir / "P2BCancel.msg").write_text(IDENTITY_FIELDS + "string reason\n", encoding="utf-8")
    (msg_dir / "P2BAdmission.msg").write_text(IDENTITY_FIELDS + "string consumer\nstring status\nstring message\nbool hold_confirmed\nbool measured_stillness_confirmed\nint64 traj_id\n", encoding="utf-8")
    (msg_dir / "P2BStampedTwist.msg").write_text(IDENTITY_FIELDS + "builtin_interfaces/Time stamp\nint64 traj_id\ngeometry_msgs/Twist twist\n", encoding="utf-8")
    bspline = msg_dir / "Bspline.msg"
    bspline.write_text(bspline.read_text(encoding="utf-8") + "\n# P2B command identity propagated from route admission to the controller.\n" + IDENTITY_FIELDS, encoding="utf-8")
    cmake = root / "scan_planner_msgs/CMakeLists.txt"
    replace_once(cmake, "find_package(geometry_msgs REQUIRED)\n", "find_package(geometry_msgs REQUIRED)\nfind_package(nav_msgs REQUIRED)\n")
    replace_once(cmake, '  "msg/DataDisp.msg"\n', '  "msg/DataDisp.msg"\n  "msg/P2BRoute.msg"\n  "msg/P2BCancel.msg"\n  "msg/P2BAdmission.msg"\n  "msg/P2BStampedTwist.msg"\n')
    replace_once(cmake, "DEPENDENCIES builtin_interfaces geometry_msgs std_msgs", "DEPENDENCIES builtin_interfaces geometry_msgs nav_msgs std_msgs")
    package = root / "scan_planner_msgs/package.xml"
    replace_once(package, "  <depend>geometry_msgs</depend>\n", "  <depend>geometry_msgs</depend>\n  <depend>nav_msgs</depend>\n")


def patch_fsm_header(root: pathlib.Path) -> None:
    path = root / "plan_manage/include/plan_manage/scan_replan_fsm.h"
    replace_once(path, "#include <scan_planner_msgs/msg/data_disp.hpp>\n", "#include <scan_planner_msgs/msg/data_disp.hpp>\n#include <scan_planner_msgs/msg/p2_b_admission.hpp>\n#include <scan_planner_msgs/msg/p2_b_cancel.hpp>\n#include <scan_planner_msgs/msg/p2_b_route.hpp>\n")
    replace_once(path, "namespace scan_planner\n{\n", "namespace scan_planner\n{\n\n  struct P2BIdentity\n  {\n    std::string run_id;\n    int64_t epoch{0};\n    std::string request_id;\n    std::string goal_id;\n    std::string route_id;\n    std::string command_id;\n    int64_t generation{0};\n    std::string map_epoch;\n    int64_t map_revision{0};\n  };\n")
    replace_once(path, "    bool go2_execution_frozen_;\n", "    bool go2_execution_frozen_;\n    bool p2b_explicit_mode_{true};\n    bool have_p2b_identity_{false};\n    P2BIdentity active_p2b_identity_;\n    int64_t p2b_route_generation_high_water_{0};\n    int64_t p2b_cancelled_generation_high_water_{0};\n")
    replace_once(path, "    rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr path_sub_;\n", "    rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr path_sub_;\n    rclcpp::Subscription<scan_planner_msgs::msg::P2BRoute>::SharedPtr p2b_route_sub_;\n    rclcpp::Subscription<scan_planner_msgs::msg::P2BCancel>::SharedPtr p2b_cancel_sub_;\n")
    replace_once(path, "    rclcpp::Publisher<scan_planner_msgs::msg::DataDisp>::SharedPtr data_disp_pub_;\n", "    rclcpp::Publisher<scan_planner_msgs::msg::DataDisp>::SharedPtr data_disp_pub_;\n    rclcpp::Publisher<scan_planner_msgs::msg::P2BAdmission>::SharedPtr p2b_admission_pub_;\n")
    replace_once(path, "    void pathCallback(nav_msgs::msg::Path::ConstSharedPtr msg);\n", "    void pathCallback(nav_msgs::msg::Path::ConstSharedPtr msg);\n    void p2bRouteCallback(scan_planner_msgs::msg::P2BRoute::ConstSharedPtr msg);\n    void p2bCancelCallback(scan_planner_msgs::msg::P2BCancel::ConstSharedPtr msg);\n    bool p2bIdentityMatches(const scan_planner_msgs::msg::P2BCancel &msg) const;\n    void publishP2BAdmission(const std::string &status, const std::string &message, bool hold_confirmed=false, bool measured_stillness_confirmed=false);\n    void attachP2BIdentity(scan_planner_msgs::msg::Bspline &bspline) const;\n")


def patch_fsm_cpp(root: pathlib.Path) -> None:
    path = root / "plan_manage/src/scan_replan_fsm.cpp"
    replace_once(path, "    bspline_pub_ = node_->create_publisher<scan_planner_msgs::msg::Bspline>(\"planning/bspline\", 10);\n", "    bspline_pub_ = node_->create_publisher<scan_planner_msgs::msg::Bspline>(\"planning/bspline\", 10);\n    p2b_admission_pub_ = node_->create_publisher<scan_planner_msgs::msg::P2BAdmission>(\"/p2b/scan_admission\", 10);\n    p2b_route_sub_ = node_->create_subscription<scan_planner_msgs::msg::P2BRoute>(\n        \"/p2b/route\", rclcpp::QoS(1).reliable(),\n        std::bind(&SCANReplanFSM::p2bRouteCallback, this, std::placeholders::_1));\n    p2b_cancel_sub_ = node_->create_subscription<scan_planner_msgs::msg::P2BCancel>(\n        \"/p2b/scan_cancel\", rclcpp::QoS(10).reliable(),\n        std::bind(&SCANReplanFSM::p2bCancelCallback, this, std::placeholders::_1));\n")
    p2b_block = r'''
  void SCANReplanFSM::p2bRouteCallback(scan_planner_msgs::msg::P2BRoute::ConstSharedPtr msg)
  {
    if (!msg) return;
    P2BIdentity candidate;
    candidate.run_id = msg->run_id;
    candidate.epoch = msg->epoch;
    candidate.request_id = msg->request_id;
    candidate.goal_id = msg->goal_id;
    candidate.route_id = msg->route_id;
    candidate.command_id = msg->command_id;
    candidate.generation = msg->generation;
    candidate.map_epoch = msg->map_epoch;
    candidate.map_revision = msg->map_revision;
    auto publish_candidate = [&](const std::string &status, const std::string &message, bool hold_confirmed=false, bool measured_stillness_confirmed=false) {
      if (!p2b_admission_pub_) return;
      scan_planner_msgs::msg::P2BAdmission out;
      out.run_id = candidate.run_id;
      out.epoch = candidate.epoch;
      out.request_id = candidate.request_id;
      out.goal_id = candidate.goal_id;
      out.route_id = candidate.route_id;
      out.command_id = candidate.command_id;
      out.generation = candidate.generation;
      out.map_epoch = candidate.map_epoch;
      out.map_revision = candidate.map_revision;
      out.consumer = "fsm";
      out.status = status;
      out.message = message;
      out.hold_confirmed = hold_confirmed;
      out.measured_stillness_confirmed = measured_stillness_confirmed;
      out.traj_id = planner_manager_ ? planner_manager_->local_data_.traj_id_ : 0;
      p2b_admission_pub_->publish(out);
    };
    if (candidate.run_id.empty() || candidate.route_id.empty() || candidate.command_id.empty() || candidate.generation <= 0)
    {
      publish_candidate("rejected", "missing_p2b_identity");
      return;
    }
    if (candidate.generation <= p2b_cancelled_generation_high_water_)
    {
      publish_candidate("rejected", "generation_cancelled_before_route");
      return;
    }
    if (candidate.generation < p2b_route_generation_high_water_)
    {
      publish_candidate("rejected", "stale_route_generation");
      return;
    }
    if (!have_odom_)
    {
      publish_candidate("rejected", "no_odometry_for_p2b_route");
      return;
    }
    if (msg->path.poses.empty())
    {
      publish_candidate("rejected", "empty_p2b_route");
      return;
    }
    std::vector<Eigen::Vector3d> waypoints;
    std::string path_error;
    if (!prepareReferenceWaypoints(msg->path, body_height_, reference_path_min_distance_, waypoints, &path_error, reference_path_simplify_tolerance_))
    {
      publish_candidate("rejected", path_error);
      return;
    }
    const bool previous_have_p2b_identity = have_p2b_identity_;
    const P2BIdentity previous_identity = active_p2b_identity_;
    active_p2b_identity_ = candidate;
    have_p2b_identity_ = true;
    trigger_ = true;
    end_pt_ = waypoints.back();
    const bool success = planGlobalTrajByWaypoints(waypoints);
    if (success)
    {
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
    }
  }

  bool SCANReplanFSM::p2bIdentityMatches(const scan_planner_msgs::msg::P2BCancel &msg) const
  {
    return have_p2b_identity_ && msg.run_id == active_p2b_identity_.run_id && msg.epoch == active_p2b_identity_.epoch && msg.request_id == active_p2b_identity_.request_id && msg.goal_id == active_p2b_identity_.goal_id && msg.route_id == active_p2b_identity_.route_id && msg.command_id == active_p2b_identity_.command_id && msg.generation == active_p2b_identity_.generation;
  }

  void SCANReplanFSM::p2bCancelCallback(scan_planner_msgs::msg::P2BCancel::ConstSharedPtr msg)
  {
    if (!msg) return;
    auto publish_cancel = [&](const std::string &status, const std::string &message, bool hold_confirmed=false, bool measured_stillness_confirmed=false) {
      if (!p2b_admission_pub_) return;
      scan_planner_msgs::msg::P2BAdmission out;
      out.run_id = msg->run_id;
      out.epoch = msg->epoch;
      out.request_id = msg->request_id;
      out.goal_id = msg->goal_id;
      out.route_id = msg->route_id;
      out.command_id = msg->command_id;
      out.generation = msg->generation;
      out.map_epoch = msg->map_epoch;
      out.map_revision = msg->map_revision;
      out.consumer = "fsm";
      out.status = status;
      out.message = message;
      out.hold_confirmed = hold_confirmed;
      out.measured_stillness_confirmed = measured_stillness_confirmed;
      out.traj_id = planner_manager_ ? planner_manager_->local_data_.traj_id_ : 0;
      p2b_admission_pub_->publish(out);
    };
    if (!p2bIdentityMatches(*msg))
    {
      if (msg->generation >= p2b_route_generation_high_water_ && msg->generation > p2b_cancelled_generation_high_water_)
      {
        p2b_cancelled_generation_high_water_ = msg->generation;
        publish_cancel("stopped", msg->reason.empty() ? "idle_cancel_hold" : msg->reason, true, false);
      }
      return;
    }
    p2b_cancelled_generation_high_water_ = std::max(p2b_cancelled_generation_high_water_, msg->generation);
    need_hover_stop_ = true;
    have_target_ = false;
    trigger_ = false;
    active_waypoints_.clear();
    current_wp_ = 0;
    callEmergencyStop(odom_pos_);
    changeFSMExecState(EMERGENCY_STOP, "P2B_CANCEL");
    publishP2BAdmission("stopped", msg->reason.empty() ? "p2b_cancel_hold" : msg->reason, true, false);
  }

  void SCANReplanFSM::publishP2BAdmission(const std::string &status, const std::string &message, bool hold_confirmed, bool measured_stillness_confirmed)
  {
    if (!have_p2b_identity_ || !p2b_admission_pub_) return;
    scan_planner_msgs::msg::P2BAdmission out;
    out.run_id = active_p2b_identity_.run_id;
    out.epoch = active_p2b_identity_.epoch;
    out.request_id = active_p2b_identity_.request_id;
    out.goal_id = active_p2b_identity_.goal_id;
    out.route_id = active_p2b_identity_.route_id;
    out.command_id = active_p2b_identity_.command_id;
    out.generation = active_p2b_identity_.generation;
    out.map_epoch = active_p2b_identity_.map_epoch;
    out.map_revision = active_p2b_identity_.map_revision;
    out.consumer = "fsm";
    out.status = status;
    out.message = message;
    out.hold_confirmed = hold_confirmed;
    out.measured_stillness_confirmed = measured_stillness_confirmed;
    out.traj_id = planner_manager_ ? planner_manager_->local_data_.traj_id_ : 0;
    p2b_admission_pub_->publish(out);
  }

  void SCANReplanFSM::attachP2BIdentity(scan_planner_msgs::msg::Bspline &bspline) const
  {
    if (!have_p2b_identity_) return;
    bspline.run_id = active_p2b_identity_.run_id;
    bspline.epoch = active_p2b_identity_.epoch;
    bspline.request_id = active_p2b_identity_.request_id;
    bspline.goal_id = active_p2b_identity_.goal_id;
    bspline.route_id = active_p2b_identity_.route_id;
    bspline.command_id = active_p2b_identity_.command_id;
    bspline.generation = active_p2b_identity_.generation;
    bspline.map_epoch = active_p2b_identity_.map_epoch;
    bspline.map_revision = active_p2b_identity_.map_revision;
  }

'''

    replace_once(path, "  void SCANReplanFSM::pathCallback(nav_msgs::msg::Path::ConstSharedPtr msg)\n  {\n", p2b_block + "  void SCANReplanFSM::pathCallback(nav_msgs::msg::Path::ConstSharedPtr msg)\n  {\n    if (p2b_explicit_mode_)\n    {\n      RCLCPP_WARN(node_->get_logger(), \"Ignoring legacy initial_path in explicit P2B typed-route mode\");\n      return;\n    }\n")
    replace_all(path, "bspline.traj_id = info->traj_id_;", "bspline.traj_id = info->traj_id_;\n      attachP2BIdentity(bspline);")


def patch_controller(root: pathlib.Path) -> None:
    path = root / "plan_manage/src/closed_loop_controller.cpp"
    text = path.read_text(encoding="utf-8")
    text = text.replace("#include <scan_planner_msgs/msg/bspline.hpp>\n", "#include <algorithm>\n#include <scan_planner_msgs/msg/bspline.hpp>\n#include <scan_planner_msgs/msg/p2_b_admission.hpp>\n#include <scan_planner_msgs/msg/p2_b_cancel.hpp>\n#include <scan_planner_msgs/msg/p2_b_stamped_twist.hpp>\n")
    text = text.replace('    cmd_vel_pub_ = create_publisher<geometry_msgs::msg::Twist>("cmd_vel", 20);\n', '    raw_cmd_pub_ = create_publisher<scan_planner_msgs::msg::P2BStampedTwist>("/quad_0/raw_scan_cmd_vel", 20);\n    p2b_admission_pub_ = create_publisher<scan_planner_msgs::msg::P2BAdmission>("/p2b/scan_admission", 10);\n    p2b_cancel_sub_ = create_subscription<scan_planner_msgs::msg::P2BCancel>("/p2b/scan_cancel", 10, std::bind(&ClosedLoopController::p2bCancelCallback, this, std::placeholders::_1));\n')
    helper_old = '''  void publishStop(double yaw_rate = 0.0)
  {
    geometry_msgs::msg::Twist cmd;
    cmd.angular.z = std::clamp(yaw_rate, -max_vyaw_, max_vyaw_);
    cmd_vel_pub_->publish(cmd);
  }
'''
    helper_new = r'''  void fillIdentity(scan_planner_msgs::msg::P2BStampedTwist &out) const
  {
    out.run_id = run_id_;
    out.epoch = epoch_;
    out.request_id = request_id_;
    out.goal_id = goal_id_;
    out.route_id = route_id_;
    out.command_id = command_id_;
    out.generation = generation_;
    out.map_epoch = map_epoch_;
    out.map_revision = map_revision_;
    out.traj_id = traj_id_;
    out.stamp = now();
  }

  void publishTaggedCommand(const geometry_msgs::msg::Twist &cmd)
  {
    scan_planner_msgs::msg::P2BStampedTwist out;
    fillIdentity(out);
    out.twist = cmd;
    raw_cmd_pub_->publish(out);
  }

  void publishStop(double yaw_rate = 0.0)
  {
    geometry_msgs::msg::Twist cmd;
    cmd.angular.z = std::clamp(yaw_rate, -max_vyaw_, max_vyaw_);
    publishTaggedCommand(cmd);
  }

  bool cancelMatches(const scan_planner_msgs::msg::P2BCancel &msg) const
  {
    return have_p2b_identity_ && msg.run_id == run_id_ && msg.epoch == epoch_ && msg.request_id == request_id_ && msg.goal_id == goal_id_ && msg.route_id == route_id_ && msg.command_id == command_id_ && msg.generation == generation_;
  }

  void publishAdmissionForIdentity(const std::string &status, const std::string &message, bool hold_confirmed,
                                  const std::string &run_id, std::int64_t epoch, const std::string &request_id,
                                  const std::string &goal_id, const std::string &route_id, const std::string &command_id,
                                  std::int64_t generation, const std::string &map_epoch, std::int64_t map_revision,
                                  std::int64_t traj_id)
  {
    scan_planner_msgs::msg::P2BAdmission out;
    out.run_id = run_id;
    out.epoch = epoch;
    out.request_id = request_id;
    out.goal_id = goal_id;
    out.route_id = route_id;
    out.command_id = command_id;
    out.generation = generation;
    out.map_epoch = map_epoch;
    out.map_revision = map_revision;
    out.consumer = "controller";
    out.status = status;
    out.message = message;
    out.hold_confirmed = hold_confirmed;
    out.measured_stillness_confirmed = false;
    out.traj_id = traj_id;
    p2b_admission_pub_->publish(out);
  }

  void publishAdmission(const std::string &status, const std::string &message, bool hold_confirmed)
  {
    if (!have_p2b_identity_) return;
    publishAdmissionForIdentity(status, message, hold_confirmed, run_id_, epoch_, request_id_, goal_id_, route_id_, command_id_, generation_, map_epoch_, map_revision_, traj_id_);
  }

  void p2bCancelCallback(const scan_planner_msgs::msg::P2BCancel::ConstSharedPtr msg)
  {
    if (!msg) return;
    if (!cancelMatches(*msg))
    {
      if (msg->generation >= max_generation_seen_ && msg->generation > cancelled_generation_high_water_)
      {
        cancelled_generation_high_water_ = msg->generation;
        const bool saved_have = have_p2b_identity_;
        publishStop();
        have_p2b_identity_ = saved_have;
        publishAdmissionForIdentity("stopped", msg->reason.empty() ? "idle_controller_hold" : msg->reason, true,
                                    msg->run_id, msg->epoch, msg->request_id, msg->goal_id, msg->route_id, msg->command_id,
                                    msg->generation, msg->map_epoch, msg->map_revision, traj_id_);
      }
      return;
    }
    cancelled_generation_high_water_ = std::max(cancelled_generation_high_water_, msg->generation);
    receive_traj_ = false;
    exec_time_ = 0.0;
    publishStop();
    publishExecutionFrozen(false);
    publishAdmission("stopped", msg->reason.empty() ? "controller_hold" : msg->reason, true);
  }
'''
    if helper_old not in text:
        raise RuntimeError("controller_publish_stop_anchor_missing")
    text = text.replace(helper_old, helper_new)
    bspline_guard_old = '''    Eigen::MatrixXd points(3, msg->pos_pts.size());
'''
    bspline_guard_new = '''    const bool incoming_has_p2b_identity = !msg->command_id.empty() && msg->generation > 0;
    if (incoming_has_p2b_identity)
    {
      if (msg->generation <= cancelled_generation_high_water_)
      {
        publishAdmissionForIdentity("rejected", "generation_cancelled_before_spline", false,
                                    msg->run_id, msg->epoch, msg->request_id, msg->goal_id, msg->route_id, msg->command_id,
                                    msg->generation, msg->map_epoch, msg->map_revision, msg->traj_id);
        return;
      }
      if (msg->generation < max_generation_seen_)
      {
        publishAdmissionForIdentity("rejected", "stale_spline_generation", false,
                                    msg->run_id, msg->epoch, msg->request_id, msg->goal_id, msg->route_id, msg->command_id,
                                    msg->generation, msg->map_epoch, msg->map_revision, msg->traj_id);
        return;
      }
    }
    Eigen::MatrixXd points(3, msg->pos_pts.size());
'''
    if bspline_guard_old not in text:
        raise RuntimeError("controller_bspline_guard_anchor_missing")
    text = text.replace(bspline_guard_old, bspline_guard_new)
    bspline_commit_old = '''    traj_id_ = msg->traj_id;
    exec_time_ = 0.0;
'''
    bspline_commit_new = '''    traj_id_ = msg->traj_id;
    run_id_ = msg->run_id;
    epoch_ = msg->epoch;
    request_id_ = msg->request_id;
    goal_id_ = msg->goal_id;
    route_id_ = msg->route_id;
    command_id_ = msg->command_id;
    generation_ = msg->generation;
    map_epoch_ = msg->map_epoch;
    map_revision_ = msg->map_revision;
    have_p2b_identity_ = incoming_has_p2b_identity;
    if (have_p2b_identity_) max_generation_seen_ = std::max(max_generation_seen_, generation_);
    exec_time_ = 0.0;
    if (have_p2b_identity_) publishAdmission("accepted", "controller_bspline_accepted", false);
'''
    if bspline_commit_old not in text:
        raise RuntimeError("controller_bspline_commit_anchor_missing")
    text = text.replace(bspline_commit_old, bspline_commit_new)
    text = text.replace('    cmd_vel_pub_->publish(command);\n', '    publishTaggedCommand(command);\n')
    text = text.replace('  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;\n', '  rclcpp::Publisher<scan_planner_msgs::msg::P2BStampedTwist>::SharedPtr raw_cmd_pub_;\n  rclcpp::Publisher<scan_planner_msgs::msg::P2BAdmission>::SharedPtr p2b_admission_pub_;\n  rclcpp::Subscription<scan_planner_msgs::msg::P2BCancel>::SharedPtr p2b_cancel_sub_;\n')
    text = text.replace('  std::int64_t traj_id_{0};\n', '  std::int64_t traj_id_{0};\n  bool have_p2b_identity_{false};\n  std::int64_t max_generation_seen_{0};\n  std::int64_t cancelled_generation_high_water_{0};\n  std::string run_id_, request_id_, goal_id_, route_id_, command_id_, map_epoch_;\n  std::int64_t epoch_{0}, generation_{0}, map_revision_{0};\n')
    path.write_text(text, encoding="utf-8")

def write_launch(root: pathlib.Path) -> None:
    (root / "plan_manage/launch/p2b_scan.launch.py").write_text('''from launch import LaunchDescription\nfrom launch_ros.actions import Node\n\n\ndef generate_launch_description():\n    return LaunchDescription([\n        Node(package="scan_planner", executable="scan_planner_node", name="scan_planner_node", output="screen", parameters=["config/planner.yaml"]),\n        Node(package="scan_planner", executable="closed_loop_controller", name="closed_loop_controller", output="screen", parameters=["config/controllers.yaml"]),\n    ])\n''', encoding="utf-8")


def materialize(source: pathlib.Path, output: pathlib.Path) -> Dict[str, object]:
    source = source.resolve()
    output = output.resolve()
    before = verify_expected(source)
    copy_source(source, output)
    append_messages(output)
    patch_fsm_header(output)
    patch_fsm_cpp(output)
    patch_controller(output)
    write_launch(output)
    after = {str(p.relative_to(output)): sha256(p) for p in sorted(output.rglob("*")) if p.is_file()}
    return {"schema": "p2b_scan_overlay_manifest_v1", "source": str(source), "output": str(output), "before": before, "after": after}


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize P2B SCAN overlay")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest")
    args = parser.parse_args()
    result = materialize(pathlib.Path(args.source).resolve(), pathlib.Path(args.output).resolve())
    manifest = pathlib.Path(args.manifest).resolve() if args.manifest else pathlib.Path(args.output).resolve() / "P2B_OVERLAY_MANIFEST.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(manifest), "output": result["output"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

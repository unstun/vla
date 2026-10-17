#!/usr/bin/env python3
"""Hash-gated local SCAN overlay with PCT support and current-person intake."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
P2B = HERE.parent
SOURCE = P2B / "builds/scan_04"
OUTPUT = P2B / "builds/scan_06"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("scan05_gate", HERE / "materialize_scan_05.py")
scan05_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan05_gate)


class Refused(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(data: bytes, old: bytes, new: bytes, description: str) -> bytes:
    count = data.count(old)
    if count != 1:
        raise Refused(f"{description}: expected one anchor, got {count}")
    return data.replace(old, new)


def after_line(data: bytes, anchor: str, inserted: list[str]) -> bytes:
    lines = data.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.rstrip(b"\r\n").decode() == anchor]
    if len(matches) != 1:
        raise Refused(f"line anchor {anchor!r}: matches={len(matches)}")
    i = matches[0]
    ending = b"\r\n" if lines[i].endswith(b"\r\n") else b"\n"
    return b"".join(lines[:i + 1] + [line.encode() + ending for line in inserted] + lines[i + 1:])


def patch_sources(root: Path) -> dict[str, str]:
    changed = {}
    grid_h = root / "plan_env/include/plan_env/grid_map.h"
    data = grid_h.read_bytes()
    data = after_line(data, "#include <plan_env/raycast.h>", [
        "#include <plan_env/reactive_collision.h>",
        "#include <scan_planner_msgs/msg/tracked_person_snapshot.hpp>",
        "#include <set>",
    ])
    data = after_line(data, "  inline int getInflateOccupancyFromBuffer(Eigen::Vector3d pos, const std::vector<char>& buffer);", [
        "  int reactiveOccupancy(const Eigen::Vector3d &point);",
        "  bool reactiveTerrainReturn(const Eigen::Vector3d &point) const;",
        "  void reactiveTomogramCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg);",
        "  void reactiveTracksCallback(scan_planner_msgs::msg::TrackedPersonSnapshot::ConstSharedPtr msg);",
    ])
    data = after_line(data, "  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_sub_;", [
        "  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr reactive_tomogram_sub_;",
        "  rclcpp::Subscription<scan_planner_msgs::msg::TrackedPersonSnapshot>::SharedPtr reactive_tracks_sub_;",
        "  reactive_stair::Parameters reactive_parameters_;",
        "  reactive_stair::CollisionDecision reactive_decision_{reactive_parameters_};",
        "  reactive_stair::TerrainSnapshot reactive_terrain_;",
        "  std::set<std::tuple<int, int, int>> reactive_terrain_hits_;",
        "  std::set<std::tuple<int, int, int>> reactive_nonterrain_hits_;",
        "  std::set<std::tuple<int, int, int>> reactive_nonterrain_history_;",
        "  double reactive_cloud_stamp_s_ = 0.0;",
        "  bool reactive_cloud_ready_ = false;",
        "  bool reactive_pending_cloud_ = false;",
        "  double reactive_tomogram_resolution_m_ = 0.1;",
        "  double reactive_tomogram_z_offset_m_ = 0.03;",
        "  double reactive_terrain_band_m_ = 0.05;",
        "  double reactive_cost_limit_ = 20.0;",
    ])
    start = data.index(b"inline int GridMap::getInflateOccupancy(Eigen::Vector3d pos, double yaw) {")
    end = data.index(b"inline int GridMap::getInflateOccupancyFromBuffer", start)
    old = data[start:end]
    ending = b"\r\n" if old.splitlines(keepends=True)[0].endswith(b"\r\n") else b"\n"
    replacement = ending.join(line.encode() for line in [
        "inline int GridMap::getInflateOccupancy(Eigen::Vector3d pos, double yaw) {",
        "  if (!pos.allFinite() || !std::isfinite(yaw)) return 1;",
        "  Eigen::Vector3d heading(std::cos(yaw), std::sin(yaw), 0.0);",
        "  Eigen::Vector3d front = pos + mp_.double_cylinder_offset_ * heading;",
        "  Eigen::Vector3d rear = pos - mp_.double_cylinder_offset_ * heading;",
        "  if (reactiveOccupancy(front) != 0) return 1;",
        "  return reactiveOccupancy(rear);",
        "}", "",
    ]) + ending
    data = data[:start] + replacement + data[end:]
    grid_h.write_bytes(data)
    changed[str(grid_h.relative_to(root))] = sha(grid_h)

    grid_cpp = root / "plan_env/src/grid_map.cpp"
    data = grid_cpp.read_bytes()
    data = after_line(data, '  load_parameter(node_, "grid_map.cloud_is_world", mp_.cloud_is_world_, true);', [
        '  load_parameter(node_, "grid_map.reactive_tomogram_resolution", reactive_tomogram_resolution_m_, 0.1);',
        '  load_parameter(node_, "grid_map.reactive_tomogram_z_offset", reactive_tomogram_z_offset_m_, 0.03);',
        '  load_parameter(node_, "grid_map.reactive_terrain_band", reactive_terrain_band_m_, 0.05);',
        '  load_parameter(node_, "grid_map.reactive_cost_limit", reactive_cost_limit_, 20.0);',
        '  load_parameter(node_, "grid_map.reactive_track_max_age", reactive_parameters_.track_max_age_s, 0.25);',
        '  load_parameter(node_, "grid_map.reactive_cloud_max_age", reactive_parameters_.obstacle_max_age_s, 0.25);',
        '  load_parameter(node_, "grid_map.reactive_tomogram_max_age", reactive_parameters_.terrain_max_age_s, 86400.0);',
        '  load_parameter(node_, "grid_map.body_height", reactive_parameters_.body_clearance_m, 0.4);',
        '  reactive_parameters_.robot_radius_m = mp_.double_cylinder_radius_;',
        '  reactive_decision_ = reactive_stair::CollisionDecision(reactive_parameters_);',
    ])
    data = after_line(data, "  md_.occupancy_buffer_[addr] = new_log_odds;", [
        "  if (!now_occ) reactive_nonterrain_history_.erase(std::make_tuple(id.x(), id.y(), id.z()));",
    ])
    reset_start = data.index(b"void GridMap::resetAllMapData()")
    reset_end = data.index(b"void GridMap::hashIdToGlobalIndex", reset_start)
    reset = data[reset_start:reset_end]
    reset = replace_once(reset, b"void GridMap::resetAllMapData()\r\n{\r\n",
        b"void GridMap::resetAllMapData()\r\n{\r\n"
        b"  reactive_terrain_hits_.clear();\r\n"
        b"  reactive_nonterrain_hits_.clear();\r\n"
        b"  reactive_nonterrain_history_.clear();\r\n"
        b"  reactive_cloud_ready_ = false;\r\n"
        b"  reactive_pending_cloud_ = false;\r\n", "full map reset")
    data = data[:reset_start] + reset + data[reset_end:]
    for function_name, next_name in (
        (b"void GridMap::resetCellByAddress(int addr)", b"void GridMap::resetCellByAddressForSliding"),
        (b"void GridMap::resetCellByAddressForSliding", b"void GridMap::updateSlidingMap"),
    ):
        start = data.index(function_name)
        end = data.index(next_name, start + len(function_name))
        block = after_line(data[start:end], "  hashIdToGlobalIndex(addr, id_g);", [
            "  const auto key = std::make_tuple(id_g.x(), id_g.y(), id_g.z());",
            "  reactive_terrain_hits_.erase(key);",
            "  reactive_nonterrain_hits_.erase(key);",
            "  reactive_nonterrain_history_.erase(key);",
        ])
        data = data[:start] + block + data[end:]
    anchor = (b'  occ_timer_ = node_->create_wall_timer(std::chrono::milliseconds(50),')
    subscriptions = b'\n'.join(line.encode() for line in [
        '  reactive_tomogram_sub_ = node_->create_subscription<sensor_msgs::msg::PointCloud2>(',
        '      "/pct_tomogram", rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local(),',
        '      std::bind(&GridMap::reactiveTomogramCallback, this, std::placeholders::_1));',
        '  reactive_tracks_sub_ = node_->create_subscription<scan_planner_msgs::msg::TrackedPersonSnapshot>(',
        '      "/tracked_person_snapshot", rclcpp::SensorDataQoS(),',
        '      std::bind(&GridMap::reactiveTracksCallback, this, std::placeholders::_1));',
        '',
    ]) + b'\n'
    data = replace_once(data, anchor, subscriptions + anchor, "reactive subscriptions")

    cloud_start = data.index(b"void GridMap::cloudCallback(")
    cloud_end = data.index(b"void GridMap::publishMap()", cloud_start)
    cloud = data[cloud_start:cloud_end]
    cloud = replace_once(cloud, b'  if (mp_.sensor_type_ != "lidar")\r\n    return;\r\n',
        b'  if (mp_.sensor_type_ != "lidar")\r\n    return;\r\n'
        b'  reactive_cloud_ready_ = false;\r\n  reactive_pending_cloud_ = false;\r\n'
        b'  if (mp_.cloud_is_world_ && img->header.frame_id != mp_.frame_id_) return;\r\n'
        b'  reactive_cloud_stamp_s_ = rclcpp::Time(img->header.stamp).seconds();\r\n'
        b'  if (!std::isfinite(reactive_cloud_stamp_s_) || reactive_cloud_stamp_s_ <= 0.0) return;\r\n',
        "cloud preflight")
    cloud = replace_once(cloud, b'  md_.proj_points_cnt = 0;\r\n',
        b'  md_.proj_points_cnt = 0;\r\n  reactive_terrain_hits_.clear();\r\n'
        b'  reactive_nonterrain_hits_.clear();\r\n', "cloud classification reset")
    cloud = replace_once(cloud, b'    md_.proj_points_cnt++;\r\n',
        b'    md_.proj_points_cnt++;\r\n'
        b'    if (isInMap(pt_world)) {\r\n'
        b'      Eigen::Vector3i reactive_id;\r\n'
        b'      posToIndex(pt_world, reactive_id);\r\n'
        b'      const auto key = std::make_tuple(reactive_id.x(), reactive_id.y(), reactive_id.z());\r\n'
        b'      if (reactiveTerrainReturn(pt_world)) reactive_terrain_hits_.insert(key);\r\n'
        b'      else {\r\n'
        b'        reactive_nonterrain_hits_.insert(key);\r\n'
        b'        reactive_nonterrain_history_.insert(key);\r\n'
        b'      }\r\n'
        b'    }\r\n', "cloud endpoint classification")
    cloud = replace_once(cloud, b'  md_.use_cloud_update_ = true;\r\n  md_.occ_need_update_ = true;',
        b'  md_.use_cloud_update_ = true;\r\n  md_.occ_need_update_ = true;\r\n'
        b'  reactive_pending_cloud_ = true;', "cloud ready after occupancy update")
    data = data[:cloud_start] + cloud + data[cloud_end:]
    occ_start = data.index(b"void GridMap::updateOccupancyCallback()")
    occ_end = data.index(b"void GridMap::depthPoseCallback", occ_start)
    occ = after_line(data[occ_start:occ_end], "  md_.use_cloud_update_ = false;", [
        "  if (reactive_pending_cloud_) reactive_cloud_ready_ = true;",
        "  reactive_pending_cloud_ = false;",
    ])
    data = data[:occ_start] + occ + data[occ_end:]
    data += b'\n#include "plan_env/scan_reactive_grid_methods.inc"\n'
    grid_cpp.write_bytes(data)
    changed[str(grid_cpp.relative_to(root))] = sha(grid_cpp)

    cmake = root / "scan_planner_msgs/CMakeLists.txt"
    data = cmake.read_bytes()
    data = after_line(data, '  "msg/P2BStampedTwist.msg"', [
        '  "msg/TrackedPerson.msg"',
        '  "msg/TrackedPersonSnapshot.msg"',
    ])
    cmake.write_bytes(data)
    changed[str(cmake.relative_to(root))] = sha(cmake)

    cmake = root / "plan_env/CMakeLists.txt"
    data = cmake.read_bytes()
    data = after_line(data, "find_package(rclcpp REQUIRED)", ["find_package(scan_planner_msgs REQUIRED)"])
    data = replace_once(data, b'  sensor_msgs tf2 tf2_ros visualization_msgs\n',
                        b'  scan_planner_msgs sensor_msgs tf2 tf2_ros visualization_msgs\n',
                        "plan_env target dependency")
    data = replace_once(data, b'  rclcpp sensor_msgs tf2 tf2_ros visualization_msgs)',
                        b'  rclcpp scan_planner_msgs sensor_msgs tf2 tf2_ros visualization_msgs)',
                        "plan_env export dependency")
    cmake.write_bytes(data)
    changed[str(cmake.relative_to(root))] = sha(cmake)

    package = root / "plan_env/package.xml"
    data = package.read_bytes()
    data = after_line(data, "  <depend>rclcpp</depend>", ["  <depend>scan_planner_msgs</depend>"])
    package.write_bytes(data)
    changed[str(package.relative_to(root))] = sha(package)
    return changed


def materialize() -> dict:
    if OUTPUT.exists():
        raise Refused("scan_06 already exists")
    base = scan05_gate.source_hashes(SOURCE, P2B / "baseline_config/planner.yaml")
    sources = {
        "plan_env/include/plan_env/reactive_collision.h": HERE / "reactive_collision.h",
        "plan_env/include/plan_env/raw_return_classification.h": HERE / "raw_return_classification.h",
        "plan_env/include/plan_env/scan_reactive_grid_methods.inc": HERE / "scan_reactive_grid_methods.inc",
        "scan_planner_msgs/msg/TrackedPerson.msg": HERE / "TrackedPerson.msg",
        "scan_planner_msgs/msg/TrackedPersonSnapshot.msg": HERE / "TrackedPersonSnapshot.msg",
    }
    try:
        shutil.copytree(SOURCE / "src", OUTPUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        root = OUTPUT / "src"
        before = {str(path.relative_to(root)): sha(path) for path in root.rglob("*") if path.is_file()}
        if before != base:
            raise Refused("copied scan_04 source hash mismatch")
        changed = patch_sources(root)
        for relative, path in sources.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            changed[relative] = sha(target)
        manifest = {
            "schema": "scan_reactive_stair_candidate_v1",
            "status": "source_candidate_unbuilt",
            "base": "scan_04",
            "base_sha256": base,
            "source_manifest_sha256": sha(SOURCE / "source_sha256.json"),
            "pinned_planner_yaml_sha256": sha(P2B / "baseline_config/planner.yaml"),
            "changed_sha256": changed,
            "track_source": "external ROS topic /tracked_person_snapshot; no producer bundled",
            "terrain_source": "PCT /pct_tomogram selected ground cells; static content identity at receipt",
            "claim": "local source overlay only; Foxy build and runtime integration pending",
        }
        (OUTPUT / "reactive_stair_candidate_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        raise


if __name__ == "__main__":
    result = materialize()
    print(json.dumps({"status": result["status"], "changed_sha256": result["changed_sha256"]}, indent=2))

"""Derive refresh_probe.cpp from the stop-class audit's stop_probe.cpp.

The replay part of stop_probe.cpp (the unchanged v30 regression gen_probe
input replay: native subscriptions, frozen scans and poses, executing spline,
route and last committed window) is kept byte for byte up to its analysis
marker. The appended contract runs one case per process against the real FSM
callbacks, so the same source measures v30 (red) and v31 (green):

- C1: clock +0.30 s, body pose re-stamped, nothing pending; safety timer.
- C2: as C1, plus the run's own scans and poses of those 0.30 s pending
  (published, not spun); safety timer.
- C3: clock +0.15 s, body pose not re-stamped, the run's body poses pending;
  safety timer.
- C4: as C2; one planning-timer call in the state's FSM entry.
- C5spin: as C2, but the executor processes the pending inputs before the
  safety timer, which gives the map for the equivalence check.

Usage: python3 make_refresh_probe.py <stop-class audit dir> <output source dir>
"""
from pathlib import Path
import hashlib, json, shutil, sys

audit, out = Path(sys.argv[1]), Path(sys.argv[2])
source = audit / "probe_source"
stop_probe = (source / "src/stop_probe.cpp").read_text()
marker = "  // ===== v30 stop-class analysis (read-only; replaces gen_probe's frontier audit) =====\n"
assert stop_probe.count(marker) == 1
replay = stop_probe[:stop_probe.index(marker)]

CONTRACT = r'''  // ===== v31 input-refresh contract (one case per process) =====
  std::cout << std::setprecision(12);
  const int64_t frozen_ns = now;
  const std::string contract_case = std::getenv("VLA_REFRESH_CASE") ? std::getenv("VLA_REFRESH_CASE") : "";
  const std::string entry_name = std::getenv("VLA_ENTRY_STATE") ? std::getenv("VLA_ENTRY_STATE") : "";
  if (contract_case != "C1" && contract_case != "C2" && contract_case != "C3" && contract_case != "C4" &&
      contract_case != "C5spin") throw std::runtime_error("Unknown contract case");
  if (entry_name != "GEN_NEW_TRAJ" && entry_name != "REPLAN_TRAJ") throw std::runtime_error("Unknown entry state");
  const auto entry = entry_name == "GEN_NEW_TRAJ" ? scan_planner::SCANReplanFSM::GEN_NEW_TRAJ
                                                  : scan_planner::SCANReplanFSM::REPLAN_TRAJ;
  const auto executing = fsm.planner_manager_->local_data_;
  const double delta = contract_case == "C3" ? 0.15 : 0.30;
  const int64_t check_ns = frozen_ns + static_cast<int64_t>(std::llround(delta * 1e9));
  clock(check_ns);
  if (contract_case != "C3") {
    body.header.stamp = rclcpp::Time(check_ns);
    body_pub->publish(body);
    spin(50);
  }
  int published_scans = 0, published_bodies = 0;
  if (contract_case != "C1") {
    const char *pending_env = std::getenv("VLA_PENDING_INPUT");
    if (!pending_env) throw std::runtime_error("Missing pending input");
    const fs::path pending(pending_env);
    std::vector<std::tuple<int64_t, int, std::string, std::string>> events;
    int64_t stamp = 0;
    std::string first, second;
    std::ifstream scans_list(pending / "scans.txt");
    while (scans_list >> stamp >> first >> second) events.emplace_back(stamp, 0, first, second);
    std::ifstream bodies_list(pending / "bodies.txt");
    while (bodies_list >> stamp >> first) events.emplace_back(stamp, 1, first, "");
    std::sort(events.begin(), events.end());
    if (events.empty()) throw std::runtime_error("No pending input");
    for (const auto &[event_ns, kind, file, sensor_file] : events) {
      if (event_ns <= frozen_ns || event_ns > check_ns) throw std::runtime_error("Pending input outside the interval");
      if (kind == 0) {
        auto sensor_pose = read_pose(pending / sensor_file);
        sensor_pose.child_frame_id = "lidar";
        sensor_pose.header.stamp = rclcpp::Time(event_ns);
        pose_pub->publish(sensor_pose);
        auto cloud = read_cloud(pending / file, false);
        cloud.header.stamp = rclcpp::Time(event_ns);
        cloud_pub->publish(cloud);
        ++published_scans;
      } else {
        auto pending_body = read_pose(pending / file);
        pending_body.child_frame_id = "base";
        pending_body.header.stamp = rclcpp::Time(event_ns);
        body_pub->publish(pending_body);
        ++published_bodies;
      }
    }
    // Delivery without spinning: the messages wait as during a long callback.
    std::this_thread::sleep_for(std::chrono::milliseconds(300));
  }
  if (contract_case == "C5spin") spin(500);
  const double now_before = node->now().seconds();
  const double cloud_stamp_before = map->reactive_cloud_stamp_s_;
  const double body_stamp_before = map->reactive_body_stamp_s_;
  fsm.planner_manager_->local_data_ = executing;
  fsm.changeFSMExecState(entry, "CONTRACT");
  std::cout << "[CONTRACT-CALL-BEGIN] case=" << contract_case << " entry=" << entry_name << std::endl;
  const auto wall_start = std::chrono::steady_clock::now();
  if (contract_case == "C4") fsm.execFSMCallback();
  else fsm.checkCollisionCallback();
  const double call_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - wall_start).count();
  std::cout << "[CONTRACT-CALL-END] exec_state=" << static_cast<int>(fsm.exec_state_) << std::endl;
  const double now_after = node->now().seconds();
  auto traj = executing.position_traj_;
  const double raw_t = (node->now() - executing.start_time_).seconds();
  const auto safety = reactive_stair::checkFullCubicTrajectory(
      traj, raw_t, map->getResolution(), GridMap::collision_heading_lookahead_s,
      [&map](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
        return map->collisionTrajectoryYaw(p, ahead, v);
      },
      [&map](const Eigen::Vector3d &p, double yaw) { return map->getInflateOccupancy(p, yaw) != 0; });
  // FNV-1a over the state that pose and scan processing writes.
  uint64_t digest = 1469598103934665603ULL;
  const auto mix = [&digest](const void *data, size_t size) {
    const auto *bytes = static_cast<const unsigned char *>(data);
    for (size_t i = 0; i < size; ++i) { digest ^= bytes[i]; digest *= 1099511628211ULL; }
  };
  const auto &md = map->md_;
  const auto &mp = map->mp_;
  mix(md.occupancy_buffer_.data(), md.occupancy_buffer_.size() * sizeof(double));
  mix(md.occupancy_buffer_inflate_.data(), md.occupancy_buffer_inflate_.size());
  mix(md.occupancy_buffer_inflate_cnt_.data(), md.occupancy_buffer_inflate_cnt_.size() * sizeof(int));
  for (const auto *keys : {&map->reactive_terrain_hits_, &map->reactive_nonterrain_hits_,
                           &map->reactive_nonterrain_history_}) {
    const size_t count = keys->size();
    mix(&count, sizeof(count));
    for (const auto &key : *keys) {
      const int values[3] = {std::get<0>(key), std::get<1>(key), std::get<2>(key)};
      mix(values, sizeof(values));
    }
  }
  const double scalars[] = {map->reactive_cloud_stamp_s_, map->reactive_body_stamp_s_,
                            md.ray_pos_.x(), md.ray_pos_.y(), md.ray_pos_.z(),
                            md.ray_q_.w(), md.ray_q_.x(), md.ray_q_.y(), md.ray_q_.z(),
                            md.sliding_map_frame_pos_.x(), md.sliding_map_frame_pos_.y(), md.sliding_map_frame_pos_.z(),
                            map->reactive_body_quaternion_.w(), map->reactive_body_quaternion_.x(),
                            map->reactive_body_quaternion_.y(), map->reactive_body_quaternion_.z(),
                            mp.map_origin_.x(), mp.map_origin_.y(), mp.map_origin_.z()};
  mix(scalars, sizeof(scalars));
  const int indices[] = {mp.map_origin_idx_.x(), mp.map_origin_idx_.y(), mp.map_origin_idx_.z(),
                         md.local_bound_min_.x(), md.local_bound_min_.y(), md.local_bound_min_.z(),
                         md.local_bound_max_.x(), md.local_bound_max_.y(), md.local_bound_max_.z(),
                         static_cast<int>(map->reactive_cloud_ready_), static_cast<int>(md.has_cloud_),
                         static_cast<int>(md.has_ray_pose_)};
  mix(indices, sizeof(indices));
  std::ostringstream digest_hex;
  digest_hex << std::hex << std::setw(16) << std::setfill('0') << digest;
  const char *status_names[] = {"Clear", "Collision", "InvalidCurve"};
  const int status = static_cast<int>(safety.status);
  std::ofstream result(output);
  result << std::setprecision(12);
  result << "{\"case\":\"" << contract_case << "\",\"entry\":\"" << entry_name << "\",\"frozen_ns\":" << frozen_ns
         << ",\"check_ns\":" << check_ns << ",\"published_scans\":" << published_scans
         << ",\"published_bodies\":" << published_bodies << ",\"now_before_s\":" << now_before
         << ",\"cloud_age_before_s\":" << now_before - cloud_stamp_before
         << ",\"body_age_before_s\":" << now_before - body_stamp_before << ",\"now_after_s\":" << now_after
         << ",\"cloud_stamp_after_s\":" << map->reactive_cloud_stamp_s_
         << ",\"cloud_age_after_s\":" << now_after - map->reactive_cloud_stamp_s_
         << ",\"body_age_after_s\":" << now_after - map->reactive_body_stamp_s_
         << ",\"exec_state_after\":" << static_cast<int>(fsm.exec_state_) << ",\"call_wall_ms\":" << call_ms
         << ",\"recheck\":{\"status\":\"" << (status >= 0 && status < 3 ? status_names[status] : "Other")
         << "\",\"first_time_s\":" << safety.first_time_s << ",\"samples\":" << safety.samples
         << ",\"raw_t\":" << raw_t << "},\"map_digest\":\"" << digest_hex.str() << "\"}\n";
  result.close();
  std::cout << "[CONTRACT] done case=" << contract_case << " exec_state=" << static_cast<int>(fsm.exec_state_)
            << " recheck=" << status << " digest=" << digest_hex.str() << std::endl;
  rclcpp::shutdown();
}
'''
source_out = out / "src"
source_out.mkdir(parents=True, exist_ok=False)
(source_out / "refresh_probe.cpp").write_text(replay + CONTRACT)
shutil.copyfile(source / "package.xml", out / "package.xml")
cmake = (source / "CMakeLists.txt").read_text()
assert cmake.count("foreach(target stop_probe)") == 1
(out / "CMakeLists.txt").write_text(cmake.replace("foreach(target stop_probe)", "foreach(target refresh_probe)"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(out.parent / "refresh_probe_derivation.json").write_text(json.dumps({
    "base": {str(p.relative_to(audit.parent.parent)): sha(p) for p in
             [source / "src/stop_probe.cpp", source / "CMakeLists.txt", source / "package.xml"]},
    "kept": "stop_probe.cpp up to its analysis marker, byte for byte (the unchanged v30 gen_probe replay)",
    "output": {str(p.relative_to(out.parent)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}},
    indent=2) + "\n")
print("refresh_probe source written")

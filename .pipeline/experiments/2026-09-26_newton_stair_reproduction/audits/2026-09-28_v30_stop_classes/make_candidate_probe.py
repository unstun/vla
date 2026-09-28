"""Derive candidate_probe.cpp: break down the planner's rejected candidate curves.

Same unchanged gen_probe input replay as stop_probe (through the
last_progress load). The clock is not advanced, so the inputs are exactly the
fresh (delta 0) inputs of stop_probe. For every candidate in
$VLA_STOP_CANDIDATES (controls and knots copied from the replan's own
spline_curve_capture "minimum_cruise_checked" line), the probe
1. rebuilds the uniform cubic B-spline with the logged knots,
2. runs the native full check from t = 0 and records status, first time and
   samples (checked against the logged final_spline_rejected line), and
3. at the first colliding sample repeats both footprint circles step by step
   (the stop_probe breakdown), cross-checked against the native functions,
   listing every unclassified contributor.
No native source, threshold or map state is changed.
"""
from pathlib import Path
import hashlib, json, re

here = Path(__file__).resolve().parent
stop = (here / "probe_source/src/stop_probe.cpp").read_text()
begin = "  // ===== v30 stop-class analysis (read-only; replaces gen_probe's frontier audit) =====\n"
helpers_end = "  auto &gd = fsm.planner_manager_->global_data_;\n"
assert stop.count(begin) == 1 and stop.count(helpers_end) == 1
prefix = stop[:stop.index(begin)]
helpers = stop[stop.index(begin):stop.index(helpers_end)]
block = r'''  // ===== candidate breakdown (read-only) =====
  std::ifstream list(std::getenv("VLA_STOP_CANDIDATES"));
  std::vector<std::vector<double>> rows;
  {
    // Plain text: one candidate per line: id n_controls x y z ... n_knots k0 k1 ...
    std::string line;
    while (std::getline(list, line)) {
      std::istringstream s(line); std::vector<double> v; double x;
      while (s >> x) v.push_back(x);
      if (!v.empty()) rows.push_back(v);
    }
  }
  std::ostringstream items; items << std::setprecision(12);
  for (size_t k = 0; k < rows.size(); ++k) {
    const auto &v = rows[k];
    const int id = static_cast<int>(v[0]);
    const int n = static_cast<int>(v[1]);
    Eigen::MatrixXd points(3, n);
    for (int i = 0; i < n; ++i) points.col(i) << v[2 + 3 * i], v[3 + 3 * i], v[4 + 3 * i];
    const int m = static_cast<int>(v[2 + 3 * n]);
    Eigen::VectorXd knots(m);
    for (int i = 0; i < m; ++i) knots[i] = v[3 + 3 * n + i];
    scan_planner::UniformBspline curve(points, 3, knots[4] - knots[3]);
    curve.setKnot(knots);
    auto checked = curve;
    const auto check = reactive_stair::checkFullCubicTrajectory(checked, 0.0, map->getResolution(),
        GridMap::collision_heading_lookahead_s, heading_fn, occupied_fn);
    items << (k ? "," : "") << "{\"id\":" << id << ",\"check\":" << status_json(check);
    if (check.status == reactive_stair::TrajectoryCheckStatus::Collision) {
      auto velocity = curve.getDerivative();
      const double t = check.first_time_s;
      const double duration = check.duration_s;
      const Eigen::Vector3d p = curve.evaluateDeBoorT(t);
      const Eigen::Vector3d ahead = curve.evaluateDeBoorT(std::min(t + GridMap::collision_heading_lookahead_s, duration));
      const Eigen::Vector3d vel = velocity.evaluateDeBoorT(t);
      const double yaw = map->collisionTrajectoryYaw(p, ahead, vel);
      const Eigen::Vector3d heading(std::cos(yaw), std::sin(yaw), 0.0);
      items << ",\"sample\":" << vec(p) << ",\"yaw\":" << yaw << ",\"native\":" << map->getInflateOccupancy(p, yaw) << ",\"circles\":[";
      for (int side = 0; side < 2; ++side) {
        const Eigen::Vector3d c = p + (side == 0 ? 1.0 : -1.0) * map->mp_.double_cylinder_offset_ * heading;
        const Circle b = circle_breakdown(c, p);
        items << (side ? "," : "") << "{\"side\":\"" << (side == 0 ? "front" : "rear") << "\",\"circle\":" << circle_json(b) << "}";
      }
      items << "]";
    }
    items << "}";
  }
  std::ofstream result(output); result << std::setprecision(12);
  result << "{\"now_s\":" << node->now().seconds() << ",\"body\":" << vec(map->md_.sliding_map_frame_pos_)
         << ",\"body_stamp_s\":" << map->reactive_body_stamp_s_ << ",\"cloud_stamp_s\":" << map->reactive_cloud_stamp_s_
         << ",\"candidates\":[" << items.str() << "]}\n";
  result.close();
  std::cout << "[CANDIDATE-ANALYSIS] done candidates=" << rows.size() << std::endl;
  rclcpp::shutdown();
}
'''
derived = prefix + helpers + block
out = here / "candidate_probe_source"
(out / "src").mkdir(parents=True, exist_ok=True)
(out / "src/candidate_probe.cpp").write_text(derived)
src = here / "probe_source"
(out / "package.xml").write_bytes((src / "package.xml").read_bytes())
cmake = (src / "CMakeLists.txt").read_text()
assert cmake.count("foreach(target stop_probe)") == 1
(out / "CMakeLists.txt").write_text(cmake.replace("foreach(target stop_probe)", "foreach(target candidate_probe)"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(here / "candidate_probe_derivation.json").write_text(json.dumps({
    "base": {str(p.relative_to(here)): sha(p) for p in [src / "src/stop_probe.cpp", src / "CMakeLists.txt"]},
    "derived": {str(p.relative_to(here)): sha(p) for p in [out / "src/candidate_probe.cpp", out / "CMakeLists.txt", out / "package.xml"]},
    "change": "Keeps stop_probe's unchanged gen_probe input replay and its read-only helpers; replaces the sweep with a candidate breakdown at the fresh inputs. Native sources unchanged.",
}, indent=2) + "\n")

# Candidate lists from each state's delta-0 replan (fresh inputs, same map as the probe).
for state in ["stairs_replan", "stairs_hold", "corridor_entry_replan", "upper_corridor_hold"]:
    log = (here / state / "probe.log")
    if not log.exists():
        continue
    lines = log.read_text(errors="replace").splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("[STOP-REPLAN-BEGIN] delta=0 "))
        end = next(i for i, l in enumerate(lines) if l.startswith("[STOP-REPLAN-END] delta=0 "))
    except StopIteration:
        continue
    candidates, capture, index = [], None, 0
    for l in lines[start:end]:
        if '"stage":"minimum_cruise_checked"' in l:
            capture = json.loads(l.split("spline_curve_capture ", 1)[1])
        m = re.search(r"final_spline_rejected status=(\d+) t=([0-9.]+) duration=([0-9.]+)", l)
        c = re.search(r"full_spline_sampled_clear duration=([0-9.]+)", l)
        if (m or c) and capture is not None:
            index += 1
            candidates.append({"id": index, "logged_status": int(m.group(1)) if m else 0,
                               "logged_t": float(m.group(2)) if m else None,
                               "logged_duration": float(m.group(3)) if m else float(c.group(1)),
                               "controls": capture["controls"], "knots": capture["knots"]})
            capture = None
    (here / state / "candidates.json").write_text(json.dumps(candidates, indent=2) + "\n")
    with (here / state / "candidates.txt").open("w") as f:
        for c in candidates:
            flat = [c["id"], len(c["controls"])] + [x for p in c["controls"] for x in p] + [len(c["knots"])] + c["knots"]
            f.write(" ".join(format(float(x), ".17g") for x in flat) + "\n")
    print(state, "candidates", len(candidates), [(c["logged_status"], c["logged_t"]) for c in candidates])
print("ok")

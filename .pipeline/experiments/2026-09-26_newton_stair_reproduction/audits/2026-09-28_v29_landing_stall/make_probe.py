"""Derive landing_probe.cpp from the unchanged v29 regression gen_probe.cpp.

The only change is a read-only breakdown block inserted before the stale-clock
negative check. It re-walks the reference frontier exactly as
SCANReplanFSM::adjustGlobalTargetIfOccupied does (from the route end backwards,
0.05 s grid, prev->pt yaw). For each footprint circle of the samples near the
frontier it repeats GridMap::reactiveOccupancy and reactiveFootprintSupportQuery
step by step with the same members (-fno-access-control), and cross-checks the
repeated result against the native functions for every circle and sample.
No native source, threshold or map state is changed.
"""
from pathlib import Path
import hashlib, json

here = Path(__file__).resolve().parent
source = here.parents[1] / "runs/v29_native_regression01/probe_source"
text = (source / "src/gen_probe.cpp").read_text()

include_anchor = "#include <plan_env/grid_map.h>\n"
includes = include_anchor + "#include <plan_env/known_lite3_trunk.h>\n#include <plan_env/raw_return_classification.h>\n#include <plan_env/eth_step_score_adaptation.h>\n#include <cmath>\n"
block_anchor = '  std::ofstream negatives(fs::path(output).parent_path()/(fs::path(output).stem().string()+"_negatives.json"));\n'
block = r'''  // ---- Landing-stall breakdown (read-only, before the stale-clock negative) ----
  {
    struct Breakdown {
      std::string stage = "free"; int in_map = 0; double log_odds = NAN; int inflate = -1;
      int contributors = 0, unclassified = 0; Eigen::Vector3d first_unclassified = Eigen::Vector3d::Constant(NAN);
      std::string first_flags = "-"; int raw_class = -1, trunk_inside = -1, final_class = -1, body_verdict = -1;
      double body_ground = NAN, footprint_ground = NAN, support_z = NAN; int verdict = -1, result = 1;
    };
    const double now_s = node->now().seconds();
    const auto support_replica = [&](const Eigen::Vector3d &body_reference, const reactive_stair::NonTerrainVoxel &obstacle,
                                     reactive_stair::Query &query, Breakdown &b) {
      if (!body_reference.allFinite()) { b.stage = "support_body_nonfinite"; return false; }
      const auto &raw = map->reactive_ground_;
      const auto &scored = map->reactive_terrain_;
      if (raw.source_id != scored.source_id || raw.frame != scored.frame || raw.resolution_m != scored.resolution_m ||
          raw.origin_x_m != scored.origin_x_m || raw.origin_y_m != scored.origin_y_m) { b.stage = "support_source_mismatch"; return false; }
      auto body_query = query;
      body_query.x_m = body_reference.x(); body_query.y_m = body_reference.y(); body_query.z_m = body_reference.z();
      body_query.in_map = map->isInMap(body_reference);
      auto support_only = obstacle;
      support_only.occupancy = reactive_stair::Occupancy::Free;
      const auto body_verdict = map->reactive_decision_.decide(body_query, support_only);
      b.body_verdict = static_cast<int>(body_verdict);
      if (body_verdict != reactive_stair::Verdict::Free) { b.stage = "support_body_verdict"; return false; }
      // Codes: 1 invalid index, 2 missing cell, 3 layer count mismatch, 4 no unique
      // layer within the limit, 5 elevation mismatch, 6 nearest layer not selected.
      const auto associated_height = [&](double x, double y, double target, double limit, double &height) {
        const double ix = std::floor((x - raw.origin_x_m) / raw.resolution_m);
        const double iy = std::floor((y - raw.origin_y_m) / raw.resolution_m);
        if (!std::isfinite(ix) || !std::isfinite(iy) ||
            ix < std::numeric_limits<int>::min() || ix > std::numeric_limits<int>::max() ||
            iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) return 1;
        const reactive_stair::Cell2 cell{static_cast<int>(ix), static_cast<int>(iy)};
        const auto original = raw.cells.find(cell), classified = scored.cells.find(cell);
        if (original == raw.cells.end() || classified == scored.cells.end()) return 2;
        if (original->second.size() != classified->second.size()) return 3;
        const int layer = reactive_stair::nearestSurface(original->second, target, limit);
        if (layer < 0) return 4;
        const auto &surface = classified->second[layer];
        if (surface.elevation_m != original->second[layer].elevation_m) return 5;
        if (!reactive_stair::selectedSurface(surface)) return 6;
        height = surface.elevation_m;
        return 0;
      };
      const double step = reactive_stair::StepScoreParameters{}.critical_height_m;
      int code = associated_height(body_query.x_m, body_query.y_m, body_query.z_m - map->reactive_parameters_.body_clearance_m,
                                   map->reactive_parameters_.body_height_tolerance_m, b.body_ground);
      if (code) { b.stage = "support_body_layer_" + std::to_string(code); return false; }
      code = associated_height(query.x_m, query.y_m, b.body_ground, step, b.footprint_ground);
      if (code) { b.stage = "support_footprint_layer_" + std::to_string(code); return false; }
      if (std::abs(b.footprint_ground - b.body_ground) >= step) { b.stage = "support_step"; return false; }
      query.z_m = b.footprint_ground + map->reactive_parameters_.body_clearance_m;
      b.support_z = query.z_m;
      return true;
    };
    const auto breakdown = [&](const Eigen::Vector3d &point, const Eigen::Vector3d &body) {
      Breakdown b;
      if (!map->reactiveSurfaceGroundReady()) { b.stage = "surface_not_ready"; return b; }
      if (!point.allFinite()) { b.stage = "nonfinite"; return b; }
      const double radius = map->mp_.double_cylinder_radius_;
      if (!std::isfinite(radius) || radius < 0.0 ||
          point.x() - radius < map->mp_.map_min_boundary_.x() || point.x() + radius > map->mp_.map_max_boundary_.x() ||
          point.y() - radius < map->mp_.map_min_boundary_.y() || point.y() + radius > map->mp_.map_max_boundary_.y() ||
          point.z() - map->mp_.obstacles_inflation_z_down < map->mp_.map_min_boundary_.z() ||
          point.z() + map->mp_.obstacles_inflation_z_up > map->mp_.map_max_boundary_.z()) { b.stage = "map_boundary"; return b; }
      reactive_stair::Query query;
      query.frame = map->mp_.frame_id_; query.stamp_s = now_s;
      query.x_m = point.x(); query.y_m = point.y(); query.z_m = point.z();
      query.in_map = map->isInMap(point); b.in_map = query.in_map;
      reactive_stair::NonTerrainVoxel obstacle;
      obstacle.frame = map->mp_.frame_id_; obstacle.stamp_s = map->reactive_cloud_stamp_s_;
      if (map->reactive_cloud_ready_) obstacle.source_id = "scan_lidar_cloud";
      if (query.in_map) {
        Eigen::Vector3i qid; map->posToIndex(point, qid);
        const int address = map->toAddress(qid);
        b.log_odds = map->md_.occupancy_buffer_[address];
        b.inflate = map->md_.occupancy_buffer_inflate_[address];
        if (map->md_.occupancy_buffer_[address] < map->mp_.clamp_min_log_ - 1e-3) {
          obstacle.occupancy = reactive_stair::Occupancy::Unknown;
        } else if (map->md_.occupancy_buffer_inflate_[address] == 0) {
          obstacle.occupancy = reactive_stair::Occupancy::Free;
        } else {
          for (const auto &offset : map->md_.inflate_offsets_) {
            const Eigen::Vector3i source = qid - offset;
            if (!map->isInMap(source) || map->md_.occupancy_buffer_[map->toAddress(source)] <= map->mp_.min_occupancy_log_) continue;
            ++b.contributors;
            const auto key = std::make_tuple(source.x(), source.y(), source.z());
            const bool tr = map->reactive_terrain_hits_.count(key) != 0, nt = map->reactive_nonterrain_hits_.count(key) != 0,
                       hi = map->reactive_nonterrain_history_.count(key) != 0;
            if (!reactive_stair::mayWaiveRawContributor(tr, nt, hi)) {
              if (!b.unclassified) { map->indexToPos(source, b.first_unclassified); b.first_flags = std::to_string(tr) + std::to_string(nt) + std::to_string(hi); }
              ++b.unclassified;
            }
          }
          obstacle.occupancy = !b.contributors ? reactive_stair::Occupancy::Unknown :
              (b.unclassified ? reactive_stair::Occupancy::Occupied : reactive_stair::Occupancy::Free);
        }
      }
      b.raw_class = static_cast<int>(obstacle.occupancy);
      if (map->reactive_known_trunk_enabled_ && query.in_map && map->reactive_body_stamp_s_ > 0.0) {
        Eigen::Vector3i id; map->posToIndex(point, id);
        const Eigen::Vector3d local = map->reactive_body_quaternion_.conjugate() * (point - map->md_.sliding_map_frame_pos_);
        const bool inside = reactive_stair::knownNavigationFootprintInterior(local.x(), local.y(), local.z(), query.stamp_s,
            map->reactive_body_stamp_s_, map->mp_.double_cylinder_radius_, map->mp_.double_cylinder_offset_);
        b.trunk_inside = inside;
        obstacle.occupancy = reactive_stair::measuredTrunkQuery(obstacle.occupancy, map->md_.occupancy_buffer_inflate_[map->toAddress(id)] != 0, inside);
      }
      b.final_class = static_cast<int>(obstacle.occupancy);
      if (!support_replica(body, obstacle, query, b)) return b;
      const auto verdict = map->reactive_decision_.decide(query, obstacle);
      b.verdict = static_cast<int>(verdict);
      b.result = verdict == reactive_stair::Verdict::Free ? 0 : 1;
      b.stage = b.result ? "verdict_" + std::to_string(b.verdict) : "free";
      return b;
    };
    auto &gd = fsm.planner_manager_->global_data_;
    const double duration = gd.global_duration_;
    const int sample_num = std::max(1, static_cast<int>(std::ceil(duration / 0.05)));
    std::ofstream diag(fs::path(output).parent_path() / (fs::path(output).stem().string() + "_breakdown.csv"));
    diag << std::setprecision(12)
         << "i,t,x,y,z,yaw,native,circle,cx,cy,cz,local_x,local_y,local_z,sensor_range,sensor_elev_deg,stage,in_map,log_odds,inflate,contributors,unclassified,first_unclassified_x,first_unclassified_y,first_unclassified_z,first_flags,first_on_ground,raw_class,trunk_inside,final_class,body_verdict,body_ground,footprint_ground,support_z,verdict,replicated,native_circle,support_native\n";
    std::ofstream walk(fs::path(output).parent_path() / (fs::path(output).stem().string() + "_walk.csv"));
    walk << std::setprecision(12) << "i,t,x,y,z,yaw,native\n";
    int circle_mismatches = 0, sample_mismatches = 0, support_mismatches = 0, rows = 0, first_free = -1;
    for (int i = sample_num; i >= 0; --i) {
      const double t = duration * i / sample_num;
      const double prev_t = duration * std::max(0, i - 1) / sample_num;
      const Eigen::Vector3d pt = gd.global_traj_.evaluate(t), prev = gd.global_traj_.evaluate(prev_t);
      const double yaw = fsm.estimateYawFromSegment(prev, pt);
      const int native = map->getInflateOccupancy(pt, yaw);
      walk << i << "," << t << "," << pt.x() << "," << pt.y() << "," << pt.z() << "," << yaw << "," << native << "\n";
      if (native == 0 && first_free < 0) first_free = i;
      if (t < frontier - 0.35 || t > frontier + 4.5) continue;
      const Eigen::Vector3d heading(std::cos(yaw), std::sin(yaw), 0.0);
      int circle_native[2];
      for (int side = 0; side < 2; ++side) {
        const Eigen::Vector3d c = pt + (side == 0 ? 1.0 : -1.0) * map->mp_.double_cylinder_offset_ * heading;
        const Breakdown b = breakdown(c, pt);
        circle_native[side] = map->reactiveOccupancy(c, &pt);
        reactive_stair::Query probe_query;
        probe_query.frame = map->mp_.frame_id_; probe_query.stamp_s = now_s;
        probe_query.x_m = c.x(); probe_query.y_m = c.y(); probe_query.z_m = c.z(); probe_query.in_map = map->isInMap(c);
        reactive_stair::NonTerrainVoxel probe_obstacle; probe_obstacle.frame = map->mp_.frame_id_;
        probe_obstacle.stamp_s = map->reactive_cloud_stamp_s_;
        if (map->reactive_cloud_ready_) probe_obstacle.source_id = "scan_lidar_cloud";
        const bool support_native = map->reactiveFootprintSupportQuery(pt, probe_obstacle, probe_query);
        const bool support_replicated = b.stage.rfind("support_", 0) != 0 && b.stage != "map_boundary" &&
                                        b.stage != "surface_not_ready" && b.stage != "nonfinite";
        if (b.stage != "map_boundary" && support_native != support_replicated) ++support_mismatches;
        if (circle_native[side] != b.result) ++circle_mismatches;
        const Eigen::Vector3d local = map->reactive_body_quaternion_.conjugate() * (c - map->md_.sliding_map_frame_pos_);
        const Eigen::Vector3d ray = c - map->md_.ray_pos_;
        const double elevation = std::atan2(ray.z(), ray.head<2>().norm()) * 180.0 / 3.14159265358979323846;
        const bool on_ground = b.first_unclassified.allFinite() && map->reactiveTerrainReturn(b.first_unclassified);
        diag << i << "," << t << "," << pt.x() << "," << pt.y() << "," << pt.z() << "," << yaw << "," << native << ","
             << (side == 0 ? "front" : "rear") << "," << c.x() << "," << c.y() << "," << c.z() << ","
             << local.x() << "," << local.y() << "," << local.z() << "," << ray.norm() << "," << elevation << ","
             << b.stage << "," << b.in_map << "," << b.log_odds << "," << b.inflate << "," << b.contributors << "," << b.unclassified << ","
             << b.first_unclassified.x() << "," << b.first_unclassified.y() << "," << b.first_unclassified.z() << "," << b.first_flags << ","
             << on_ground << "," << b.raw_class << "," << b.trunk_inside << "," << b.final_class << "," << b.body_verdict << ","
             << b.body_ground << "," << b.footprint_ground << "," << b.support_z << "," << b.verdict << "," << b.result << ","
             << circle_native[side] << "," << support_native << "\n";
        ++rows;
      }
      if (native != (circle_native[0] ? 1 : circle_native[1])) ++sample_mismatches;
    }
    walk.close();
    diag.close();
    std::cout << "[LANDING-BREAKDOWN] frontier=" << frontier << " duration=" << duration << " sample_num=" << sample_num
              << " first_free_from_end_i=" << first_free << " t=" << duration * first_free / sample_num << " rows=" << rows
              << " circle_mismatches=" << circle_mismatches << " sample_mismatches=" << sample_mismatches
              << " support_mismatches=" << support_mismatches << " body=" << map->md_.sliding_map_frame_pos_.transpose()
              << " sensor=" << map->md_.ray_pos_.transpose() << " map_min=" << map->mp_.map_min_boundary_.transpose()
              << " map_max=" << map->mp_.map_max_boundary_.transpose() << " now=" << now_s
              << " cloud_stamp=" << map->reactive_cloud_stamp_s_ << " body_stamp=" << map->reactive_body_stamp_s_ << std::endl;
  }
'''
assert text.count(include_anchor) == 1 and text.count(block_anchor) == 1
derived = text.replace(include_anchor, includes).replace(block_anchor, block + block_anchor)
out = here / "probe_source"
(out / "src").mkdir(parents=True, exist_ok=True)
(out / "src/landing_probe.cpp").write_text(derived)
(out / "package.xml").write_bytes((source / "package.xml").read_bytes())
cmake = (source / "CMakeLists.txt").read_text()
old_targets = "foreach(target gen_probe legacy_probe measured_cloud_probe ground_contract body_support_contract)"
assert cmake.count(old_targets) == 1
(out / "CMakeLists.txt").write_text(cmake.replace(old_targets, "foreach(target landing_probe)"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(here / "probe_derivation.json").write_text(json.dumps({
    "base": {str(p.relative_to(here.parents[1])): sha(p) for p in [source / "src/gen_probe.cpp", source / "CMakeLists.txt", source / "package.xml"]},
    "derived": {str(p.relative_to(here)): sha(p) for p in [out / "src/landing_probe.cpp", out / "CMakeLists.txt", out / "package.xml"]},
    "change": "Adds read-only includes and the landing-stall breakdown block before the stale-clock negative; CMake builds only landing_probe. Native sources unchanged.",
}, indent=2) + "\n")
print("ok", len(derived) - len(text), "bytes added")

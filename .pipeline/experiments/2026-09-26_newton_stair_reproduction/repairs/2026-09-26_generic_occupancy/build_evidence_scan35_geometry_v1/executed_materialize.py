"""Create a hash-gated geometry-only candidate without editing SCAN33."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ORIGINAL = BASE / "builds/scan33_humble_amd64_v1"
WORKSPACE = BASE / "runtime/scan34_geometry_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path, old, new):
    data = path.read_bytes()
    if data.count(old.encode()) != 1:
        raise ValueError(f"Expected exactly one patch anchor in {path}: {old[:80]}")
    path.write_bytes(data.replace(old.encode(), new.encode()))


def remove_between(path, start, end):
    data = path.read_bytes()
    left, right = data.index(start.encode()), data.index(end.encode())
    if right <= left:
        raise ValueError("Invalid removal interval")
    path.write_bytes(data[:left] + data[right:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("geometry", "terrain_cache"), default="geometry")
    args = parser.parse_args()
    global WORKSPACE
    if args.variant == "terrain_cache":
        WORKSPACE = BASE / "runtime/scan35_geometry_v1"
    original = json.loads((ORIGINAL / "source_sha256.json").read_text())
    actual = {name: sha(ORIGINAL / name) for name in original}
    if actual != original:
        raise ValueError("SCAN33 baseline source mismatch")
    if WORKSPACE.exists():
        raise FileExistsError(WORKSPACE)
    shutil.copytree(ORIGINAL / "src", WORKSPACE / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    header = WORKSPACE / "src/plan_env/include/plan_env/reactive_collision.h"
    remove_between(header, "struct Track {", "struct Query {")
    remove_between(header, "inline bool valid(const TrackSnapshot", "class CollisionDecision {")
    remove_between(header, "  bool acceptTracks(", "  Verdict decide(")
    replace_once(header, "  double track_max_age_s = 0.25;\n", "")
    replace_once(header, "!terrain_ready_ || !tracks_ready_ || obstacle.source_id.empty()", "!terrain_ready_ || obstacle.source_id.empty()")
    replace_once(header, "query.frame != terrain_.frame || query.frame != tracks_.frame || query.frame != obstacle.frame", "query.frame != terrain_.frame || query.frame != obstacle.frame")
    replace_once(header, "if (!fresh(query.stamp_s, tracks_.stamp_s, p_.track_max_age_s) ||\n        !fresh(query.stamp_s, terrain_.stamp_s", "if (!fresh(query.stamp_s, terrain_.stamp_s")
    remove_between(header, "    for (const Track &track : tracks_.tracks)", "    if (obstacle.occupancy == Occupancy::Unknown)")
    replace_once(header, "  TrackSnapshot tracks_;\n", "")
    replace_once(header, "  bool tracks_ready_ = false;\n", "")
    replace_once(header, "  Person,\n", "  Person,  // Reserved legacy log value; geometry-only queries never return it.\n")
    replace_once(header, "// Local experiment contract. This header has no ROS dependency and is not\n// connected to scan_05's GridMap until the three input producers are verified.",
                 "// Geometry-only navigation contract. All unclassified measured obstacles\n// block regardless of semantic class or motion. Required inputs are current\n// geometric occupancy and terrain support; person tracking is diagnostic only.")

    grid_header = WORKSPACE / "src/plan_env/include/plan_env/grid_map.h"
    data = grid_header.read_bytes().splitlines(keepends=True)
    grid_header.write_bytes(b"".join(line for line in data if not any(token in line for token in
        (b"tracked_person_snapshot.hpp", b"reactiveTracksCallback", b"reactive_tracks_sub_"))))
    grid = WORKSPACE / "src/plan_env/src/grid_map.cpp"
    lines = grid.read_bytes().splitlines(keepends=True)
    grid.write_bytes(b"".join(line for line in lines if b"reactive_track_max_age" not in line))
    remove_between(grid, "  reactive_tracks_sub_ =", "  occ_timer_ =")
    methods = WORKSPACE / "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    remove_between(methods, "void GridMap::reactiveTracksCallback(", "bool GridMap::reactiveTerrainReturn(")
    if args.variant == "terrain_cache":
        # Occupancy persists across scans. Its positive terrain classification
        # must have the same lifetime, with nonterrain observations taking
        # precedence. Cell reset, terrain-map replacement and ray clearing
        # invalidate the classification; semantic tracks never clear it.
        data = grid.read_bytes()
        start = data.index(b"void GridMap::cloudCallback(")
        end = data.index(b"void GridMap::publishMap()", start)
        part = data[start:end]
        if part.count(b"  reactive_terrain_hits_.clear();") != 1:
            raise ValueError("Unexpected terrain classification reset")
        part = part.replace(b"  reactive_terrain_hits_.clear();\r\n", b"")
        grid.write_bytes(data[:start] + part + data[end:])
        replace_once(grid,
            "  if (!now_occ) reactive_nonterrain_history_.erase(std::make_tuple(id.x(), id.y(), id.z()));",
            "  if (!now_occ) {\n    const auto key = std::make_tuple(id.x(), id.y(), id.z());\n    reactive_nonterrain_history_.erase(key);\n    reactive_terrain_hits_.erase(key);\n  }")
        raw = WORKSPACE / "src/plan_env/include/plan_env/raw_return_classification.h"
        data = raw.read_bytes().replace(b"current_terrain_return", b"confirmed_terrain_return")
        raw.write_bytes(data)
        replace_once(methods, "positively classified current LiDAR endpoints", "positively classified measured LiDAR endpoints")
        replace_once(methods, "have a positively classified current terrain return.", "have a retained, positively observed terrain classification.")

    manager = WORKSPACE / "src/plan_manage/src/planner_manager.cpp"
    data = manager.read_bytes()
    manager.write_bytes(b"#include <iomanip>\n#include <sstream>\n" + data)
    capture = '''    // Diagnostic capture preserves the exact initializer input, before fitting.
    std::ostringstream seed_capture;
    seed_capture << std::setprecision(17) << "{\\\"interval\\\":" << ts
      << ",\\\"velocity_limit\\\":" << pp_.max_vel_ << ",\\\"acceleration_limit\\\":" << pp_.max_acc_
      << ",\\\"tolerance\\\":" << pp_.feasibility_tolerance_ << ",\\\"points\\\":[";
    for (size_t i = 0; i < point_set.size(); ++i) {
      if (i) seed_capture << ",";
      seed_capture << "[" << point_set[i].x() << "," << point_set[i].y() << "," << point_set[i].z() << "]";
    }
    seed_capture << "],\\\"derivatives\\\":[";
    for (size_t i = 0; i < start_end_derivatives.size(); ++i) {
      if (i) seed_capture << ",";
      const auto &d = start_end_derivatives[i];
      seed_capture << "[" << d.x() << "," << d.y() << "," << d.z() << "]";
    }
    seed_capture << "]}";
    RCLCPP_INFO(node_->get_logger(), "spline_seed_capture %s", seed_capture.str().c_str());
'''
    replace_once(manager, "    auto timed = reactive_stair::initializeTimedCubic", capture + "    auto timed = reactive_stair::initializeTimedCubic")
    shutil.copytree(HERE / "geometry_probe", WORKSPACE / "src/geometry_probe")
    manifest = {"src/" + str(path.relative_to(WORKSPACE / "src")): sha(path)
                for path in sorted((WORKSPACE / "src").rglob("*")) if path.is_file()}
    (WORKSPACE / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    changed = {name: value for name, value in manifest.items() if original.get(name) != value}
    identity_name = "candidate_identity.json" if args.variant == "geometry" else "candidate_terrain_cache_identity.json"
    (HERE / identity_name).write_text(json.dumps({
        "original": str(ORIGINAL), "workspace": str(WORKSPACE),
        "original_manifest_sha256": sha(ORIGINAL / "source_sha256.json"),
        "generator_sha256": sha(Path(__file__)), "variant": args.variant, "changed_files": changed,
        "source_sha256": manifest,
        "contract": "Native geometric occupancy and support own navigation; no semantic tracker input or simulator truth. Timing capture is diagnostic; timing algorithm unchanged in this candidate."
    }, indent=2) + "\n")
    shutil.copyfile(Path(__file__), WORKSPACE / "executed_materialize.py")
    print(json.dumps({"workspace": str(WORKSPACE), "changed_files": list(changed)}))


if __name__ == "__main__":
    main()

"""Separate physical body clearance from the frozen route-height offset."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_10"
OUT = HERE.parent / "builds/scan_11"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if expected != actual or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_10 source/build gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    cpp = OUT / "src/plan_env/src/grid_map.cpp"
    source = cpp.read_bytes()
    old = b'load_parameter(node_, "grid_map.body_height", reactive_parameters_.body_clearance_m, 0.4);'
    new = b'load_parameter(node_, "grid_map.reactive_body_clearance", reactive_parameters_.body_clearance_m, 0.35);'
    if source.count(old) != 1:
        raise ValueError("body-clearance parameter seam changed")
    cpp.write_bytes(source.replace(old, new, 1))
    inc = OUT / "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    text = inc.read_text()
    old_query = '  return reactive_decision_.decide(query, obstacle) == reactive_stair::Verdict::Free ? 0 : 1;'
    new_query = '''  const auto verdict = reactive_decision_.decide(query, obstacle);
  if (verdict != reactive_stair::Verdict::Free) {
    RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 1000,
        "reactive_collision_blocked verdict=%d voxel=%d q=(%.3f,%.3f,%.3f) now=%.3f cloud_stamp=%.3f cloud_ready=%d terrain_cells=%zu body_clearance=%.3f",
        static_cast<int>(verdict), static_cast<int>(obstacle.occupancy),
        query.x_m, query.y_m, query.z_m, query.stamp_s, obstacle.stamp_s,
        reactive_cloud_ready_, reactive_terrain_.cells.size(), reactive_parameters_.body_clearance_m);
  }
  return verdict == reactive_stair::Verdict::Free ? 0 : 1;'''
    if text.count(old_query) != 1:
        raise ValueError("collision decision seam changed")
    inc.write_text(text.replace(old_query, new_query, 1))
    changed = {str(p.relative_to(OUT)): sha(p) for p in (cpp, inc)}
    manifest = {"base": "scan_10", "base_source_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": changed,
                "problem": "grid_map.body_height=0 is a route-coordinate offset, not the robot's physical 0.35 m clearance",
                "change": "Independent grid_map.reactive_body_clearance parameter plus throttled collision verdict diagnostics",
                "preserved": "frozen planner YAML, accepted scan_04, raw occupancy and track/terrain safety rules",
                "status": "source_candidate_requires_build_and_runtime_check"}
    (OUT / "body_clearance_candidate_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

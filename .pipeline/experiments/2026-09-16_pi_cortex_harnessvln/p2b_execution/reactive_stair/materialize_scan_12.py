"""Add bounded near-sensor collision diagnostics without changing decisions."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_11"
OUT = HERE.parent / "builds/scan_12"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if expected != actual or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_11 source/build gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    inc = OUT / "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    source = inc.read_text()
    old = "  const auto verdict = reactive_decision_.decide(query, obstacle);"
    new = old + '''
  static std::set<std::tuple<int, int, int>> diagnosed;
  Eigen::Vector3i diagnostic_id;
  posToIndex(point, diagnostic_id);
  const auto diagnostic_key = std::make_tuple(diagnostic_id.x(), diagnostic_id.y(), diagnostic_id.z());
  if (query.in_map && (point - md_.ray_pos_).norm() < 0.8 &&
      diagnosed.size() < 120 && diagnosed.insert(diagnostic_key).second) {
    const int diagnostic_address = toAddress(diagnostic_id);
    RCLCPP_WARN(node_->get_logger(),
        "near_sensor_verdict verdict=%d voxel=%d q=(%.5f,%.5f,%.5f) sensor=(%.5f,%.5f,%.5f) log_odds=%.5f inflation=%d stamp=%.3f",
        static_cast<int>(verdict), static_cast<int>(obstacle.occupancy),
        point.x(), point.y(), point.z(), md_.ray_pos_.x(), md_.ray_pos_.y(), md_.ray_pos_.z(),
        md_.occupancy_buffer_[diagnostic_address], static_cast<int>(md_.occupancy_buffer_inflate_[diagnostic_address]), query.stamp_s);
  }'''
    if source.count(old) != 1:
        raise ValueError("diagnostic anchor changed")
    inc.write_text(source.replace(old, new))
    manifest = {"base": "scan_11", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(inc.relative_to(OUT)): sha(inc)},
                "behavior": "unchanged; capped diagnostics for 120 distinct near-sensor voxels"}
    (OUT / "diagnostic_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()

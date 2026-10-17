"""Current trunk geometry and atomic cloud fusion, preserving outside unknown."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_12"
OUT = HERE.parent / "builds/scan_13"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(path, old, new):
    source = path.read_bytes()
    if source.count(old) != 1:
        raise ValueError("anchor changed: " + repr(old[:80]))
    path.write_bytes(source.replace(old, new, 1))


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if expected != actual or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_12 source/build gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    inc = OUT / "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    cpp = OUT / "src/plan_env/src/grid_map.cpp"
    hdr = OUT / "src/plan_env/include/plan_env/grid_map.h"
    geometry = hdr.parent / "known_lite3_trunk.h"
    shutil.copy2(HERE / geometry.name, geometry)
    replace(hdr, b'  MappingData md_;', b'''  MappingData md_;
  bool reactive_known_trunk_enabled_ = false;
  double reactive_body_stamp_s_ = 0.0;
  Eigen::Quaterniond reactive_body_quaternion_ = Eigen::Quaterniond::Identity();''')
    anchor = b'  reactive_parameters_.robot_radius_m = mp_.double_cylinder_radius_;'
    replace(cpp, anchor, b'  load_parameter(node_, "grid_map.reactive_known_lite3_trunk", reactive_known_trunk_enabled_, false);\n' + anchor)
    anchor = b'  md_.sliding_map_frame_pos_ = Eigen::Vector3d(pos.x, pos.y, pos.z);'
    replace(cpp, anchor, anchor + b'''
  const auto &q = pose->pose.pose.orientation;
  Eigen::Quaterniond rotation(q.w, q.x, q.y, q.z);
  const double stamp = rclcpp::Time(pose->header.stamp).seconds();
  reactive_body_stamp_s_ = 0.0;
  if (pose->header.frame_id == mp_.frame_id_ && md_.sliding_map_frame_pos_.allFinite() &&
      rotation.coeffs().allFinite() && std::abs(rotation.norm() - 1.0) < 1e-3 && stamp > 0.0) {
    reactive_body_quaternion_ = rotation.normalized();
    reactive_body_stamp_s_ = stamp;
  }''')
    # The ROS executor is single-threaded. Finish classification and raycasting
    # in this callback so no query sees a new stamp with an unfinished map.
    anchor = b'  reactive_pending_cloud_ = true;\r\n}'
    replace(cpp, anchor, b'  reactive_pending_cloud_ = true;\r\n  updateOccupancyCallback();\r\n}')
    replace(inc, b'#include <plan_env/raw_return_classification.h>',
            b'#include <plan_env/raw_return_classification.h>\n#include <plan_env/known_lite3_trunk.h>')
    anchor = b'  const auto verdict = reactive_decision_.decide(query, obstacle);'
    replace(inc, anchor, b'''  if (reactive_known_trunk_enabled_ && query.in_map && reactive_body_stamp_s_ > 0.0) {
    Eigen::Vector3i id;
    posToIndex(point, id);
    const Eigen::Vector3d local = reactive_body_quaternion_.conjugate() *
                                 (point - md_.sliding_map_frame_pos_);
    const bool inside = reactive_stair::knownLite3TrunkInterior(
        local.x(), local.y(), local.z(), query.stamp_s, reactive_body_stamp_s_);
    obstacle.occupancy = reactive_stair::measuredTrunkQuery(
        obstacle.occupancy, md_.occupancy_buffer_inflate_[toAddress(id)] != 0, inside);
  }
''' + anchor)
    manifest = {"base": "scan_12", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (inc, cpp, hdr, geometry)},
                "known_ego_geometry": "Opt-in exact two TORSO URDF boxes at current measured 6D pose; max age 0.1 s; no map clearing",
                "preserved": "External unknown, any inflated hit, tracked person precedence, stale required inputs remain blocked",
                "fusion": "Existing raycasting finishes atomically within its cloud callback before other queries"}
    (OUT / "known_trunk_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()

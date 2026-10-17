"""Record the first failed initial spline pose with exact collision verdicts."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_15"
OUT = HERE.parent / "builds/scan_16"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(path, old, new):
    source = path.read_bytes()
    if source.count(old) != 1:
        raise ValueError("anchor changed: " + repr(old[:70]))
    path.write_bytes(source.replace(old, new, 1))


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if expected != actual or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_15 source/build gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    hdr = OUT / "src/plan_env/include/plan_env/grid_map.h"
    inc = OUT / "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    opt = OUT / "src/bspline_opt/src/bspline_optimizer.cpp"
    anchor = b'  inline int getInflateOccupancy(Eigen::Vector3d pos, double yaw);'
    replace(hdr, anchor, anchor + b'\n  void logInitialSplineCollision(const Eigen::Vector3d &pos, double yaw);')
    anchor = b'  bool reactive_known_trunk_enabled_ = false;'
    replace(hdr, anchor, anchor + b'\n  bool reactive_diagnostic_force_ = false;')
    replace(inc,
        b'  if (query.in_map && (point - md_.ray_pos_).norm() < 0.8 &&\n      diagnosed.size() < 120 && diagnosed.insert(diagnostic_key).second) {',
        b'  if (query.in_map && (reactive_diagnostic_force_ || ((point - md_.ray_pos_).norm() < 0.8 &&\n      diagnosed.size() < 120 && diagnosed.insert(diagnostic_key).second))) {')
    with inc.open("ab") as f:
        f.write(b'''
void GridMap::logInitialSplineCollision(const Eigen::Vector3d &pos, double yaw) {
  RCLCPP_WARN(node_->get_logger(),
      "initial_spline_collision pos=(%.8f,%.8f,%.8f) yaw=%.8f body=(%.8f,%.8f,%.8f) body_q=(%.8f,%.8f,%.8f,%.8f) body_stamp=%.8f now=%.8f",
      pos.x(), pos.y(), pos.z(), yaw,
      md_.sliding_map_frame_pos_.x(), md_.sliding_map_frame_pos_.y(), md_.sliding_map_frame_pos_.z(),
      reactive_body_quaternion_.w(), reactive_body_quaternion_.x(), reactive_body_quaternion_.y(), reactive_body_quaternion_.z(),
      reactive_body_stamp_s_, node_->now().seconds());
  const Eigen::Vector3d heading(std::cos(yaw), std::sin(yaw), 0.0);
  reactive_diagnostic_force_ = true;
  reactiveOccupancy(pos + mp_.double_cylinder_offset_ * heading);
  reactiveOccupancy(pos - mp_.double_cylinder_offset_ * heading);
  reactive_diagnostic_force_ = false;
}
''')
    anchor = b'            if (t <= bspline_interval_) // First 3 control points in obstacles!'
    replace(opt, anchor, b'''            static bool diagnosed_initial_collision = false;
            if (t <= bspline_interval_ && !diagnosed_initial_collision) {
              grid_map_->logInitialSplineCollision(pos, estimateSegmentYaw(pos, pos_next));
              diagnosed_initial_collision = true;
            }
''' + anchor)
    manifest = {"base": "scan_15", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (hdr, inc, opt)},
                "behavior": "unchanged; one forced diagnostic of the first rejected initial spline pose"}
    (OUT / "initial_pose_diagnostic_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()

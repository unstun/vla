"""Share the controller's unresolved-direction rule across collision callers."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_16"
OUT = HERE.parent / "builds/scan_17"


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
        raise ValueError("scan_16 source/build gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    hdr = OUT / "src/plan_env/include/plan_env/grid_map.h"
    inc = OUT / "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    opt = OUT / "src/bspline_opt/src/bspline_optimizer.cpp"
    fsm = OUT / "src/plan_manage/src/scan_replan_fsm.cpp"
    heading = hdr.parent / "motion_heading.h"
    shutil.copy2(HERE / heading.name, heading)
    anchor = b'  void logInitialSplineCollision(const Eigen::Vector3d &pos, double yaw);'
    replace(hdr, anchor, anchor + b'\n  double collisionSegmentYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const;')
    replace(inc, b'#include <plan_env/known_lite3_trunk.h>',
            b'#include <plan_env/known_lite3_trunk.h>\n#include <plan_env/motion_heading.h>')
    with inc.open("ab") as f:
        f.write(b'''
double GridMap::collisionSegmentYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const {
  const Eigen::Vector3d direction = reactive_body_quaternion_.toRotationMatrix().col(0);
  const double body_yaw = std::atan2(direction.y(), direction.x());
  return reactive_stair::motionHeading(to.x() - from.x(), to.y() - from.y(), body_yaw,
                                      node_->now().seconds(), reactive_body_stamp_s_);
}
''')
    replace(opt,
        b'    Eigen::Vector2d diff(to(0) - from(0), to(1) - from(1));\r\n    if (diff.squaredNorm() < 1e-8)\r\n      return 0.0;\r\n    return std::atan2(diff(1), diff(0));',
        b'    return grid_map_->collisionSegmentYaw(from, to);')
    replace(fsm,
        b'    Eigen::Vector2d diff(to(0) - from(0), to(1) - from(1));\n    if (diff.squaredNorm() < 1e-8)\n      return getOdomYaw();\n    return std::atan2(diff(1), diff(0));',
        b'    return planner_manager_->grid_map_->collisionSegmentYaw(from, to);')
    manifest = {"base": "scan_16", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (hdr, inc, opt, fsm, heading)},
                "evidence": "scan16_settled: actual yaw -1.525 rad, initial spline collision yaw -0.583 rad, two unknown lateral references",
                "change": "Optimizer and live safety use fresh measured body yaw below the existing controller's 0.01 m direction threshold",
                "preserved": "all collision verdict rules, observed person precedence, external unknown rejection; stale direction fallback returns NaN and blocks"}
    (OUT / "motion_heading_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()

"""Use the frozen controller's lookahead and velocity fallback for spline yaw."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_17"
OUT = HERE.parent / "builds/scan_18"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(path, old, new, count=1):
    source = path.read_bytes()
    if source.count(old) != count:
        raise ValueError("anchor changed: " + repr(old[:70]))
    path.write_bytes(source.replace(old, new))


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if expected != actual or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_17 source/build gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    hdr = OUT / "src/plan_env/include/plan_env/grid_map.h"
    inc = OUT / "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    opt = OUT / "src/bspline_opt/src/bspline_optimizer.cpp"
    fsm = OUT / "src/plan_manage/src/scan_replan_fsm.cpp"
    anchor = b'  double collisionSegmentYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const;'
    replace(hdr, anchor, anchor + b'''
  static constexpr double collision_heading_lookahead_s = 0.8;
  double collisionTrajectoryYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &ahead,
                               const Eigen::Vector3d &velocity) const;''')
    with inc.open("ab") as f:
        f.write(b'''
double GridMap::collisionTrajectoryYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &ahead,
                                       const Eigen::Vector3d &velocity) const {
  if (!from.allFinite() || !ahead.allFinite() || !velocity.allFinite())
    return std::numeric_limits<double>::quiet_NaN();
  if ((ahead - from).head<2>().squaredNorm() < 1e-4)
    return collisionSegmentYaw(Eigen::Vector3d::Zero(), velocity);
  return collisionSegmentYaw(from, ahead);
}
''')
    replace(opt,
        b'Eigen::Vector3d pos_next = traj.evaluateDeBoorT(std::min(t + t_step, tmp));',
        b'Eigen::Vector3d pos_next = traj.evaluateDeBoorT(std::min(t + GridMap::collision_heading_lookahead_s, tmp));\n'
        b'          const double spline_yaw = grid_map_->collisionTrajectoryYaw(pos, pos_next, traj.getDerivative().evaluateDeBoorT(t));', count=2)
    replace(opt, b'grid_map_->getInflateOccupancy(pos, estimateSegmentYaw(pos, pos_next))',
            b'grid_map_->getInflateOccupancy(pos, spline_yaw)', count=2)
    replace(opt, b'grid_map_->logInitialSplineCollision(pos, estimateSegmentYaw(pos, pos_next));',
            b'grid_map_->logInitialSplineCollision(pos, spline_yaw);')
    replace(fsm,
        b'Eigen::Vector3d pos_next = info->position_traj_.evaluateDeBoorT(std::min(t + time_step, info->duration_));\n      if (map->getInflateOccupancy(pos, estimateYawFromSegment(pos, pos_next)))',
        b'''Eigen::Vector3d pos_next = info->position_traj_.evaluateDeBoorT(std::min(t + GridMap::collision_heading_lookahead_s, info->duration_));
      const double spline_yaw = map->collisionTrajectoryYaw(pos, pos_next, info->velocity_traj_.evaluateDeBoorT(t));
      if (map->getInflateOccupancy(pos, spline_yaw))''')
    manifest = {"base": "scan_17", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (hdr, inc, opt, fsm)},
                "problem": "tiny check-step chords disagree with the controller's 0.8 s heading lookahead; using current yaw for all distant small chords is also incorrect",
                "change": "Spline optimization and live safety use the exact controller direction order: 0.8 s lookahead, velocity, then current measured yaw",
                "preserved": "collision sample spacing, heading controller, occupancy rules, limits, time caps; fresh body fallback still required"}
    (OUT / "controller_heading_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()

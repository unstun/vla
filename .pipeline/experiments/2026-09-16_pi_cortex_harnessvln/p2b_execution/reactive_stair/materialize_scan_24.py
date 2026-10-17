"""Require complete sampled spline coverage before publication and while executing."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_23"
OUT = HERE.parent / "builds/scan_24"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((BASE / "build_result.json").read_text())["passed"]:
        raise ValueError("scan_23 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    helper = OUT / "src/bspline_opt/include/bspline_opt/full_trajectory_collision.h"
    shutil.copy2(HERE / helper.name, helper)
    spline = OUT / "src/bspline_opt/include/bspline_opt/uniform_bspline.h"
    once(spline, "    double getInterval();", "    double getInterval();\n    int getDegree() const { return p_; }")
    manager = OUT / "src/plan_manage/src/planner_manager.cpp"
    fsm = OUT / "src/plan_manage/src/scan_replan_fsm.cpp"
    for path in (manager, fsm):
        path.write_bytes(b'#include <bspline_opt/full_trajectory_collision.h>\n' + path.read_bytes())
    once(manager, "    // save planned results", '''    const auto collision_started = std::chrono::steady_clock::now();
    const auto collision = reactive_stair::checkFullCubicTrajectory(
        pos, 0.0, grid_map_->getResolution(), GridMap::collision_heading_lookahead_s,
        [this](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
          return grid_map_->collisionTrajectoryYaw(p, ahead, v);
        },
        [this](const Eigen::Vector3d &p, double yaw) { return grid_map_->getInflateOccupancy(p, yaw) != 0; });
    const double collision_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - collision_started).count();
    if (!collision.clear()) {
      RCLCPP_WARN(node_->get_logger(), "final_spline_rejected status=%d t=%.9f duration=%.9f samples=%zu wall_ms=%.3f",
                  static_cast<int>(collision.status), collision.first_time_s, collision.duration_s, collision.samples, collision_ms);
      continuous_failures_count_++;
      return false;
    }
    RCLCPP_INFO(node_->get_logger(), "full_spline_sampled_clear duration=%.9f samples=%zu wall_ms=%.3f",
                collision.duration_s, collision.samples, collision_ms);

    // save planned results''')
    once(fsm, '''    constexpr double time_step = 0.01;
    double t_cur = (node_->now() - info->start_time_).seconds();
    double t_2_3 = info->duration_ * 2 / 3;
    for (double t = t_cur; t < info->duration_; t += time_step)
    {
      if (t_cur < t_2_3 && t >= t_2_3) // If t_cur < t_2_3, only the first 2/3 partition of the trajectory is considered valid and will get checked.
        break;

      Eigen::Vector3d pos = info->position_traj_.evaluateDeBoorT(t);
      Eigen::Vector3d pos_next = info->position_traj_.evaluateDeBoorT(std::min(t + GridMap::collision_heading_lookahead_s, info->duration_));
      const double spline_yaw = map->collisionTrajectoryYaw(pos, pos_next, info->velocity_traj_.evaluateDeBoorT(t));
      if (map->getInflateOccupancy(pos, spline_yaw))
      {
        if (planFromCurrentTraj()) // Make a chance
        {
          changeFSMExecState(EXEC_TRAJ, "SAFETY");
          return;
        }
        else
        {
          if (t - t_cur < emergency_time_) // 0.8s of emergency time
          {
            RCLCPP_WARN(node_->get_logger(), "Obstacle discovered; emergency stop in %.3fs", t - t_cur);
            changeFSMExecState(EMERGENCY_STOP, "SAFETY");
          }
          else
          {
            //ROS_WARN("current traj in collision, replan.");
            changeFSMExecState(REPLAN_TRAJ, "SAFETY");
          }
          return;
        }
        break;
      }
    }''', '''    const double raw_t_cur = (node_->now() - info->start_time_).seconds();
    const auto collision = reactive_stair::checkFullCubicTrajectory(
        info->position_traj_, raw_t_cur, map->getResolution(), GridMap::collision_heading_lookahead_s,
        [&map](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
          return map->collisionTrajectoryYaw(p, ahead, v);
        },
        [&map](const Eigen::Vector3d &p, double yaw) { return map->getInflateOccupancy(p, yaw) != 0; });
    if (collision.clear()) return;
    if (collision.status != reactive_stair::TrajectoryCheckStatus::Collision) {
      // Never evaluate/replan from an invalid old curve or a regressed clock.
      RCLCPP_ERROR(node_->get_logger(), "remaining_spline_invalid status=%d raw_t=%.9f samples=%zu",
                   static_cast<int>(collision.status), raw_t_cur, collision.samples);
      flag_escape_emergency_ = true;
      changeFSMExecState(EMERGENCY_STOP, "INVALID_SPLINE_INPUT");
      return;
    }
    const double t_cur = std::min(collision.duration_s, std::max(0.0, raw_t_cur));
    if (planFromCurrentTraj()) {
      changeFSMExecState(EXEC_TRAJ, "SAFETY");
      return;
    }
    if (collision.first_time_s - t_cur < emergency_time_) {
      RCLCPP_WARN(node_->get_logger(), "Obstacle discovered; emergency stop in %.3fs", collision.first_time_s - t_cur);
      changeFSMExecState(EMERGENCY_STOP, "SAFETY");
    } else {
      changeFSMExecState(REPLAN_TRAJ, "SAFETY");
    }''')
    (OUT / "full_trajectory_manifest.json").write_text(json.dumps({
        "base": "scan_23", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (helper, spline, manager, fsm)},
        "generator_sha256": sha(Path(__file__)),
        "change": "Complete final spline and remaining execution interval sampling, including exact endpoints; relative-time/shape validation and finite fail-closed status",
        "preserved": "Original optimizer objectives, heading lookahead/fallback, occupancy/terrain/person thresholds and unknown blocking. No short-prefix probe imported.",
        "contract": "Maximum temporal step .01s, center displacement bound half voxel using derivative control-point norms; maximum10000 samples. Sampled checks do not prove continuous rotating footprint coverage."}, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()

"""Build a reviewable inventory from inspected, pinned repository sources."""
import hashlib
import json
from pathlib import Path
from fetch_sources import DEST, ROOT

# Context and observations are source-reading notes, not new runtime results.
NOTES = {
 'wuyi2121/SCAN-Planner': ('legged', 'ROS 1; Go2; cloud/odometry; B-spline output', 'Three initialization attempts and failure counter; eventual emergency stop/new target.', 'src/planner/plan_manage/src/scan_replan_fsm.cpp', 'void SCANReplanFSM::finishProcess', '50 independent trials per scene, SR/CR/SPL in author paper; no fixed 30 Hz acceptance criterion found.'),
 'byangw/PCT_planner': ('global/3D', 'ROS/Python/C++; prebuilt point-cloud tomography; global trajectory', 'Search and trajectory optimization can each return failure.', 'planner/lib/src/ele_planner/offline_ele_planner.cc', 'bool OfflineElePlanner::Plan', 'Paper Table IV uses 50 trajectory-generation attempts, not whole closed-loop missions.'),
 'leggedrobotics/art_planner': ('legged', 'ROS Noetic; ANYmal; elevation map; geometric path to follower', 'Separate NO_SOLUTION/INVALID_START/INVALID_GOAL feedback; publish only solved paths.', 'art_planner_ros/src/planner_ros.cpp', 'case PlannerStatus::NOT_SOLVED', 'SubT deployment/bag replay; paper target 0.5 Hz differs from released params.yaml default 1 Hz.'),
 'jizhang-cmu/autonomy_stack_go2': ('legged', 'ROS 2 foxy-humble; Go2; terrain point cloud; path and cmd_vel', 'Reduce candidate path scale/range; publish a one-point origin path if no path is found.', 'src/base_autonomy/local_planner/src/localPlanner.cpp', 'if (!pathFound)', 'Runnable stack and demonstration instructions; no repeated-trial acceptance percentage identified in inspected README/source.'),
 'leggedrobotics/viplanner': ('legged/learned', 'ROS Noetic; RGB/depth/semantics; learned local path plus risk status', 'Can flag high-risk path prediction as invalid; exposes planning time separately from other processing.', 'ros/planner/src/viplanner_node.py', 'if fear > 0.7', 'Paper uses 500 random paths per environment; reported path goal attainment is not our full mission SR.'),
 'leggedrobotics/fdm': ('legged/learned', 'Isaac Lab / ROS Noetic; ANYmal; height scan and proprioception; MPPI velocity sequence', 'Planning and high-frequency path following have separate threads.', 'ros/fdm_navigation_ros/scripts/planner_node.py', 'Thread to follow the latest path', 'Paper Table III: 88.33% 2D / 73.75% 3D mission success; inspect reward/timeout/terrain before comparison.'),
 'WangJinCheng1998/sandplanner': ('legged/learned', 'Python server / NavDP simulator; depth; candidate B-spline paths', 'Samples candidates and selects using ESDF evaluation; warmup success counters are not navigation success rates.', 'sand_planner/core/trajectory_evaluator.py', 'def evaluate', 'Paper evaluates 2020 ClutteredEnv and 4040 InternScenes episodes; 90.1% / 72.0% SR.'),
 'ori-drs/field_local_planner': ('ground/reactive', 'ROS 1 plugins; map/cloud and state; path/twist', 'execute returns validity and status; output publication depends on validity.', 'field_local_planner_base/field_local_planner_base_plugin/src/field_local_planner_base_plugin/base_plugin.cpp', 'bool valid_output', 'Reusable APF/RMP/Falco/plugin structure; no common numerical qualification cutoff found in inspected files.'),
 'ZJU-FAST-Lab/ego-planner': ('aerial', 'ROS 1; quadrotor; cloud/depth/odometry; B-spline', 'Retries three initialization choices and can trigger emergency stop.', 'src/planner/plan_manage/src/ego_replan_fsm.cpp', 'bool EGOReplanFSM::planFromCurrentTraj', 'README around 1 ms is an author claim; FlightBench independently reports context-dependent runtime and success.'),
 'ZJU-FAST-Lab/EGO-Planner-v2': ('aerial/same lineage', 'ROS 1; quadrotor swarm; polynomial trajectories', 'Global-trajectory attempts can repeat; emergency recovery is explicit.', 'swarm-playground/main_ws/src/planner/plan_manage/src/ego_replan_fsm.cpp', 'case GEN_NEW_TRAJ', 'Same EGO family, not an independent vote; failure branches establish handling, not failure frequency.'),
 'HKUST-Aerial-Robotics/Fast-Planner': ('aerial', 'ROS 1; quadrotor; map/odometry; kinodynamic trajectory', 'Failed replanning returns FSM to trajectory generation.', 'fast_planner/plan_manage/src/kino_replan_fsm.cpp', 'bool success = callKinodynamicReplan', 'FlightBench uses ten independent runs per metric and reports lower success in harder cases.'),
 'mit-acl/faster': ('aerial/ground', 'ROS 1; occupancy; Gurobi MIQP; committed/safe trajectory', 'Failed JPS/whole/safe search returns without replacing committed plan.', 'faster/src/faster.cpp', 'if (solved_safe == false)', 'Paper explicitly keeps prior committed safe trajectory on infeasibility or late replan; assumptions matter.'),
 'rst-tu-dortmund/teb_local_planner': ('ground', 'ROS 1 Noetic; costmap/footprint; local twist', 'Invalid trajectories return failure; optional reduced-horizon recovery.', 'src/teb_local_planner_ros.cpp', 'if (!feasible)', 'Arena-Bench evaluates TEB across platforms, scenes and simulation/real repetitions; not zero internal failures.'),
 'ros-navigation/navigation2': ('ground/framework', 'Current main inspected; ROS 2; plugins; action / cmd_vel', 'MPPI resets/retries before NoValidControl; system test checks terminal action success.', 'nav2_mppi_controller/src/optimizer.cpp', 'bool Optimizer::fallback', 'Current-main MPPI is a comparison reference, not our Foxy dependency. Foxy 0.4.7 remains separately pinned.'),
 'ros-planning/navigation': ('ground/framework', 'ROS 1 Noetic; archived upstream; DWA/move_base; cmd_vel', 'DWA can reject all samples; move_base stops on stale costmap and supports recovery.', 'move_base/src/move_base.cpp', 'Sensor data is out of date', 'Default controller frequency 20 Hz is configuration, not achieved runtime or mandatory acceptance.'),
 'ignc-research/arena-bench': ('benchmark', 'ROS / Gazebo / Flatland; multiple wheeled robots and planners', 'Launch supports interchangeable planners and scenario/repetition workflow.', 'arena_bringup/launch/start_arena_gazebo.launch', 'action_frequency', 'Paper: 15 repeats per planner/scenario in sim and real; its success definition allows fewer than two collisions.'),
 'SlyPredator/the-barn-challenge': ('benchmark', 'BARN/DynaBARN; Jackal/Gazebo; containerized navigation', 'Runner records success/collision/timeout and normalized traversal-time score.', 'run.py', 'while compute_distance(goal_coor', 'Pinned runner: 1 m goal tolerance, 100 s timeout after motion starts. Do not copy that tolerance into our task.'),
 'thu-uav/FlightBench': ('benchmark', 'Ubuntu 20.04/ROS Noetic; quadrotor; Flightmare/Gazebo/GPU render', 'Bag parser checks start/end and collision, and separates mapping/planning/projection time.', 'flightbench/script/bag_parser.py', 'def parse_one_bag', 'Author paper: ten independent runs per metric; difficulty and latency are explicit experimental variables.'),
}


def main():
    rows = json.loads((DEST / 'manifest.json').read_text())
    result = []
    total_files = total_bytes = 0
    for row in rows:
        repo = row['requested_repository']
        group, environment, finding, code, needle, evidence = NOTES[repo]
        folder = ROOT / row['selected_source_path']
        for item in row['files']:
            raw = (folder / item['path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == item['sha256'], (repo, item['path'])
            total_files += 1
            total_bytes += len(raw)
        lines = (folder / code).read_text().splitlines()
        matches = [i + 1 for i, line in enumerate(lines) if needle in line]
        assert matches, (repo, needle)
        anchor = matches[0]
        url = f"{row['canonical_url']}/blob/{row['pinned_commit']}/{code}#L{anchor}"
        original_commands = []
        for item in row['files']:
            if item['path'].lower().startswith('readme'):
                original_commands += [s.strip() for s in (folder/item['path']).read_text().splitlines()
                                      if any(t in s for t in ('roslaunch ', 'ros2 launch ', 'python ', 'python3 '))]
        result.append(dict(**row, group=group, environment_and_interface=environment,
                           observed_code_behavior=finding, evaluation_evidence=evidence,
                           code_permalink=url, evidence_line=anchor,
                           original_readme_commands=original_commands[:8],
                           asset_boundary='README links only; no weights/datasets downloaded',
                           inspection_scope='README/license, selected code/config/test, and linked primary evaluation when cited'))
    assert len(result) == len(NOTES) == 18
    (DEST/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    # JSON is valid YAML; preserve complete provenance without a YAML dependency.
    (DEST/'repository_manifest.yaml').write_text(json.dumps(dict(
        topic='Navigation qualification evidence',date='2026-10-09',status='surveyed',
        repositories=result,selection=dict(recommended_first_target='Pinned SCAN under same-input replay',
            reason='Closest algorithm and interface; no new runtime or adoption claim',
            unresolved_questions=['Comparable full-mission success rate', 'Failed-search input cause', 'Freshness and recovery coupling'])),indent=2)+'\n')
    table=['# Inspected repository inventory','',
           '18 repositories: 15 implementations/frameworks and 3 benchmarks. Same-lineage repositories are not independent evidence. All status labels are `surveyed`; no upstream run was performed.','',
           '| Repository / pin | Scope | Verified code behavior | Evaluation evidence / boundary |',
           '|---|---|---|---|']
    for r in result:
        table.append(f"| [{r['canonical_repository']}]({r['code_permalink']}) `{r['pinned_commit'][:8]}` | {r['environment_and_interface']} | {r['observed_code_behavior']} | {r['evaluation_evidence']} |")
    (DEST/'comparison.md').write_text('\n'.join(table)+'\n')
    quality=dict(repositories=18,files_hash_verified=total_files,source_bytes_verified=total_bytes,
                 all_code_anchors_verified=True,upstream_runs=0,runtime_changed=False)
    (DEST/'quality.json').write_text(json.dumps(quality,indent=2)+'\n')
    print(json.dumps(quality))


if __name__ == '__main__':
    main()

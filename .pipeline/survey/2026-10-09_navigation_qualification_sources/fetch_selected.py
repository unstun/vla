"""Download selected text files for source inspection, without executing them."""
import concurrent.futures
import hashlib
import json
from fetch_sources import DEST, get

SELECT = {
 'wuyi2121/SCAN-Planner': ['src/planner/plan_manage/src/scan_replan_fsm.cpp'],
 'byangw/PCT_planner': ['planner/lib/src/ele_planner/offline_ele_planner.cc'],
 'leggedrobotics/art_planner': ['art_planner_ros/src/planner_ros.cpp', 'art_planner_ros/config/params.yaml'],
 'jizhang-cmu/autonomy_stack_go2': ['src/base_autonomy/local_planner/src/localPlanner.cpp', 'src/base_autonomy/local_planner/src/pathFollower.cpp'],
 'leggedrobotics/viplanner': ['ros/planner/src/viplanner_node.py', 'viplanner/utils/eval_utils.py'],
 'leggedrobotics/fdm': ['scripts/eval_metrics.py', 'ros/fdm_navigation_ros/scripts/planner_node.py'],
 'WangJinCheng1998/sandplanner': ['sand_planner/agent/sand_planner_agent.py', 'sand_planner/core/trajectory_evaluator.py'],
 'ori-drs/field_local_planner': ['field_local_planner_ros/src/local_planner_node.cpp'],
 'ZJU-FAST-Lab/ego-planner': ['src/planner/plan_manage/src/ego_replan_fsm.cpp'],
 'ZJU-FAST-Lab/EGO-Planner-v2': ['swarm-playground/main_ws/src/planner/plan_manage/src/ego_replan_fsm.cpp'],
 'HKUST-Aerial-Robotics/Fast-Planner': ['fast_planner/plan_manage/src/kino_replan_fsm.cpp'],
 'mit-acl/faster': ['faster/src/faster.cpp'],
 'rst-tu-dortmund/teb_local_planner': ['src/teb_local_planner_ros.cpp'],
 'ros-navigation/navigation2': ['nav2_controller/src/controller_server.cpp', 'nav2_mppi_controller/README.md', 'nav2_mppi_controller/src/optimizer.cpp', 'nav2_system_tests/src/system/nav_to_pose_tester_node.py'],
 'ros-planning/navigation': ['dwa_local_planner/src/dwa_planner_ros.cpp', 'move_base/src/move_base.cpp'],
 'ignc-research/arena-bench': ['.gitmodules', 'arena_bringup/launch/start_arena_gazebo.launch'],
 'SlyPredator/the-barn-challenge': ['run.py', 'report_test.py'],
 'thu-uav/FlightBench': ['flightbench/script/test.py', 'flightbench/script/bag_parser.py'],
}


def collect(repo, paths):
    directory = DEST / 'source' / repo.replace('/', '__')
    metadata_path = directory / 'metadata.json'
    metadata = json.loads(metadata_path.read_text())
    known_paths = set((directory / 'tree_paths.txt').read_text().splitlines())
    for path in paths:
        if path not in known_paths:
            print(repo, 'MISSING', path, flush=True)
            continue
        if any(item['path'] == path for item in metadata['files']):
            continue
        url = f"https://raw.githubusercontent.com/{metadata['canonical_repository']}/{metadata['pinned_commit']}/{path}"
        raw = get(url)
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        metadata['files'].append(dict(path=path, url=url, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    metadata_path.write_text(json.dumps(metadata, indent=2) + '\n')
    print(repo, 'text files', len(metadata['files']), flush=True)
    return metadata


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [pool.submit(collect, repo, paths) for repo, paths in SELECT.items()]
        rows = [task.result() for task in tasks]
    (DEST / 'manifest.json').write_text(json.dumps(rows, indent=2) + '\n')

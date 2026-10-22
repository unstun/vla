from pathlib import Path
import subprocess,os,json
R=Path('/home/ubuntu/sun/vla_v288_20261020');P=Path('/home/ubuntu/sun/vla_v287_20261020');V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288';E=R/'parent_tracking01';(E/'source').mkdir(parents=True)
(E/'source/CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.16)
project(parent_tracking_control)
set(CMAKE_CXX_STANDARD 17)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_gtest REQUIRED)
find_package(scan_nav2_controller REQUIRED)
ament_add_gtest(parent_tracking /source/src/scan_nav2_controller/test/test_tracking_behavior.cpp)
ament_target_dependencies(parent_tracking rclcpp nav_msgs scan_planner_msgs tf2 scan_nav2_controller)
''')
cmd=['docker','run','--rm','--pull=never','--name','v288-parent-tracking','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','--network=host','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs','-v',str(P/'native')+':/work:ro','-v',str(E)+':/evaluation:rw','-v',str(V)+':/source:ro','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','-c','source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && cmake -S /evaluation/source -B /evaluation/build && cmake --build /evaluation/build -j2 && /evaluation/build/parent_tracking --gtest_filter=TrackingBehavior.TerminalYawCentersInWorldCoordinatesWithSlew --gtest_output=xml:/evaluation/result.xml']
with (E/'log').open('x') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
(E/'result.json').write_text(json.dumps(dict(returncode=rc,expected_test_failure=True,physics_steps=0),indent=2)+'\n')

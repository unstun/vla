cmake_minimum_required(VERSION 3.8)
project(nav2_alignment_contract)
set(CMAKE_CXX_STANDARD 17)
find_package(ament_cmake REQUIRED)
find_package(Eigen3 REQUIRED)
set(dependencies ament_index_cpp bspline_opt geometry_msgs nav_msgs path_searching plan_env rclcpp rosgraph_msgs scan_planner_msgs sensor_msgs std_msgs tf2 tf2_geometry_msgs tf2_ros traj_utils visualization_msgs)
foreach(dependency ${dependencies})
  find_package(${dependency} REQUIRED)
endforeach()
add_executable(native_probe native_probe.cpp
  /workspace/src/plan_manage/src/scan_replan_fsm.cpp
  /workspace/src/plan_manage/src/planner_manager.cpp)
target_include_directories(native_probe PRIVATE /workspace/src/plan_manage/include)
target_compile_options(native_probe PRIVATE -fno-access-control)
ament_target_dependencies(native_probe ${dependencies})
target_link_libraries(native_probe Eigen3::Eigen)
add_executable(performance_probe performance_probe.cpp
  /workspace/src/plan_manage/src/scan_replan_fsm.cpp
  /workspace/src/plan_manage/src/planner_manager.cpp)
target_include_directories(performance_probe PRIVATE /workspace/src/plan_manage/include)
target_compile_options(performance_probe PRIVATE -fno-access-control)
ament_target_dependencies(performance_probe ${dependencies})
target_link_libraries(performance_probe Eigen3::Eigen)

add_executable(cache_probe cache_probe.cpp)
target_compile_options(cache_probe PRIVATE -fno-access-control)
ament_target_dependencies(cache_probe ${dependencies})
target_link_libraries(cache_probe Eigen3::Eigen)

cmake_minimum_required(VERSION 3.8)
project(v126_retry_ownership_contract)
set(CMAKE_CXX_STANDARD 17)
find_package(ament_cmake REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(Threads REQUIRED)
set(dependencies ament_index_cpp bspline_opt geometry_msgs nav_msgs path_searching
  plan_env rclcpp rosgraph_msgs scan_planner_msgs sensor_msgs std_msgs tf2
  tf2_geometry_msgs tf2_ros traj_utils visualization_msgs)
foreach(dependency ${dependencies})
  find_package(${dependency} REQUIRED)
endforeach()
foreach(mode parent candidate)
  add_executable(retry_${mode} retry_probe.cpp
    ${FIXTURE_ROOT}/${mode}/planner_manager.cpp
    ${FIXTURE_ROOT}/${mode}/scan_replan_fsm.cpp)
  target_include_directories(retry_${mode} BEFORE PRIVATE /task/candidate/src/plan_manage/include)
  target_compile_options(retry_${mode} PRIVATE -fno-access-control)
  ament_target_dependencies(retry_${mode} ${dependencies})
  target_link_libraries(retry_${mode} Eigen3::Eigen OpenSSL::Crypto Threads::Threads)
endforeach()
target_compile_definitions(retry_parent PRIVATE RETRY_PARENT)

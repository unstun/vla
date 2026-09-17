cmake_minimum_required(VERSION 3.8)
project(scan_replan_native_repro)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
add_compile_options(-Wall -Wextra -Wpedantic)

find_package(ament_cmake REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(bspline_opt REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(path_searching REQUIRED)
find_package(plan_env REQUIRED)
find_package(rclcpp REQUIRED)
find_package(scan_planner_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(traj_utils REQUIRED)
find_package(visualization_msgs REQUIRED)

set(SCAN03_SOURCE_ROOT "" CACHE PATH "Read-only root of accepted scan_03 source workspace containing src/plan_manage")
if(NOT SCAN03_SOURCE_ROOT)
  message(FATAL_ERROR "Set -DSCAN03_SOURCE_ROOT=/path/to/scan_03/source-root. Expected ${SCAN03_SOURCE_ROOT}/src/plan_manage/src/planner_manager.cpp")
endif()
get_filename_component(SCAN03_SOURCE_ROOT "${SCAN03_SOURCE_ROOT}" ABSOLUTE)
set(SCAN_MANAGER_CPP "${SCAN03_SOURCE_ROOT}/src/plan_manage/src/planner_manager.cpp" CACHE FILEPATH "planner_manager.cpp to compile. Defaults to frozen scan_03; may point at an isolated instrumented copy.")
get_filename_component(SCAN_MANAGER_CPP "${SCAN_MANAGER_CPP}" ABSOLUTE)
set(SCAN03_PLANNER_MANAGER_CPP "${SCAN_MANAGER_CPP}")
set(SCAN03_PLAN_MANAGE_INCLUDE "${SCAN03_SOURCE_ROOT}/src/plan_manage/include")
if(NOT EXISTS "${SCAN03_PLANNER_MANAGER_CPP}")
  message(FATAL_ERROR "Missing planner_manager.cpp at ${SCAN03_PLANNER_MANAGER_CPP}")
endif()
if(NOT EXISTS "${SCAN03_PLAN_MANAGE_INCLUDE}/plan_manage/planner_manager.h")
  message(FATAL_ERROR "Missing planner_manager.h under ${SCAN03_PLAN_MANAGE_INCLUDE}")
endif()

set(scan_replan_native_repro_dependencies
  ament_index_cpp bspline_opt geometry_msgs nav_msgs path_searching plan_env
  rclcpp scan_planner_msgs sensor_msgs std_msgs tf2 tf2_geometry_msgs tf2_ros
  traj_utils visualization_msgs)

add_executable(rebound_replan_repro
  src/rebound_replan_repro.cpp
  ${SCAN03_PLANNER_MANAGER_CPP})
target_include_directories(rebound_replan_repro PRIVATE ${SCAN03_PLAN_MANAGE_INCLUDE})
ament_target_dependencies(rebound_replan_repro ${scan_replan_native_repro_dependencies})
target_link_libraries(rebound_replan_repro Eigen3::Eigen)

install(TARGETS rebound_replan_repro DESTINATION lib/${PROJECT_NAME})

ament_package()

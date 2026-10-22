cmake_minimum_required(VERSION 3.16)
project(pct_planner)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(pybind11_vendor REQUIRED)
find_package(pybind11 REQUIRED)

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(GTSAM REQUIRED)

execute_process(
  COMMAND "${Python3_EXECUTABLE}" -c "import sysconfig; print(sysconfig.get_path('platlib', vars={'platbase': '.', 'base': '.'}))"
  OUTPUT_VARIABLE PYTHON_INSTALL_DIR
  OUTPUT_STRIP_TRAILING_WHITESPACE
)

add_subdirectory(lib)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS scripts/planner_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_python_install_package(${PROJECT_NAME})

# Export the existing native implementation without changing algorithm sources.
install(DIRECTORY lib/src/ DESTINATION include/pct_planner FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")
install(TARGETS ele_planner_lib a_star_search gpmp_optimizer map_manager common_smoothing
  LIBRARY DESTINATION lib ARCHIVE DESTINATION lib)
ament_export_include_directories(include/pct_planner)
ament_export_libraries(ele_planner_lib a_star_search gpmp_optimizer map_manager common_smoothing)
ament_export_dependencies(Eigen3 GTSAM)
install(FILES LICENSE NOTICE DESTINATION share/${PROJECT_NAME})
ament_package()

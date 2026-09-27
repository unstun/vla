set -e
source /opt/ros/humble/setup.bash
g++ -std=c++17 -O2 -I/usr/include/eigen3 -I/workspace/src/plan_manage/include -I/workspace/src/bspline_opt/include /version/test_minimum_cruise.cpp /workspace/src/bspline_opt/src/uniform_bspline.cpp -o /attempt/cruise_test
/attempt/cruise_test /version/recorded_curves.txt

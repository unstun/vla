set -e
. /opt/ros/humble/setup.sh
mkdir -p /task/workspace/src /task/results
cp -a /native/src/. /task/workspace/src/
cd /task/workspace
colcon build --base-paths src --packages-up-to plan_env --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF > /task/results/native_build.log 2>&1
. install/setup.sh
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v84 -B /task/workspace/v84_probe -DCMAKE_BUILD_TYPE=Release > /task/results/probe_build.log 2>&1
cmake --build /task/workspace/v84_probe -j2 >> /task/results/probe_build.log 2>&1
printf 'V84_NATIVE_BUILD_PASSED\n'

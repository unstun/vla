set -e
. /opt/ros/humble/setup.sh
. /task/workspace/install/setup.sh
versions=/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions
cmake -S "$versions/v84" -B /task/workspace/v84_probe -DCMAKE_BUILD_TYPE=Release > /task/results/additional_probe_build.log 2>&1
cmake --build /task/workspace/v84_probe -j2 >> /task/results/additional_probe_build.log 2>&1
cmake -S "$versions/v85" -B /task/workspace/v85_probe -DCMAKE_BUILD_TYPE=Release >> /task/results/additional_probe_build.log 2>&1
cmake --build /task/workspace/v85_probe -j2 >> /task/results/additional_probe_build.log 2>&1
printf 'V85_AND_TRANSIENT_BUILD_PASSED\n'

set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
mkdir -p /attempt/replay
ln -s /archive/audits/2026-10-02_v52_corner_43s/attempt05/replay/events.bin /attempt/replay/events.bin
cmake -S /profile -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1
cmake --build /attempt/probe_build -j2 >> /attempt/build.log 2>&1
stdbuf -oL /attempt/probe_build/tail_replay --ros-args --params-file /version/building_planner.yaml --params-file /version/controller.yaml > /attempt/replay.log 2>&1

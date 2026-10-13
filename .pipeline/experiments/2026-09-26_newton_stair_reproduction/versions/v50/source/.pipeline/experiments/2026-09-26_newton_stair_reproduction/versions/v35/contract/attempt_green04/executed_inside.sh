set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /contract -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release -DLEGACY_PARENT=${V35_LEGACY_PARENT:-OFF} > /attempt/build.log 2>&1
cmake --build /attempt/probe_build -j2 >> /attempt/build.log 2>&1
/attempt/probe_build/periodic_probe --ros-args --params-file /config/planner.yaml > /attempt/probe.log 2>&1
if [ "${V35_LEGACY_PARENT:-OFF}" != "ON" ]; then
  V35_EXPECT_FREQUENCY=0 /attempt/probe_build/periodic_probe --ros-args --params-file /config/parent.yaml > /attempt/omitted_frequency.log 2>&1
  for invalid in -1 nan inf 101 1e-310; do
    V35_INVALID_FREQUENCY=$invalid /attempt/probe_build/periodic_probe --ros-args --params-file /config/planner.yaml > /attempt/invalid_${invalid}.log 2>&1
  done
fi

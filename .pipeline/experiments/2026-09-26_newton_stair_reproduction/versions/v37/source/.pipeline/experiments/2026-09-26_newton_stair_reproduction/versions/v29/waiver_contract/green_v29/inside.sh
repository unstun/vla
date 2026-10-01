set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /contract -B /attempt/build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1
cmake --build /attempt/build -j2 --target waiver_contract >> /attempt/build.log 2>&1
set +e
env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_CONTRACT_INPUT=/archive/audits/2026-09-28_v28_start_thrash/stopped/inputs VLA_CONTRACT_OUTPUT=/attempt/stopped.json /attempt/build/waiver_contract --ros-args --params-file /version/building_planner.yaml > /attempt/stopped.log 2>&1
echo $? > /attempt/stopped_exit_code.txt
set -e
set +e
env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_CONTRACT_INPUT=/archive/audits/2026-09-28_v28_start_thrash/height_sweep/z_0p3650/inputs VLA_CONTRACT_OUTPUT=/attempt/z_0p3650.json /attempt/build/waiver_contract --ros-args --params-file /version/building_planner.yaml > /attempt/z_0p3650.log 2>&1
echo $? > /attempt/z_0p3650_exit_code.txt
set -e
set +e
env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_CONTRACT_INPUT=/archive/audits/2026-09-28_v28_start_thrash/control/inputs VLA_CONTRACT_OUTPUT=/attempt/control.json /attempt/build/waiver_contract --ros-args --params-file /version/building_planner.yaml > /attempt/control.log 2>&1
echo $? > /attempt/control_exit_code.txt
set -e

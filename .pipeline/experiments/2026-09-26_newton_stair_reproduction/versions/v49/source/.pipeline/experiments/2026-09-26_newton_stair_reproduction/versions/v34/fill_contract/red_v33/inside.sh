set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /contract -B /attempt/build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1
cmake --build /attempt/build -j2 >> /attempt/build.log 2>&1
set +e
/attempt/build/fill_contract /version/fill_contract/cases.txt /archive/audits/2026-09-27_pct_precision/ground_precise.f32 /archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 /attempt > /attempt/fill.log 2>&1
echo $? > /attempt/fill_exit_code.txt
env VLA_ORDER=nav_first VLA_NAVIGATION_GROUND=/archive/audits/2026-09-27_pct_precision/ground_precise.f32 VLA_SURFACE_EVIDENCE=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_CONTRACT_OUTPUT=/attempt/order_nav_first.json /attempt/build/fill_order_contract --ros-args --params-file /version/building_planner.yaml > /attempt/order_nav_first.log 2>&1
echo $? > /attempt/order_nav_first_exit_code.txt
env VLA_ORDER=evidence_first VLA_NAVIGATION_GROUND=/archive/audits/2026-09-27_pct_precision/ground_precise.f32 VLA_SURFACE_EVIDENCE=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_CONTRACT_OUTPUT=/attempt/order_evidence_first.json /attempt/build/fill_order_contract --ros-args --params-file /version/building_planner.yaml > /attempt/order_evidence_first.log 2>&1
echo $? > /attempt/order_evidence_first_exit_code.txt
set -e

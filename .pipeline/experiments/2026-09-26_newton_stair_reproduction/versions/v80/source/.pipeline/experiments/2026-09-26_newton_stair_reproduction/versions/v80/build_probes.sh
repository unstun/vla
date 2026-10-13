set -e
source /opt/ros/humble/setup.bash
mkdir -p /task/baseline
tar -xzf /task/native_runtime.tar.gz -C /task/baseline
source /task/workspace/v80/install/setup.bash
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v80 -B /task/workspace/v80/map_probe_build -DCMAKE_BUILD_TYPE=Release > /task/results/v80_probe_build.log 2>&1
cmake --build /task/workspace/v80/map_probe_build -j2 >> /task/results/v80_probe_build.log 2>&1
export V80_INPUT=/task/prepared_inputs ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1
for repeat in 1 2 3; do
  for mode in baseline optimized; do
    export V80_OUTPUT=/task/results/v80_${mode}_${repeat}.jsonl
    if [ "$mode" = baseline ]; then
      LD_LIBRARY_PATH=/task/baseline/install/plan_env/lib:/task/baseline/install/traj_utils/lib:${LD_LIBRARY_PATH:-} /task/workspace/v80/map_probe_build/${mode}_map_probe --ros-args --params-file /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v80/building_planner.yaml > /task/results/v80_${mode}_${repeat}.log 2>&1
    else
      /task/workspace/v80/map_probe_build/${mode}_map_probe --ros-args --params-file /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v80/building_planner.yaml > /task/results/v80_${mode}_${repeat}.log 2>&1
    fi
  done
done
for mode in baseline optimized; do
  export V80_OUTPUT=/task/results/v80_${mode}_synthetic.jsonl V80_SYNTHETIC=1
  if [ "$mode" = baseline ]; then
    LD_LIBRARY_PATH=/task/baseline/install/plan_env/lib:/task/baseline/install/traj_utils/lib:${LD_LIBRARY_PATH:-} /task/workspace/v80/map_probe_build/${mode}_map_probe --ros-args --params-file /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v80/building_planner.yaml > /task/results/v80_${mode}_synthetic.log 2>&1
  else
    /task/workspace/v80/map_probe_build/${mode}_map_probe --ros-args --params-file /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v80/building_planner.yaml > /task/results/v80_${mode}_synthetic.log 2>&1
  fi
done

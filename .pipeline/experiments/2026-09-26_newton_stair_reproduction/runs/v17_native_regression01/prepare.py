"""Version-bound native replay with explicit mode restoration assertions."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
old=BASE/'runs/v15_native_continuation01'
new=BASE/'audits/2026-09-27_v15_optimizer_collision'
(HERE/'probe_source/src').mkdir(parents=True)
shutil.copyfile(old/'probe_source/src/frontier_probe.cpp',HERE/'probe_source/src/legacy_probe.cpp')
shutil.copyfile(new/'probe_source/src/frontier_probe.cpp',HERE/'probe_source/src/moving_probe.cpp')
shutil.copyfile(BASE/'versions/v5/regression_probe/src/measured_cloud_probe.cpp',HERE/'probe_source/src/height_probe.cpp')
shutil.copyfile(new/'physical_ground.f32',HERE/'physical_ground.f32')
for name in ['legacy_probe.cpp','moving_probe.cpp']:
 p=HERE/'probe_source/src'/name;s=p.read_text();anchor='result.close();rclcpp::shutdown();'
 if anchor not in s:
  anchor='rclcpp::shutdown();'
 suffix='''
  if(!fsm.planner_manager_->bspline_optimizer_rebound_->optimizesHeight())
    throw std::runtime_error("Configured height mode leaked after complete planner calls");
  std::cout << "[RECOVERY-STATE] configured_height_mode_restored=1" << std::endl;
  '''
 assert s.count(anchor)==1;s=s.replace(anchor,suffix+anchor)
 if name=='moving_probe.cpp':
  anchor='''      if(progress) planned=fsm.planner_manager_->reboundReplan(original_start,expected_velocity,expected_acceleration,
          selected,Eigen::Vector3d::Zero(),true,false);'''
  replacement='''      if(progress) {
        const int before=fsm.planner_manager_->continuous_failures_count_;
        const auto trajectory_before=fsm.planner_manager_->local_data_.traj_id_;
        planned=fsm.planner_manager_->reboundReplan(original_start,expected_velocity,expected_acceleration,
          selected,Eigen::Vector3d::Zero(),true,false);
        if(!fsm.planner_manager_->bspline_optimizer_rebound_->optimizesHeight() ||
           (!planned && fsm.planner_manager_->continuous_failures_count_!=before+1) ||
           (planned && fsm.planner_manager_->continuous_failures_count_!=0) ||
           (!planned && fsm.planner_manager_->local_data_.traj_id_!=trajectory_before))
          throw std::runtime_error("Recovery state/count/publication contract failed");
        std::cout << "[RECOVERY-STATE] outcome=" << planned << " mode_restored=1 failure_count_ok=1 failed_publication_unchanged=1" << std::endl;
      }'''
  assert s.count(anchor)==1;s=s.replace(anchor,replacement)
 p.write_text(s)
cm=(old/'probe_source/CMakeLists.txt').read_text()
start=cm.index('add_executable(')
cm=cm[:start]+'''add_library(native_manager OBJECT /workspace/src/plan_manage/src/scan_replan_fsm.cpp /workspace/src/plan_manage/src/planner_manager.cpp)
target_include_directories(native_manager PRIVATE /workspace/src/plan_manage/include)
ament_target_dependencies(native_manager ${dependencies})
target_link_libraries(native_manager Eigen3::Eigen)
foreach(target legacy_probe moving_probe height_probe)
 add_executable(${target} src/${target}.cpp $<TARGET_OBJECTS:native_manager>)
 target_include_directories(${target} PRIVATE /workspace/src/plan_manage/include)
 target_compile_options(${target} PRIVATE -fno-access-control)
 ament_target_dependencies(${target} ${dependencies})
 target_link_libraries(${target} Eigen3::Eigen)
endforeach()
ament_package()
'''
(HERE/'probe_source/CMakeLists.txt').write_text(cm)
shutil.copyfile(old/'probe_source/package.xml',HERE/'probe_source/package.xml')
inside='''set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j2
ulimit -v 1500000
'''
for name,exe,inp,env in [('expired01','legacy','/expired',''),('original66','legacy','/original',''),('moving_selected','moving','/moving',''),('moving_physical','moving','/moving','VLA_DIAGNOSTIC_PHYSICAL_GROUND=1'),('moving_physical_repeat','moving','/moving','VLA_DIAGNOSTIC_PHYSICAL_GROUND=1')]:
 inside+=f'env {env} VLA_GEOMETRY_INPUT={inp} VLA_GEOMETRY_OUTPUT=/attempt/{name}.json /attempt/probe_build/{exe}_probe --ros-args --params-file /version/building_planner.yaml > /attempt/{name}.log 2>&1\n'
 if exe=='moving':inside+=f'mv /attempt/neighborhoods.json /attempt/{name}_neighborhoods.json\n'
height_inside=(BASE/'runs/v5_height_regression01/inside.sh').read_text()
(HERE/'v5_original_inside.sh').write_text(height_inside)
# Original v5 fixture arguments are added after reading its exact contract.
(HERE/'inside.sh').write_text(inside)
r=json.loads((old/'request.json').read_text());r['command']=[v.replace(str(old),str(HERE)).replace('scan52_riser_ground_v15','scan54_height_retry_v17').replace('/versions/v15:','/versions/v17:').replace('vla-v15-native-continuation01','vla-v17-native-regression01') for v in r['command']]
pos=r['command'].index('--entrypoint');r['command'][pos:pos]=['-v',str(BASE/'audits/2026-09-27_v15_moving_frontier/inputs')+':/moving:ro','-v',str(BASE/'audits/2026-09-27_v4_cause/frozen_map')+':/v5input:ro']
r['deadline_s']=450;r['expected']='Old continuations retained; new failure recorded; physical-ground diagnosis is not production; native manager mode/count/publication invariants'
(HERE/'request.json').write_text(json.dumps(r,indent=2)+'\n')
(HERE/'inputs_sha256.json').write_text(json.dumps({str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file()},indent=2)+'\n')

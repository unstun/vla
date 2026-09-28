from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];BUILD=BASE/'runtime/scan54_height_retry_v17'
source=HERE/'probe_source';(source/'src').mkdir(parents=True)
s=(BUILD/'src/geometry_probe/src/measured_cloud_probe.cpp').read_text();s=s.replace('#include <cstdlib>','#include <cstdlib>\n#include <cstring>\n#include <limits>')
anchor='  std::ifstream listing(root / "clouds.txt");'
insert='''  if(std::getenv("VLA_RAW_QUALIFIED") && fs::exists(root/"qualified_ground.f32")) {
    auto points=read_cloud(root/"qualified_ground.f32",true);
    reactive_stair::TerrainSnapshot raw=map->reactive_ground_;
    raw.cells.clear();raw.source_id="diagnostic_raw_cost_qualified";
    double minx=std::numeric_limits<double>::infinity(),miny=minx;
    for(size_t i=0;i<points.width;++i){float v[4];std::memcpy(v,points.data.data()+16*i,16);minx=std::min(minx,static_cast<double>(v[0]));miny=std::min(miny,static_cast<double>(v[1]));}
    raw.origin_x_m=minx-raw.resolution_m/2.;raw.origin_y_m=miny-raw.resolution_m/2.;
    for(size_t i=0;i<points.width;++i){float v[4];std::memcpy(v,points.data.data()+16*i,16);
      raw.cells[{static_cast<int>(std::floor((v[0]-raw.origin_x_m)/raw.resolution_m)),static_cast<int>(std::floor((v[1]-raw.origin_y_m)/raw.resolution_m))}].push_back({reactive_stair::Support::Stair,v[2]-map->reactive_tomogram_z_offset_m_});}
    map->reactive_ground_=std::move(raw);
  }
'''
assert s.count(anchor)==1;s=s.replace(anchor,insert+anchor);(source/'src/measured_cloud_probe.cpp').write_text(s)
cm=(BUILD/'src/geometry_probe/CMakeLists.txt').read_text();cm=cm.replace('ament_target_dependencies(measured_cloud_probe','target_compile_options(measured_cloud_probe PRIVATE -fno-access-control)\nament_target_dependencies(measured_cloud_probe');(source/'CMakeLists.txt').write_text(cm);shutil.copyfile(BUILD/'src/geometry_probe/package.xml',source/'package.xml')
inside='set -e\nsource /opt/ros/humble/setup.bash\nsource /workspace/install/setup.bash\ncmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release\ncmake --build /attempt/probe_build -j2\n'
for name in ['mapped_low_box','mapped_low_box_near_wall','mapped_box','mapped_short_wall','mapped_overhead']:
 for mode in ['selected','qualified']:
  env='VLA_RAW_QUALIFIED=1' if mode=='qualified' else ''
  inside+=f'env {env} VLA_GEOMETRY_INPUT=/attempt/{name} VLA_GEOMETRY_OUTPUT=/attempt/{name}_{mode}.json /attempt/probe_build/measured_cloud_probe --ros-args --params-file /version/building_planner.yaml > /attempt/{name}_{mode}.log 2>&1\n'
for name in ['empty','static_human','box','thin_wall','post','low_box','occluded_human','blocked_corridor']:
 inside+=f'env VLA_RAW_QUALIFIED=1 VLA_GEOMETRY_INPUT=/original/{name} VLA_GEOMETRY_OUTPUT=/attempt/unmapped_{name}.json /attempt/probe_build/measured_cloud_probe --ros-args --params-file /version/building_planner.yaml > /attempt/unmapped_{name}.log 2>&1\n'
(HERE/'inside.sh').write_text(inside)
cmd=['docker','run','--rm','--pull=never','--platform=linux/amd64','--network=none','--cpus=2','--memory=4g','--name','vla-pct-ground-negatives','-e','ROS_DOMAIN_ID=225','-e','ROS_LOCALHOST_ONLY=1','-v',str(BUILD)+':/workspace:ro','-v',str(BASE/'versions/v17')+':/version:ro','-v',str(BASE/'runs/generic_sensor_cases_v1')+':/original:ro','-v',str(HERE)+':/attempt:rw','--entrypoint','/bin/bash','sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb','/attempt/inside.sh']
(HERE/'request.json').write_text(json.dumps({'command':cmd,'deadline_s':240,'claim':'Diagnostic difference test of raw-cost qualification on mapped obstacles; all original eight cases retained'},indent=2)+'\n')

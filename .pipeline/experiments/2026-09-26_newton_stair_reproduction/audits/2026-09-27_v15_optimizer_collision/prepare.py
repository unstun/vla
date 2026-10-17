"""Instrument actual optimizer collisions; no production behavior change."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
prior=BASE/'audits/2026-09-27_v15_physical_ground'
heading=BASE/'audits/2026-09-27_v15_optimizer_heading'
shutil.copytree(prior/'probe_source',HERE/'probe_source')
shutil.copyfile(prior/'physical_ground.f32',HERE/'physical_ground.f32')
shutil.copyfile(heading/'probe_source/CMakeLists.txt',HERE/'probe_source/CMakeLists.txt')
(HERE/'optimizer').mkdir()
p=heading/'optimizer/bspline_optimizer.cpp'
s=p.read_text()
anchor='''          if (flag_occ)
          {
            //cout'''
replacement='''          if (flag_occ)
          {
            std::cout << std::setprecision(17) << "[OPT-COLLISION] restart=" << restart_nums
                << " time=" << t << " duration=" << tmp << " point=" << pos.transpose()
                << " ahead=" << pos_next.transpose() << " heading=" << estimateSegmentYaw(pos,pos_next) << std::endl;
            grid_map_->logInitialSplineCollision(pos,estimateSegmentYaw(pos,pos_next));
            for(int ci=0;ci<cps_.points.cols();++ci)
              std::cout << "[OPT-CONTROL] index=" << ci << " point=" << cps_.points.col(ci).transpose() << std::endl;
            //cout'''
assert s.count(anchor)==1
s=s.replace(anchor,replacement)
(HERE/'optimizer/bspline_optimizer.cpp').write_text(s)
p=HERE/'probe_source/src/frontier_probe.cpp';s=p.read_text()
a=s.index('  auto physical=');b=s.index('  std::ifstream listing',a)
s=s[:a]+'  if(std::getenv("VLA_DIAGNOSTIC_PHYSICAL_GROUND")){\n'+s[a:b]+'  }\n'+s[b:]
s=s.replace('if(path.size()>1) {','''if(path.size()>1) {
      for(size_t pi=0;pi<path.size();++pi)
        std::cout << std::setprecision(17) << "[NEIGHBOR-SEED] t=" << proposal_t << " i=" << pi << " point=" << path[pi].transpose() << std::endl;''')
p.write_text(s)
inside='''set -e
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cmake -S /attempt/probe_source -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release
cmake --build /attempt/probe_build -j1
'''
for name,env,args in [('selected','', ''),('physical','VLA_DIAGNOSTIC_PHYSICAL_GROUND=1',''),('physical_fixed_height','VLA_DIAGNOSTIC_PHYSICAL_GROUND=1',' -p optimization.optimize_height:=false')]:
 inside+=f'env {env} VLA_GEOMETRY_INPUT=/recorded/inputs VLA_GEOMETRY_OUTPUT=/attempt/{name}.json /attempt/probe_build/frontier_probe --ros-args --params-file /version/building_planner.yaml{args} > /attempt/{name}.log 2>&1\nmv /attempt/neighborhoods.json /attempt/{name}_neighborhoods.json\n'
(HERE/'inside.sh').write_text(inside)
request=json.loads((prior/'request.json').read_text());request['command']=[v.replace(str(prior),str(HERE)).replace('vla-v15-physical-ground','vla-v15-opt-collision') for v in request['command']];request['deadline_s']=300
request['claim']='Diagnostic-only optimizer collision evidence; fixed-height ablation; no source promotion'
(HERE/'request.json').write_text(json.dumps(request,indent=2)+'\n')
(HERE/'inputs_sha256.json').write_text(json.dumps({str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file()},indent=2)+'\n')

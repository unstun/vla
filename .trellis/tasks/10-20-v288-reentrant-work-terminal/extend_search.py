from pathlib import Path
import json,hashlib
b=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction');v=b/'versions/v288'
p=v/'src/path_searching/src/dyn_a_star.cpp';s=p.read_text();a=s.index('    if(terrain_search_) {');bpos=s.index('    Eigen::Vector3d start_to_end = end_pt - start_pt;',a)
s=s[:a]+'''    if(terrain_search_) {
      // Prefer one support-aligned endpoint. Endpoint quantization need not
      // prove an extra adjacent edge: the actual search edges do that below.
      const auto project=[&](const Vector3d &point,Vector3i &index) {
        Vector3d p=latticeCoord(index);p.z()=point.z();
        if(!grid_map_->terrainSupportHeight(p,p.z()) || !Coord2Index(p,index) || !poolIndexValid(index,true))return false;
        for(int dx=-1;dx<=1;++dx)for(int dy=-1;dy<=1;++dy) {
          if((dx||dy) && checkOccupancy(p,std::atan2(double(dy),double(dx)))==0) {
            terrain_points_[terrainKey(index)]=p;return true;
          }
        }
        return false;
      };
      if(project(start_pt,start_idx) && (goal_tolerance>0. || project(end_pt,end_idx)))return true;
      // SCAN's original chord/plane representation is a proposal fallback,
      // subject to the same occupancy, support, edge and downstream curve checks.
      terrain_search_=false;terrain_points_.clear();
      if(!Coord2Index(start_pt,start_idx) || !Coord2Index(end_pt,end_idx))return false;
    }

'''+s[bpos:]
s=s.replace('if(++attempts>2)return false;','if(++attempts>POOL_SIZE_.maxCoeff())return false;')
# Check the allocation bound before stepping, so fallback cannot index/log a
# fictitious out-of-pool node. Coord2Index is still used for legal proposals.
s=s.replace('''            start_pt -= start_to_end * step_size_;
            if (!Coord2Index(start_pt, start_idx))''','''            start_pt -= start_to_end * step_size_;
            if (((start_pt-center_)*inv_step_size_+CENTER_IDX_.cast<double>()).minCoeff()<1. ||
                (((start_pt-center_)*inv_step_size_+CENTER_IDX_.cast<double>()).array()>=(POOL_SIZE_-Vector3i::Ones()).cast<double>().array()).any())return false;
            if (!Coord2Index(start_pt, start_idx))''')
s=s.replace('''            end_pt += start_to_end * step_size_;
            if (!Coord2Index(end_pt, end_idx))''','''            end_pt += start_to_end * step_size_;
            if (((end_pt-center_)*inv_step_size_+CENTER_IDX_.cast<double>()).minCoeff()<1. ||
                (((end_pt-center_)*inv_step_size_+CENTER_IDX_.cast<double>()).array()>=(POOL_SIZE_-Vector3i::Ones()).cast<double>().array()).any())return false;
            if (!Coord2Index(end_pt, end_idx))''')
p.write_text(s)
p=v/'src/bspline_opt/src/bspline_optimizer.cpp';s=p.read_text().replace('      lbfgs_params.max_iterations = 200;','      lbfgs_params.max_iterations = 200;\n      lbfgs_params.past = 3;\n      lbfgs_params.delta = 1e-6;');assert s.count('lbfgs_params.past = 3;')==2;p.write_text(s)
(v/'source_inventory.json').write_text(json.dumps({str(p.relative_to(v)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((v/'src').rglob('*')) if p.is_file()},indent=2)+'\n')
t=Path('.trellis/tasks/10-20-v288-reentrant-work-terminal')
for name in ['prd.md','design.md','implement.md']:
 p=t/name;s=p.read_text();s+='\n## Latest authorized extension\nCompare pinned author SCAN348e8a590a50a5a6bbab8d8c6dcfd171f009be26 and PCT35cd73fd82bcd51bc538429294af7646b2a09815 source archives. Simplify terrain endpoint projection to one support-aligned candidate with safe heading, then permit the inherited chord/plane proposal fallback within pool bounds and unchanged full edge/trajectory checks. Keep terrain-aware search when projection succeeds. Enable past3/delta1e-6 function-decrease stopping in both optimizer stages, without replacing LBFGS or changing hard acceptance. Requalify affected binaries and all native tests before any scored freeze.\n';p.write_text(s)
print('AStar projection simplified and upstream proposal fallback enabled; optimizer past3/delta1e-6')

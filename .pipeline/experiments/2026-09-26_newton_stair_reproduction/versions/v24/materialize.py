"""Prepare the body-reference support repair without changing frozen v23."""
from pathlib import Path
import difflib,hashlib,json,shutil
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2]
P=B/'runtime/scan56_dense_ground_v23';N=B/'runtime/scan58_body_support_v24'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def replace(s,old,new):
 assert s.count(old)==1,old[:100]
 return s.replace(old,new)
def main():
 parent=json.loads((H.parent/'v23/manifest.json').read_text())
 assert not N.exists() and not (H/'prepared.json').exists()
 for name,digest in parent['source_files'].items():assert sha(R/name)==digest,name
 N.mkdir();shutil.copytree(P/'src',N/'src');before={}
 p=N/'src/plan_env/include/plan_env/grid_map.h';before[p]=p.read_bytes();s=before[p].decode()
 s=replace(s,'  int reactiveOccupancy(const Eigen::Vector3d &point);','  bool reactiveFootprintSupportQuery(const Eigen::Vector3d &body_reference,\n      const reactive_stair::NonTerrainVoxel &obstacle, reactive_stair::Query &query);\n  int reactiveOccupancy(const Eigen::Vector3d &point, const Eigen::Vector3d *body_reference = nullptr);')
 s=replace(s,'reactiveOccupancy(front) != 0','reactiveOccupancy(front, &pos) != 0')
 s=replace(s,'return reactiveOccupancy(rear);','return reactiveOccupancy(rear, &pos);');p.write_bytes(s.encode())
 p=N/'src/plan_env/include/plan_env/scan_reactive_grid_methods.inc';before[p]=p.read_bytes();s=before[p].decode()
 helper=(H/'support_query_method.inc').read_text()
 s=replace(s,'int GridMap::reactiveOccupancy(const Eigen::Vector3d &point) {',helper+'\nint GridMap::reactiveOccupancy(const Eigen::Vector3d &point, const Eigen::Vector3d *body_reference) {')
 for sign in ['+','-']:
  s=replace(s,f'reactiveOccupancy(pos {sign} mp_.double_cylinder_offset_ * heading);',f'reactiveOccupancy(pos {sign} mp_.double_cylinder_offset_ * heading, &pos);')
 s=replace(s,'  const auto verdict = reactive_decision_.decide(query, obstacle);','  if (body_reference && !reactiveFootprintSupportQuery(*body_reference, obstacle, query)) return 1;\n  const auto verdict = reactive_decision_.decide(query, obstacle);')
 s=replace(s,'reactive_collision_blocked verdict=%d voxel=%d q=(%.3f,%.3f,%.3f) now=', 'reactive_collision_blocked verdict=%d voxel=%d q=(%.3f,%.3f,%.3f) support_z=%.3f now=')
 s=replace(s,'query.x_m, query.y_m, query.z_m, query.stamp_s, obstacle.stamp_s,','point.x(), point.y(), point.z(), query.z_m, query.stamp_s, obstacle.stamp_s,');p.write_bytes(s.encode())
 for p,raw in before.items():
  q=H/'parent_source'/p.relative_to(N);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
 patch=''.join(''.join(difflib.unified_diff(raw.decode().splitlines(True),p.read_bytes().decode().splitlines(True),fromfile='v23/'+str(p.relative_to(N)),tofile='v24/'+str(p.relative_to(N)))) for p,raw in before.items())
 (H/'changes.patch').write_bytes(patch.encode())
 native={str(p.relative_to(N)):sha(p) for p in sorted((N/'src').rglob('*')) if p.is_file()};(N/'source_sha256.json').write_text(json.dumps(native,indent=2)+'\n')
 identity=B/'repairs/2026-09-26_generic_occupancy/candidate58_body_support_v24_identity.json';identity.write_text(json.dumps({'source_sha256':native,'integration_version':'v24','claim':'Unvalidated body-reference terrain-support query repair; raw obstacle geometry and all parameters unchanged.'},indent=2)+'\n')
 for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(H.parent/'v23'/name,H/name)
 (H/'prepared.json').write_text(json.dumps({'parent':'v23','status':'unfrozen_candidate','native_build':str(N.relative_to(R)),'changed_files':[str(p.relative_to(R)) for p in before]+[str(identity.relative_to(R))]},indent=2)+'\n')
 print('v24 candidate prepared; acceptance pending')
if __name__=='__main__':main()

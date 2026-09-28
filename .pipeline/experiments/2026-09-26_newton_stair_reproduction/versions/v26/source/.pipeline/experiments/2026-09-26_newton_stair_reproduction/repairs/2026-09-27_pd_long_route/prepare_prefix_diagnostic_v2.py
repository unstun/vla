"""Hash-gated diagnostic copy; planner behavior and source baseline unchanged."""
from pathlib import Path
import hashlib, importlib.util, json, shutil
BASE=Path(__file__).resolve().parents[2]
source=BASE/'runtime/scan42_geometry_v9';target=BASE/'runtime/scan43_prefix_diagnostic_v2'
for name in ('source_sha256.json','install_sha256.json'):
 for p,h in json.loads((source/name).read_text()).items():
  if hashlib.sha256((source/p).read_bytes()).hexdigest()!=h:raise ValueError('Baseline changed')
target.mkdir(exist_ok=False)
for name in ('src','build','install'):shutil.copytree(source/name,target/name,symlinks=True)
p=target/'src/plan_manage/src/scan_replan_fsm.cpp';data=p.read_bytes()
anchor=b'    double candidate_t = local_target_time_;\n'
new=anchor+b'''    RCLCPP_WARN(node_->get_logger(), "[DEBUG-prefix-01] reference=%d remaining=%d local=%.12f projection=%.12f frontier=%.12f", reference, remaining, local_target_time_, local_projection_time_, reference_frontier_time_);
'''
assert data.count(anchor)==1;data=data.replace(anchor,new)
anchor=b'      const double yaw = estimateYawFromSegment(odom_pos_, candidate);\n'
new=anchor+b'''      RCLCPP_WARN(node_->get_logger(), "[DEBUG-prefix-01] candidate t=%.12f xyz=[%.12f,%.12f,%.12f] yaw=%.12f occ=%d", candidate_t,candidate.x(),candidate.y(),candidate.z(),yaw,planner_manager_->grid_map_->getInflateOccupancy(candidate,yaw));
      if (candidate_t > 0.9 && candidate_t < 1.2) {
        planner_manager_->grid_map_->logInitialSplineCollision(start_pt_, yaw);
        planner_manager_->grid_map_->logInitialSplineCollision(start_pt_ + Eigen::Vector3d(0.05,0,0), yaw);
      }
'''
assert data.count(anchor)==1;p.write_bytes(data.replace(anchor,new))
manifest={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (target/'src').rglob('*') if p.is_file()}
(target/'source_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
identity={'source_sha256':manifest,'baseline':str(source),'change':'Diagnostic prefix proposals only; no algorithm change'}
(BASE/'repairs/2026-09-26_generic_occupancy/candidate43_prefix_diagnostic_v2_identity.json').write_text(json.dumps(identity,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('prefix_build',BASE/'setup/build_scan_local.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.WORKSPACE=target;m.NAME='vla-scan43-prefix-build-v2';m.main()

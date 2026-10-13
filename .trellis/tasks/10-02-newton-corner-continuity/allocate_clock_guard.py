from pathlib import Path
import json,shutil,hashlib
T=Path('.trellis/tasks');parent=T/'10-02-newton-corner-continuity';G=T/'10-02-newton-v54-warm-clock-guard';G.mkdir()
old=json.loads((T/'10-02-newton-v54-recovery-freshness/task.json').read_text());g=dict(old);g.update(id='newton-v54-warm-clock-guard',name='newton-v54-warm-clock-guard',title='Reject uninitialized or incompatible warm-curve clocks before subtraction',status='planning',notes='Required by actual native v53 DDS red replay: repeated qualified refresh before first accepted curve throws on mixed clock types. Frozen v53 remains immutable.');g['meta']={'planned_version':'v54','planned_parent':'v53','depends_on':'qualified frozen v53 with recorded clock defect'};(G/'task.json').write_text(json.dumps(g,indent=2)+'\n')
(G/'prd.md').write_text('# v54 warm binding clock guard\n\nAuthorized within the reviewed parent plan: a frozen-stage defect requires the next integer. Native v53 freshness/red01 reproduced a mixed-clock exception on repeated pre-trajectory route refresh. Reject absent/unowned or clock-incompatible local curves before subtracting timestamps. Keep all valid-curve behavior, deadlines and stop protocol unchanged. Native build, new pre-trajectory/mixed-clock regressions, inherited safety/callback/warm/backend gates and corner continuity replay must pass.\n')
(G/'design.md').write_text('# Design\n\nAdd only an early trajectory-ID/accepted-ID/clock-type precondition in canPreserveReferenceBinding(), before its existing time subtraction. No binding or curve mutation. Qualified reference refresh follows legacy invalidation when no valid accepted source exists. v53 frozen bytes and the actual failure remain recorded.\n')
(G/'implement.md').write_text('# Execution\n\nImplement guard in v54 parented to frozen v53. Build and run the actual DDS pre-trajectory path that threw in v53, plus explicit initial-ID and incompatible-clock negative contracts. Run inherited gates and corner replay; review/freeze component. Then D2 becomes v55 parent v54; D3 becomes v56 parent v55. Physics/30 Hz/reserve scoring remains the original parent integration gate.\n')
for n in ['implement.jsonl','check.jsonl','research.jsonl']:
 (G/n).write_text('')
for slug,ver,par in [('10-02-newton-v54-recovery-freshness','v55','v54'),('10-02-newton-v55-floor-presence','v56','v55')]:
 p=T/slug/'task.json';r=json.loads(p.read_text());r['status']='planning';r['meta'].update(planned_version=ver,planned_parent=par,depends_on=f'qualified frozen {par}');r['notes']=f'Renumbered after reproduced frozen-v53 clock defect: {ver} from {par}. Original approved behavior scope unchanged.';p.write_text(json.dumps(r,indent=2)+'\n')
 for name in ['prd.md','design.md','implement.md']:
  p=T/slug/name;s=p.read_text();s+='\n\n## Version allocation update 2026-10-02\n\n'+r['notes']+' See parent version-allocation record.\n';p.write_text(s)
for name in ['design.md','implement.md','prd.md']:
 p=parent/name;hist=parent/'research'/('approved_'+name);shutil.copyfile(p,hist)
 p.write_text(p.read_text()+'\n\n## Version allocation update 2026-10-02\n\nFrozen v53 passes its declared component suite but actual DDS pre-trajectory replay exposes a mixed-clock exception. Preserve that failure. Chain is v52 -> v53 -> v54 (clock guard) -> v55 (D2 freshness) -> v56 (D3 physical floor). Original behavior scope and final physics gates are unchanged.\n')
p=parent/'task.json';r=json.loads(p.read_text());r.setdefault('children',[]).append(G.name);r['notes']='Approved plan executing; reproduced frozen-v53 pre-trajectory clock defect adds v54 guard. D2 v55; D3 v56. Integrated physics/reserve/30 Hz pending.';p.write_text(json.dumps(r,indent=2)+'\n')
B=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction');V=B/'versions/v54'
# Move the still-unimplemented freshness harness out of v54-owned frozen source.
F=parent/'research/freshness_harness';F.mkdir();shutil.move(str(V/'freshness'),str(F/'freshness'));shutil.move(str(V/'contract/freshness_probe.cpp'),str(F/'freshness_probe.cpp'))
(V/'PLAN.md').write_text((G/'prd.md').read_text());
p=B/'runtime/scan76_recovery_freshness_v54/src/plan_manage/src/scan_replan_fsm.cpp';s=p.read_text();s=s.replace('    const double age = (node_->now() - curve.start_time_).seconds();','''    const auto now = node_->now();
    if (curve.traj_id_ < 1 || binding.trajectory_id != curve.traj_id_ ||
        now.get_clock_type() != curve.start_time_.get_clock_type()) return false;
    const double age = (now - curve.start_time_).seconds();''',1);p.write_text(s)
# Explicit actual-native negatives; no time arithmetic may occur in these branches.
p=V/'contract/reference_refresh_checks.inc';s=p.read_text();marker='  restore();fsm.feasible_window_.endpoint_world=Eigen::Vector3d::Constant(1000.0);'
s=s.replace(marker,'''  restore();manager.local_data_.traj_id_=0;manager.local_data_.start_time_=rclcpp::Time(0,RCL_SYSTEM_TIME);
  require(!fsm.canPreserveReferenceBinding(),"no_accepted_curve_rejects_before_clock_arithmetic");
  restore();manager.local_data_.start_time_=rclcpp::Time(node->now().nanoseconds(),RCL_SYSTEM_TIME);
  require(!fsm.canPreserveReferenceBinding(),"incompatible_clock_type_rejects_before_subtraction");
'''+marker);p.write_text(s)
N=B/'runtime/scan76_recovery_freshness_v54';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(N/'source_sha256.json').write_text(json.dumps({str(p.relative_to(N)):sha(p) for p in (N/'src').rglob('*') if p.is_file()},indent=2)+'\n')
(B/'versions/v53/POST_FREEZE_FINDING.md').write_text('# Frozen v53 post-freeze defect\n\nNative DDS regression versions/v54/freshness/red01 (remote only) throws "can\'t subtract times with different time sources [1 != 2]" while replaying repeated qualified route callbacks before an accepted local curve was initialized. canPreserveReferenceBinding computed age before rejecting traj_id=0. The frozen v53 source/manifest/component results are unchanged. v54 adds a separate early ID/clock guard; D2 and D3 move to v55/v56. This does not invalidate the passing post-refresh accepted-curve fixture, but precludes treating v53 as generally navigation-validated.\n')
print(json.dumps({'allocated_clock_guard':'v54','freshness':'v55','floor':'v56','frozen_v53_unchanged':True}))

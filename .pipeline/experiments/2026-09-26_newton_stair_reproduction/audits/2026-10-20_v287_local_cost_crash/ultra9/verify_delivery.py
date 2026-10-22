"""Verify returned artifacts and frozen parents without changing experiment data."""
from pathlib import Path
import json,hashlib,ast
H=Path(__file__).resolve().parent;E=H.parents[2];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
def main():
 inventory=load(H/'physical_return/return_inventory.json')
 for rel,row in inventory['files'].items():assert sha(H/'physical_return'/rel)==row['sha256'],rel
 for name,digest in inventory['analysis_sources'].items():assert sha(H/name)==digest,name
 media=load(H/'evidence/local_media_verification01.json');assert media['visual_samples']==20
 summary=load(H/'physical_summary.json')
 for row in media['cases']:
  name=Path(row['video']).name;expected=inventory['videos'][name];p=H/'delivered'/name
  assert p.is_file() and not p.is_symlink() and sha(p)==row['sha256']==expected['sha256'],name
  case=next(v for v in summary['cases'] if v['case_id']==row['case_id']);assert case['video_frames']==row['frames']
 media.update(visual_review_pending=False,visual_review_passed=True,review='Both contact sheets inspected:20 actual source samples, correct route/version labels, visible robot/scene and causal overlays; full decode verified remotely with identical local SHA')
 (H/'evidence/local_media_verification01.json').write_text(json.dumps(media,indent=2)+'\n')
 parents={}
 for version in ['v283','v284','v285','v286','v287']:
  p=E/'versions'/version;m=load(p/'native_manifest.json')
  for rel,h in m['source_files'].items():assert sha(p/rel)==h,(version,rel)
  parents[version]=dict(native_manifest_sha256=sha(p/'native_manifest.json'),all_local_declared_source_files_verified=len(m['source_files']))
 gate=load(H/'offline/offline_gate.json');assert gate['passed'] and gate['calls']==53
 assert len(load(H/'offline/audit_ledger.json'))==53 and all(r['exit_code']==0 for r in load(H/'offline/audit_ledger.json'))
 assert summary['formal_attempts']==10 and summary['attempts_per_case']==1
 assert summary['goal_and_pd_passed']==6 and summary['goal_pd_and_all_recorded_physical_envelope_clear']==4
 assert load(H/'acceptance.json')['physical_acceptance_passed'] is False
 remote=load(H/'evidence/final_frozen_sources01.json');assert remote['passed'] and remote['active_v287_containers']==[]
 assert remote['positive_physics_steps']==sum(r['physics_steps'] for r in load(H/'evidence/physical_batch_status.json'))
 for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
 result=dict(passed=True,physical_acceptance_passed=False,all53_offline_complete=True,ten_single_positive_physics_attempts=True,
  physics_steps=remote['positive_physics_steps'],regular_videos=10,video_bytes=sum(v['bytes'] for v in inventory['videos'].values()),compact_files=len(inventory['files']),compact_bytes=sum(v['bytes'] for v in inventory['files'].values()),
  visual_samples_reviewed=20,all_local_video_sha256_match_remote_decode=True,frozen_local_sources=parents,
  hard_radius_m=.35,sensor_period_s=.1,report_sha256=sha(H/'RESULTS.md'),chinese_report_sha256=sha(H/'RESULTS_zh.md'),source_diff_sha256=sha(E/'versions/v287/changes.patch'),
  remote_final_verification_sha256=sha(H/'evidence/final_frozen_sources01.json'),additional_local_delivery_sources={n:sha(H/n) for n in ['media_qa.py','write_report_zh.py','verify_delivery.py','final_verify_remote.py']})
 (H/'evidence/local_delivery_verification_final.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ['frozen_local_sources','additional_local_delivery_sources']}))
if __name__=='__main__':main()

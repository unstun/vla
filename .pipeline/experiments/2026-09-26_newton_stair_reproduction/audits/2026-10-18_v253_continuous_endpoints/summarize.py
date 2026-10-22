"""Summarize completed source-bound physical attempts; preserve failed denominators."""
from pathlib import Path
import csv,json,math
HERE=Path(__file__).resolve().parent
raw=json.loads((HERE/'results/raw_pose_audit01/summary.json').read_text());rows=[]
for cid in ('A02',):
 root=HERE/'physical'/cid/'results';read=lambda n:json.loads((root/n).read_text())
 outcome=read('outcome.json');route=read('full_route_verification.json');metrics=read('metrics.json')
 window=read('window_audit.json');nav=window['windows']['navigation_since_goal_request'];stair=window['windows'].get('cross_floor_transition')
 scan=read('scanner_timing_summary.json');pd=read('terminal_pd_hold.json');p=metrics['planning']
 rows.append(dict(case_id=cid,formal_attempts=1,overall_result=outcome['overall_result'],terminal_status=outcome['terminal_status'],
  recording_end_physics_s=outcome['physics_duration_s'],first_arrived_s=window['first_arrived_observation_physics_s'],
  local_successes=nav['successful_rounds'],local_completed=nav['completed_rounds'],
  local_success_percent=100*nav['successful_rounds']/nav['completed_rounds'] if nav['completed_rounds'] else None,
  local_successful_wall_hz=p.get('successful_wall_hz'),local_maximum_solve_ms=p['solve_ms'].get('maximum',p['solve_ms'].get('max')),
  nav_pauses_ge_05s=nav['measured']['count_ge_05s'],nav_pauses_ge_1s=nav['measured']['count_ge_1s'],
  stair_window_s=stair['measured']['window_s'] if stair else None,
  stair_pauses_ge_05s=stair['measured']['count_ge_05s'] if stair else None,
  stair_pauses_ge_1s=stair['measured']['count_ge_1s'] if stair else None,
  nav_min_gap_aware_ENV_edge_m=nav['edge_margin']['minimum_m'],
  nav_min_raw_solid_margin_m=raw['cases'][cid]['navigation_since_goal_request']['minimum_raw_solid_margin_m'],
  nav_static_free=nav['native_static_support']['free'],nav_static_samples=nav['native_static_support']['samples'],
  nav_emergency_publications=len(nav['emergency_times_s']),terminal_pd_passed=pd['passed'],terminal_pd_duration_s=pd['duration_s'],
  final_xy_error_m=route.get('final_xy_error_m'),final_height_error_m=route.get('final_height_error_m'),
  scanner_completed=scan['completed'],scanner_deadline_failures=scan['deadline_failures'],scanner_max_total_ms=scan['maximum_total_ms'],
  source_full_qualification=metrics['full_qualification'],source_sustained_30hz=metrics['sustained_30hz_validated']))
summary=dict(native='v254',execution='v255',formal_attempts=1,full_route_passed=sum(r['overall_result']=='PASSED' for r in rows),rows=rows,
 scanner_total=sum(r['scanner_completed'] for r in rows),scanner_deadline_failures=sum(r['scanner_deadline_failures'] for r in rows),
 baseline_unchanged='v232/v233',claim='One A02 physical regression; G07/R11 physical controls remain v252, not reruns on this source')
(HERE/'results/SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
with (HERE/'results/SUMMARY.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
print(json.dumps(summary),flush=True)

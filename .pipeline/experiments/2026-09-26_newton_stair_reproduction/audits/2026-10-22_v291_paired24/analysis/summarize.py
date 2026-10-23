"""Compare all24 fixed slots; never turn missing/censored stop data into success."""
from pathlib import Path
import argparse,json,statistics

def median(values):return statistics.median(values) if values else None

def summarize(data):
 assert data['full_geometry'] and len(data['runs'])==24
 rows=data['runs'];assert len({(r['variant'],r['case_id'],r['repeat']) for r in rows})==24
 groups={}
 for case in ('D07','CD12','S04','A04'):
  groups[case]={}
  for version in ('v290','v291'):
   band=[r for r in rows if r['case_id']==case and r['variant']==version];assert len(band)==3
   first=[r['stop']['first'] for r in band if r['stop'].get('first')]
   completed=[e for e in first if not e['pd_entry_censored']]
   last=[next((e for e in reversed(r['stop']['episodes']) if not e['pd_entry_censored']),None) for r in band];last=[e for e in last if e is not None]
   groups[case][version]={'successes':sum(r['success'] for r in band),'arrival_and_pd':sum(r['arrival_and_pd'] for r in band),
    'first_stop_observed_n':len(first),'first_stop_completed_n':len(completed),'first_stop_censored_n':len(first)-len(completed),
    'first_pd_entry_observed_n':len(completed),'first_fixed_stand_observed_n':sum(e['fixed_stand_s'] is not None for e in first),
    'first_stop_observed_median_cm':median([e['max_displacement_cm'] for e in first]),
    'first_completed_stop_median_cm':median([e['max_displacement_cm'] for e in completed]),
    'worst_episode_median_cm':median([r['stop']['worst_episode_cm'] for r in band if r['stop'].get('worst_episode_cm') is not None]),
    'last_completed_stop_median_cm':median([e['max_displacement_cm'] for e in last]),
    'last_completed_stop_n':len(last),'first_completed_pd_delay_median_s':median([e['pd_delay_s'] for e in completed]),
    'restarts_total':sum(r['stop'].get('restart_count',0) for r in band),
    'pd_aborts_total':sum(r.get('terminal_pd_aborts',0) for r in band),
    'scanner_deadline_failures':sum(r['scanner_deadline_failures'] for r in band),
    'completion_wall_median_s':median([r['nav_complete_wall_s'] for r in band if r['nav_complete_wall_s'] is not None]),
    'completion_wall_n':sum(r['nav_complete_wall_s'] is not None for r in band)}
 totals={v:sum(r['success'] for r in rows if r['variant']==v) for v in ('v290','v291')}
 a=groups['A04'];old=a['v290']['completion_wall_median_s'];new=a['v291']['completion_wall_median_s'];slowdown=(new/old-1) if old is not None and new is not None else None
 gate={'candidate_success_min10':totals['v291']>=10,'gain_min3':totals['v291']-totals['v290']>=3,'a04_three_successes':a['v291']['successes']==3,'a04_wall_slowdown_max15pct':slowdown is not None and slowdown<=.15}
 pair_rows=[]
 for case in groups:
  for repeat in (1,2,3):
   b={v:next(r for r in rows if r['case_id']==case and r['repeat']==repeat and r['variant']==v) for v in ('v290','v291')}
   old=b['v290']['stop'].get('first');new=b['v291']['stop'].get('first');matched=old is not None and new is not None and not old['pd_entry_censored'] and not new['pd_entry_censored']
   pair_rows.append({'case_id':case,'repeat':repeat,'parent_success':b['v290']['success'],'candidate_success':b['v291']['success'],
     'both_first_stops_complete':matched,'first_complete_drift_delta_cm':new['max_displacement_cm']-old['max_displacement_cm'] if matched else None,
     'observed_worst_delta_cm':b['v291']['stop']['worst_episode_cm']-b['v290']['stop']['worst_episode_cm'] if all(b[v]['stop'].get('worst_episode_cm') is not None for v in b) else None})
 return dict(physical_runs=24,totals=totals,case_groups=groups,paired=pair_rows,a04_slowdown_fraction=slowdown,first_review_gate=gate,first_review_passed=all(gate.values()),
             claim='Three fresh repeats per route and version on one shared host. Legacy completed-stop fields mean PD entry was observed within that episode, not that final PD or full-route success passed. Censored observations and missing stops remain distinct. No new-map or hardware claim.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=summarize(json.loads(a.input.read_text()));a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'totals':r['totals'],'gate':r['first_review_gate'],'passed':r['first_review_passed']}))

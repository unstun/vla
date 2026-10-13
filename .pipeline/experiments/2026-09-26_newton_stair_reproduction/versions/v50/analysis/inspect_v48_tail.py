"""Read-only phase attribution from original v48 logs; no CPU-profiler claim."""
from pathlib import Path
import csv,hashlib,json,re
import numpy as np
OUT=Path(__file__).resolve().parent
BASE=OUT.parents[2]
LOG=BASE/'runs/v48_realtime_trial01/scan.log'
ROUNDS=BASE/'versions/v48/analysis/v48_rounds.json'
STAMP=re.compile(r'\[(\d+)\.(\d{9})\]')
ASTAR=re.compile(r'A-star path search took ([\d.]+)s, iter=(\d+)')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(line):
 m=STAMP.search(line)
 return int(m[1])*10**9+int(m[2]) if m else None
def stats(a):
 return {'count':len(a),'median':float(np.median(a)),'p95':float(np.percentile(a,95)),'maximum':float(max(a)),'sum':float(sum(a))} if a else None

def main():
 lines=LOG.read_text().splitlines();rounds=json.loads(ROUNDS.read_text());records=[];examples=[]
 for r in rounds:
  segment=lines[r['start_line']-1:r['end_line']]
  start=stamp(segment[0]);indices=[i for i,l in enumerate(segment) if 'input_refresh site=replan_start ' in l]
  first=indices[0] if indices else None
  warnings=[(r['start_line']+i,ASTAR.search(l)) for i,l in enumerate(segment[:first] if first is not None else []) if ASTAR.search(l)]
  warm_only=r['warm_accepts']>0 and r['warm_graph_fallbacks']==0
  prefix=(stamp(segment[first])-start)/1e6 if first is not None else None
  record={'start_line':r['start_line'],'end_line':r['end_line'],'simulation_s':r['ros_s'],'round_ms':r['wall_s']*1000,
   'warm_only':warm_only,'rebound_attempts':r['rebound_attempts'],'first_manager_entry_prefix_ms':prefix,
   'logged_goal_search_count':len(warnings),'logged_goal_search_ms':sum(float(m[1])*1000 for _,m in warnings),
   'logged_goal_search_iterations':sum(int(m[2]) for _,m in warnings)}
  records.append(record)
  if warnings and warm_only:
   examples.append({'round':record,'evidence_lines':[{'line':r['start_line']+i,'text':l} for i,l in enumerate(segment) if any(s in l for s in ('nominal_replan ','A-star path search took','reference_frontier ','input_refresh ','V48_WARM_SEED ','iter(+1)','full_spline_sampled_clear','nominal_replan_result'))]})
 groups={}
 for name,predicate in (('all',lambda r:True),('warm_only',lambda r:r['warm_only']),('warm_only_over_100ms',lambda r:r['warm_only'] and r['round_ms']>=100),('no_warm_only',lambda r:not r['warm_only'])):
  rr=[r for r in records if predicate(r)];pp=[r for r in rr if r['first_manager_entry_prefix_ms'] is not None]
  groups[name]={'round_ms':stats([r['round_ms'] for r in rr]),'pre_manager_ms':stats([r['first_manager_entry_prefix_ms'] for r in pp]),
   'pre_manager_share_of_group_wall_time':sum(r['first_manager_entry_prefix_ms'] for r in pp)/sum(r['round_ms'] for r in rr),
   'rounds_with_logged_pre_manager_astar':sum(r['logged_goal_search_count']>0 for r in rr),
   'logged_pre_manager_astar_ms_lower_bound':sum(r['logged_goal_search_ms'] for r in rr)}
 examples.sort(key=lambda x:x['round']['round_ms'],reverse=True)
 result={'run':'v48_realtime_trial01','source_sha256':{'scan.log':sha(LOG),'v48_rounds.json':sha(ROUNDS)},'completed_rounds':len(records),'groups':groups,
  'definitions':{'first_manager_entry_prefix_ms':'RCLCPP wall timestamp difference from nominal start to first replan_start refresh completion. Includes target selection, goal-neighborhood A*, other checks, first input refresh, logging and scheduling; not an isolated function or CPU timer.',
   'logged_goal_search_ms':'Native A-star elapsed warning inside that prefix. Warnings emitted only above 0.1 s; values rounded to milliseconds. Sum is a censored lower-bound estimate, not all goal-search time.',
   'warm_only':'At least one V48_WARM_RESULT accepted=1 and no warm-to-graph fallback, matching prior v48 analysis.',
   'claim_boundary':'Attribution from one recorded run. Does not prove cache hits, CPU cost, diagnostic output share, numerical equivalence of any optimization, or future 30 Hz.'}}
 (OUT/'v48_tail_attribution.json').write_text(json.dumps(result,indent=2)+'\n')
 (OUT/'v48_tail_examples.json').write_text(json.dumps(examples[:5],indent=2)+'\n')
 with (OUT/'v48_phase_spans.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()

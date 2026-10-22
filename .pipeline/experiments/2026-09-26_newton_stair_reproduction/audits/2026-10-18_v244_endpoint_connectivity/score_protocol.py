"""Report approved native protocol separately from v245's extra row-position flag.

PCT may begin its polyline after the measured body. Its unchanged native final
sampler explicitly includes that connector. Requiring the first returned row
itself to equal the body (new in v245) wrongly rejects unchanged v242 A02.
Keep the as-scored flags, verify actual endpoint/connector receipts, and apply
exactly the original v242 native success predicate. No native call is rerun.
"""
from pathlib import Path
import copy,csv,hashlib,json,statistics
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'endpoint_connectivity_v244/evaluation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,a):p.write_text(json.dumps(a,indent=2)+'\n')
def main():
 original=json.loads((OUT/'matrix_summary.json').read_text());assert len(original['calls'])==60
 matrix=copy.deepcopy(original);matrix['protocol']='Original frozen v242 native admission; exact real goal; sampled measured-start connector'
 corrections=[]
 for row in matrix['calls']:
  row['v245_extra_row_flag']=row['end_to_end_pass']
  m=row['metrics'];folder=OUT/'scored'/row['case_id']/f"rep{row['repetition']:02d}"
  ok=bool(row['exit_code']==0 and row['global_admitted'] and row['scan_published'] and m.get('published_independent_status')==0 and m.get('start_live_verdict')==0 and m.get('stale_inputs_ready')==0 and row['local_native_rejected_samples']==0)
  if row['global_admitted']:
   points=list(csv.DictReader((folder/'route.csv').open()));ep=list(map(float,(BASE/'generalization_v242/cases'/row['case_id']/'endpoints.txt').read_text().split()))[:6]
   end=[float(points[-1][k]) for k in ('x','y','z')];first=[float(points[0][k]) for k in ('x','y','z')]
   row['goal_max_abs_error_m']=max(abs(a-b) for a,b in zip(end,ep[3:]));row['implicit_start_connector_length_m']=sum((a-b)**2 for a,b in zip(first,ep[:3]))**.5
   refs=[q for q in row['static_query_phases'] if q['kind']=='final_reference' and q['rejected']==0]
   assert refs
   samples=list(csv.DictReader((folder/f"static_request_{refs[-1]['number']}.csv").open()))
   first_native=[float(samples[0][k]) for k in ('x','y','z')]
   row['native_checked_actual_start']=max(abs(a-b) for a,b in zip(first_native,ep[:3]))<1e-8
   ok &= row['native_checked_actual_start'] and row['goal_max_abs_error_m']<1e-5
   if row['case_id']=='A02':
    control=BASE/'generalization_v242/scored/A02'/f"rep{row['repetition']:02d}"/'route.csv'
    row['unchanged_v242_route_bytes']=sha(folder/'route.csv')==sha(control);assert row['unchanged_v242_route_bytes']
  row['end_to_end_pass']=bool(ok)
  if row['v245_extra_row_flag']!=row['end_to_end_pass']:corrections.append(dict(case_id=row['case_id'],repetition=row['repetition'],as_scored=row['v245_extra_row_flag'],native_protocol=row['end_to_end_pass'],implicit_start_connector_length_m=row['implicit_start_connector_length_m'],native_checked_actual_start=row['native_checked_actual_start'],unchanged_v242_route_bytes=row.get('unchanged_v242_route_bytes')))
 bycase=[]
 for old in original['by_case']:
  c=copy.deepcopy(old);rows=[r for r in matrix['calls'] if r['case_id']==c['case_id']];c['end_to_end_pass']=sum(r['end_to_end_pass'] for r in rows);bycase.append(c)
 matrix['by_case']=bycase;matrix['passed_calls']=sum(r['end_to_end_pass'] for r in matrix['calls']);matrix['corrections']=corrections
 write(OUT/'protocol_matrix_summary.json',matrix)
 cases=json.loads((BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v242/cases_manifest.json').read_text())['cases'];selected=[];excluded=[]
 for stratum,order in (('oblique_entry',['A02','A03','A04']),('new_destination',['G07','G05','G06']),('reverse',['R11','R10','R12'])):
  for caseid in order:
   c=next(r for r in bycase if r['case_id']==caseid)
   if c['end_to_end_pass']==5:
    case=next(r for r in cases if r['case_id']==caseid);selected.append(dict(case_id=caseid,stratum=stratum,scenario_sha256=case['scenario_sha256']));break
   excluded.append(dict(case_id=caseid,passed=c['end_to_end_pass']))
 selection=dict(selected=selected,excluded=excluded,predeclared_order=True,physical_admission_passed=len(selected)==3,cases_manifest_sha256=sha(BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v242/cases_manifest.json'),scored_calls=60)
 write(OUT/'protocol_selection.json',selection)
 gate=dict(passed=len(selected)==3,physical_representatives_admitted=len(selected),calls=60,passed_calls=matrix['passed_calls'],all_cases_passed=matrix['passed_calls']==60,boundary_group_coverage=any(c['case_id'] in ('B08','B09') and c['goal_search_calls'] for c in bycase),source_matrix_sha256=sha(OUT/'matrix_summary.json'),protocol_matrix_sha256=sha(OUT/'protocol_matrix_summary.json'),scope='Physical representative admission only; this does not assert universal endpoint generalization or required boundary branch coverage')
 write(OUT/'protocol_offline_gate.json',gate)
 write(OUT/'metric_correction.json',dict(reason=__doc__,as_scored_passes=original['passed_calls'],approved_native_protocol_passes=matrix['passed_calls'],corrections=corrections,source_sha256=sha(Path(__file__)),original_protocol_source_sha256=sha(BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v242/run_matrix.py')))
 print(json.dumps(gate))
if __name__=='__main__':main()

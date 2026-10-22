"""Frozen treatment: all original12requests x5fresh native processes."""
from pathlib import Path
import csv,hashlib,importlib.util,json,re,statistics,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'endpoint_connectivity_v244/evaluation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,a):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(a,indent=2)+'\n')
def main():
 freeze=json.loads((HERE/'manifest.json').read_text())
 for rel,h in freeze['source_files'].items():assert sha(HERE/rel)==h,rel
 manifest=json.loads((HERE.parent/'v242/cases_manifest.json').read_text());assert sha(HERE.parent/'v242/cases_manifest.json')==freeze['cases_manifest_sha256']
 policy=BASE/'repo/.pipeline/experiments/2026-09-26_newton_macos_policy/policy/policy_stateless_h10.onnx'
 assert sha(policy)=='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b'
 for group in ('source_inventory','installed_files'):
  for rel,h in json.loads((HERE.parent/'v240/results'/(group+'.json')).read_text()).items():assert sha(BASE/'cooperative_search_v240'/rel)==h,rel

 work=BASE/'endpoint_connectivity_v244/native';inventory=json.loads((HERE/'results/source_inventory.json').read_text())
 for rel,h in inventory.items():assert sha(work/rel)==h,rel
 for rel,h in json.loads((HERE/'results/installed_files.json').read_text()).items():assert sha(work/rel)==h,rel
 s=importlib.util.spec_from_file_location('frozen_metrics',HERE.parent/'v242/run_matrix.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
 write(OUT/'native_identity.json',dict(source_manifest_sha256=sha(HERE/'manifest.json'),source_inventory_sha256=sha(HERE/'results/source_inventory.json'),installed_inventory_sha256=sha(HERE/'results/installed_files.json'),cases_sha256=freeze['cases_manifest_sha256'],policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',native_probe_sha256=sha(OUT/'build/native_probe')))
 rows=[]
 for case in manifest['cases']:
  folder=BASE/'generalization_v242/cases'/case['case_id'];fixture=json.loads((folder/'fixture.json').read_text())
  for n,h in fixture['files'].items():assert sha(folder/n)==h,n
  assert fixture['physics_steps']==0 and fixture['max_scan_s']<=.1
  for repetition in range(1,6):
   dest=OUT/'scored'/case['case_id']/f'rep{repetition:02d}';dest.mkdir(parents=True,exist_ok=False);began=time.monotonic()
   with (dest/'stdout.log').open('w') as log:
    try:code=subprocess.run([sys.executable,str(HERE/'probe.py'),'/cases/'+case['case_id'],'/evaluation/scored/'+case['case_id']+f'/rep{repetition:02d}'],stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
    except subprocess.TimeoutExpired:code=124
   row=old.summarize(dest,code,time.monotonic()-began)
   context=None;queries=[];solvers=[]
   for line in (dest/'stdout.log').read_text(errors='replace').splitlines():
    m=re.search(r'pct_solver_attempt attempt=(\d+) smooth=(\d+)',line)
    if m:solvers.append(dict(attempt=int(m[1]),smooth=bool(int(m[2]))))
    m=re.search(r'pct_endpoint_connector_query samples=(\d+)',line)
    if m:context=dict(kind='endpoint_connector',samples=int(m[1]))
    m=re.search(r'pct_final_reference_query attempt=(\d+)',line)
    if m:context=dict(kind='final_reference',attempt=int(m[1]))
    m=re.search(r'STATIC_REQUEST number=(\d+) samples=(\d+) rejected=(\d+)',line)
    if m and context:queries.append(dict(context,number=int(m[1]),samples=int(m[2]),rejected=int(m[3])));context=None
   finals=[q for q in queries if q['kind']=='final_reference']
   row.update(case_id=case['case_id'],repetition=repetition,solver_attempts=solvers,static_query_phases=queries,
       first_gpmp_static_pass=bool(finals and finals[0]['attempt']==0 and finals[0]['rejected']==0),
       graph_fallback_attempted=any(s['attempt']==2 for s in solvers))
   if row['global_admitted']:
    route=list(csv.DictReader((dest/'route.csv').open()));endpoints=list(map(float,(folder/'endpoints.txt').read_text().split()))[:6]
    actual=[float(route[0][k]) for k in ('x','y','z')]+[float(route[-1][k]) for k in ('x','y','z')]
    row['endpoint_max_abs_error_m']=max(abs(a-b) for a,b in zip(actual,endpoints))
    row['end_to_end_pass'] &= row['endpoint_max_abs_error_m']<1e-5
   else:row['endpoint_max_abs_error_m']=None
   write(dest/'summary.json',row);rows.append(row);write(OUT/'matrix_progress.json',rows)
   print(json.dumps(dict(case_id=case['case_id'],rep=repetition,global_pass=row['global_admitted'],local_pass=row['scan_published'],overall=row['end_to_end_pass'],exit_code=code)),flush=True)
 bycase=[]
 for case in manifest['cases']:
  calls=[r for r in rows if r['case_id']==case['case_id']]
  def minimum(k):return min((r[k] for r in calls if r[k] is not None),default=None)
  bycase.append(dict(case_id=case['case_id'],denominator=len(calls),first_gpmp_static_pass=sum(r['first_gpmp_static_pass'] for r in calls),global_admitted=sum(r['global_admitted'] for r in calls),scan_first_published=sum(r['scan_published'] for r in calls),end_to_end_pass=sum(r['end_to_end_pass'] for r in calls),graph_fallback_calls=sum(r['graph_fallback_attempted'] for r in calls),edge_margin_min=minimum('edge_margin_min'),raw_solid_margin_min=minimum('raw_solid_margin_min'),local_edge_margin_min=minimum('local_edge_margin_min'),observed_point_margin_min=minimum('observed_point_margin_min'),global_time_s=[r['metrics'].get('global_s') for r in calls],local_time_s=[r['metrics'].get('scan_first_round_s') for r in calls],goal_search_calls=sum(r['metrics'].get('reference_goal_search_calls',0) for r in calls)))
 selected=[];excluded=[]
 for stratum,order in (('oblique_entry',['A02','A03','A04']),('new_destination',['G07','G05','G06']),('reverse',['R11','R10','R12'])):
  for caseid in order:
   entry=next(r for r in bycase if r['case_id']==caseid)
   if entry['end_to_end_pass']==5:
    case=next(c for c in manifest['cases'] if c['case_id']==caseid);selected.append(dict(case_id=caseid,stratum=stratum,scenario_sha256=case['scenario_sha256']));break
   excluded.append(dict(case_id=caseid,stratum=stratum,passed=entry['end_to_end_pass']))
 write(OUT/'matrix_summary.json',dict(version='v244',control='v242',calls=rows,by_case=bycase,margin_cap_m=.15,scored_calls=len(rows),passed_calls=sum(r['end_to_end_pass'] for r in rows),timing_mode='fixed ROS capture epoch; original sensor fixture; steady-clock wall durations; no live scheduling claim')))
 write(OUT/'selection.json',dict(selected=selected,excluded=excluded,predeclared_order=True,physical_admission_passed=len(selected)==3,cases_manifest_sha256=freeze['cases_manifest_sha256'],scored_calls=len(rows)))
 gate=dict(passed=len(rows)==60 and len(selected)==3,all_cases_passed=all(r['end_to_end_pass'] for r in rows),physical_representatives_admitted=len(selected),calls=len(rows),passed_calls=sum(r['end_to_end_pass'] for r in rows),boundary_coverage_observed=any(r['goal_search_calls'] for r in bycase),scope='Same-map native endpoint repair; retain every reject; selected physical representatives only')
 write(OUT/'offline_gate.json',gate)
 with (OUT/'matrix_table.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(bycase[0]));w.writeheader();w.writerows(bycase)
 print(json.dumps(gate),flush=True)
if __name__=='__main__':main()

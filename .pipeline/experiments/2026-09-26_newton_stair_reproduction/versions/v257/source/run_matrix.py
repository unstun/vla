"""Exactly one cold scored call per immutable distinct spatial case."""
from pathlib import Path
import csv,collections,hashlib,importlib.util,json,math,os,re,signal,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'space_coverage_v257';WORK=BASE/'generic_mechanisms_v256/native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def verify_frozen():
 native=HERE.parent/'v256';m=json.loads((native/'manifest.json').read_text())
 for rel,h in m['source_files'].items():assert sha(native/rel)==h,rel
 for name,h in m['inventories'].items():
  p=native/'results'/(name+'.json');assert sha(p)==h,name;root=OUT if name=='evaluator_files' else WORK
  if name=='evaluator_files':root=BASE/'generic_mechanisms_v256/evaluation'
  for rel,v in json.loads(p.read_text()).items():assert sha(root/rel)==v,rel
 assert sha(Path(m['raw_solid_source']))==m['raw_solid_sha256']
 for rel,h in json.loads((HERE/'manifest.json').read_text())['source_files'].items():assert sha(HERE/rel)==h,rel
 frozen=json.loads((HERE/'manifest.json').read_text());assert frozen['native_manifest_sha256']==sha(native/'manifest.json')
 assert sha(OUT/'cases_manifest.json')==frozen['cases_manifest_sha256']==sha(HERE/'cases_manifest.json')
 for cid,h in frozen['fixtures'].items():
  p=OUT/'cases'/cid/'fixture.json';assert sha(p)==h,cid;q=json.loads(p.read_text());assert q['physics_steps']==0 and q['max_scan_s']<=.1
  for rel,v in q['files'].items():assert sha(p.parent/rel)==v,(cid,rel)
 assert sha(OUT/'build/native_probe')==frozen['native_probe_sha256']
 assert sha(OUT/'policy_golden.json')==frozen['policy_golden_sha256'] and json.loads((OUT/'policy_golden.json').read_text())['passed']
 assert sha(BASE/'repo/.pipeline/experiments/2026-09-26_newton_macos_policy/policy/policy_stateless_h10.onnx')==m['policy_sha256']
 return frozen
spec=importlib.util.spec_from_file_location('metrics',HERE.parent/'v254/run_matrix.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
def summarize(target,c,code,elapsed):
 row=old.summarize(target,code,elapsed);row.update(case_id=c['case_id'],stratum=c['stratum'],expected=c['expected'],feature=c['feature'],calls=1)
 margin_file=target/'route_margins.csv'
 margin_rows=list(csv.DictReader(margin_file.open())) if margin_file.exists() else []
 row['legacy_raw_solid_margin_min']=min((float(p['legacy_raw_solid_margin']) for p in margin_rows),default=None)
 audit_file=target/'independent_solid_audit.json'
 audit=json.loads(audit_file.read_text()) if audit_file.exists() else {}
 row['local_raw_solid_margin_min']=audit.get('local_solid_margin_min')
 row['scan_failure_reason']='not_evaluated_global_rejected' if not row['global_admitted'] else ''
 if row['global_admitted'] and not row['scan_published']:
  m=row['metrics']
  row['scan_failure_reason']=('inputs_not_ready' if m.get('inputs_ready')!=1 else 'start_live_verdict='+str(m.get('start_live_verdict')) if m.get('start_live_verdict')!=0 else 'reference_target_rejected' if m.get('reference_have_target')!=1 else 'fsm_no_planning_round' if m.get('scan_rounds')==0 else 'first_planning_round_failed')
  row['scan_rejection_log']=[line for line in (target/'stdout.log').read_text(errors='replace').splitlines() if re.search(r'\[WARN\]|\[ERROR\]|[Ff]ailed|reject|verdict',line)][-12:]
 row['static_rejection_counts']=dict(collections.Counter(int(r['verdict']) for p in target.glob('static_request_*.csv') for r in csv.DictReader(p.open()) if int(r['verdict'])))
 row['optimizer_reasons']=re.findall(r'pct_optimizer_rejected attempt=\d+ reason=([^\n]+)',(target/'stdout.log').read_text(errors='replace'))
 row['start_error_m']=row['goal_error_m']=row['goal_yaw_error_rad']=row['initial_departure_turn_rad']=None
 if row['global_admitted']:
  path=list(csv.DictReader((target/'route.csv').open()));a,b=path[0],path[-1]
  xyz=lambda item:[float(item[k]) for k in ('x','y','z')]
  want=lambda which:c[which]['ground'][:2]+[c[which]['ground'][2]+.3]
  row['start_error_m']=max(abs(x-y) for x,y in zip(xyz(a),want('start')));row['goal_error_m']=max(abs(x-y) for x,y in zip(xyz(b),want('goal')))
  row['goal_yaw_error_rad']=abs(math.remainder(float(b['yaw'])-c['goal']['yaw'],2*math.pi))
  departure=next((p for p in path if math.hypot(float(p['x'])-float(a['x']),float(p['y'])-float(a['y']))>=.2),b)
  row['initial_departure_turn_rad']=abs(math.remainder(math.atan2(float(departure['y'])-float(a['y']),float(departure['x'])-float(a['x']))-c['start']['yaw'],2*math.pi))
  row['end_to_end_pass'] &= row['start_error_m']<1e-6 and row['goal_error_m']<1e-6 and row['goal_yaw_error_rad']<1e-6 and row['raw_solid_margin_min'] is not None and row['raw_solid_margin_min']>=-1e-10
 if row['scan_published']:
  row['end_to_end_pass'] &= row['local_raw_solid_margin_min'] is not None and row['local_raw_solid_margin_min']>=-1e-10
  if not row['end_to_end_pass'] and row['local_raw_solid_margin_min'] is not None and row['local_raw_solid_margin_min']<0:row['scan_failure_reason']='published_curve_static_solid_intrusion'
 row['expected_outcome_pass']=not row['global_admitted'] and code==0 if c['expected']=='reject' else row['end_to_end_pass']
 return row

def main():
 frozen=verify_frozen();manifest=json.loads((HERE/'cases_manifest.json').read_text());assert len(manifest['cases'])>=50
 rows=[]
 for c in manifest['cases']:
  cid=c['case_id'];target=OUT/'scored'/cid;target.mkdir(parents=True,exist_ok=False);name='v257-scored-'+cid.lower();began=time.monotonic()
  with (target/'stdout.log').open('x') as log:
   p=subprocess.Popen([sys.executable,str(HERE/'probe.py'),'/evaluation/cases/'+cid,'/evaluation/scored/'+cid],env=dict(os.environ,V257_CONTAINER_NAME=name),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   try:code=p.wait(timeout=150)
   except subprocess.TimeoutExpired:
    os.killpg(p.pid,signal.SIGTERM);subprocess.run(['docker','rm','-f',name],stdout=log,stderr=subprocess.STDOUT);p.wait(timeout=15);code=124
  if (target/'route_margins.csv').exists():
   with (target/'independent_audit.log').open('x') as audit_log:
    audit_code=subprocess.run(['/home/sun/vla_exec/envs/newton_worker/bin/python',str(HERE/'independent_solid_audit.py'),'route',str(target)],stdout=audit_log,stderr=subprocess.STDOUT).returncode
   if audit_code:code=125
  row=summarize(target,c,code,time.monotonic()-began);write(target/'summary.json',row);rows.append(row);write(OUT/'matrix_progress.json',rows)
  print(json.dumps({k:row[k] for k in ('case_id','expected','global_admitted','first_gpmp_static_pass','scan_published','end_to_end_pass','raw_solid_margin_min')}),flush=True)
 positives=[r for r in rows if r['expected']=='admit'];negative=[r for r in rows if r['expected']=='reject'];admitted=[r for r in rows if r['global_admitted']]
 safe=all(r['raw_solid_margin_min'] is not None and r['raw_solid_margin_min']>=-1e-10 for r in admitted)
 eligible=[r for r in positives if r['end_to_end_pass'] and r['first_gpmp_static_pass']]
 hardness=lambda r:(min(r['edge_margin_min'],r['raw_solid_margin_min']),-r['initial_departure_turn_rad'],r['case_id'])
 chosen=[]
 def take(ids):
  for cid in ids:
   row=next((r for r in eligible if r['case_id']==cid),None)
   if row and cid not in chosen:chosen.append(cid)
 take(['A04','G05','U14'])
 for group,count,predicate in [('descent',2,lambda r:True),('intermediate',1,lambda r:'start' in r['feature']),('intermediate',1,lambda r:'goal' in r['feature']),('same_floor',2,lambda r:True),('boundary',1,lambda r:True)]:
  take([r['case_id'] for r in sorted([r for r in eligible if r['stratum']==group and predicate(r)],key=hardness) if r['case_id'] not in chosen][:count])
 legal_pass=sum(r['end_to_end_pass'] for r in positives);first=sum(r['first_gpmp_static_pass'] for r in admitted)
 gate=dict(passed=legal_pass/len(positives)>=.9 and first/max(1,len(admitted))>=.9 and all(r['expected_outcome_pass'] for r in negative) and safe and len(chosen)==10,
  calls=len(rows),distinct_spatial_pairs=manifest['distinct_spatial_pairs'],positive_total=len(positives),positive_passed=legal_pass,illegal_controls=len(negative),illegal_correct_rejections=sum(r['expected_outcome_pass'] for r in negative),global_admitted=len(admitted),first_gpmp_passed=first,zero_admitted_negative_raw_margin=safe,selected=chosen,physical_attempts=0,scope='Installed C++ global/static and cold first local, explicit terminal heading; no physical claim')
 selection=dict(selected=[dict(case_id=cid,stratum=next(c['stratum'] for c in manifest['cases'] if c['case_id']==cid),scenario_sha256=next(c['scenario_sha256'] for c in manifest['cases'] if c['case_id']==cid)) for cid in chosen],physical_admission_passed=gate['passed'],ranking='Hardest eligible margin per stratum; A04/G05/U14 mandatory',cases_manifest_sha256=sha(HERE/'cases_manifest.json'))
 write(OUT/'offline_gate.json',gate);write(OUT/'selection.json',selection);write(OUT/'matrix_summary.json',dict(version='v257',native='v256',calls=rows,gate=gate))
 keys=['case_id','stratum','expected','global_admitted','first_gpmp_static_pass','graph_fallback_attempted','scan_published','end_to_end_pass','expected_outcome_pass','edge_margin_min','raw_solid_margin_min','legacy_raw_solid_margin_min','local_raw_solid_margin_min','observed_point_margin_min','start_error_m','goal_error_m','goal_yaw_error_rad','initial_departure_turn_rad','rejection','scan_failure_reason','global_s','scan_first_round_s','scan_first_publish_s']
 with (OUT/'matrix_table.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for r in rows:
   item={k:r.get(k) for k in keys};item.update(rejection=r['metrics'].get('global_error') or ('scan_first_round_failed' if not r['end_to_end_pass'] and r['expected']=='admit' else ''),global_s=r['metrics'].get('global_s'),scan_first_round_s=r['metrics'].get('scan_first_round_s'),scan_first_publish_s=r['metrics'].get('scan_first_publish_s'));w.writerow(item)
 print(json.dumps(gate),flush=True)
if __name__=='__main__':main()

"""One complete scored 50+3 cohort; no physics until the returned gate passes."""
from pathlib import Path
import concurrent.futures,csv,hashlib,importlib.util,json,math,os,statistics,subprocess,sys,time

HERE=Path(__file__).resolve().parent;ROOT=Path('/home/sun/vla_exec/local_search_tracking_v285')
OUT=ROOT/'benchmark';COHORT=ROOT/'cohort';PYTHON='/home/sun/vla_exec/envs/newton_worker/bin/python'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2)+'\n')
def verify():
    m=json.loads((HERE/'native_manifest.json').read_text())
    for rel,h in m['source_files'].items():assert sha(HERE/rel)==h,rel
    assert sha(COHORT/'cases_manifest.json')==m['cohort_sha256']
    for cid,h in m['fixtures'].items():assert sha(COHORT/'cases'/cid/'fixture.json')==h,cid
    for rel,h in json.loads((HERE/'results/installed_files.json').read_text()).items():assert sha(ROOT/'native'/rel)==h,rel
    assert sha(HERE/'results/evaluator_files.json')==m['evaluator_inventory_sha256']
    assert sha(HERE/'results/installed_files.json')==m['installed_inventory_sha256']
    for rel,h in json.loads((HERE/'results/evaluator_files.json').read_text()).items():assert sha(ROOT/rel)==h,rel
    return m
def audit(cid):
    folder=OUT/cid
    if not (folder/'route_margins.csv').exists():return dict(case_id=cid,exit_code=0,evaluated=False)
    with (folder/'independent_audit.log').open('x') as f:
        result=subprocess.run([PYTHON,str(HERE/'independent_source_audit.py'),'route',str(folder)],stdout=f,stderr=subprocess.STDOUT)
    return dict(case_id=cid,exit_code=result.returncode,evaluated=True)
def main():
    manifest=verify();cases=json.loads((COHORT/'cases_manifest.json').read_text())['cases'];assert len(cases)==53
    OUT.mkdir(exist_ok=True);ledger=[]
    with (OUT/'native_ledger.json').open('x') as f:json.dump(ledger,f)
    for c in cases:
        cid=c['case_id'];folder=OUT/cid;folder.mkdir(exist_ok=False)
        row=dict(case_id=cid,state='started',request_sha256=sha(COHORT/'cases'/cid/'endpoints.txt'));ledger.append(row);save(OUT/'native_ledger.json',ledger)
        started=time.monotonic()
        with (folder/'stdout.log').open('x') as log:
            try:code=subprocess.run([sys.executable,str(HERE/'run_native.py'),'case',str(COHORT/'cases'/cid),str(folder)],stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
            except subprocess.TimeoutExpired:
                subprocess.run(['docker','rm','-f','v285-case-'+cid.lower()],stdout=log,stderr=subprocess.STDOUT);code=124
        row.update(state='finished',exit_code=code,wall_s=time.monotonic()-started);save(OUT/'native_ledger.json',ledger)
        metrics=dict(l.split('=',1) for l in (folder/'metrics.txt').read_text().splitlines() if '=' in l) if (folder/'metrics.txt').exists() else {}
        print(json.dumps(dict(case_id=cid,code=code,global_admitted=metrics.get('global_admitted'),global_s=metrics.get('global_s'),scan_published=metrics.get('scan_published'))),flush=True)
    verify();audits=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(audit,[c['case_id'] for c in cases]):
            audits.append(result);save(OUT/'audit_ledger.json',audits);print(json.dumps(dict(stage='audit',**result)),flush=True)
    spec=importlib.util.spec_from_file_location('original_metrics',HERE.parent/'v257/run_matrix.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    results=[]
    for c,execution in zip(cases,ledger):
        cid=c['case_id'];a=next(a for a in audits if a['case_id']==cid)
        row=module.summarize(OUT/cid,c,execution['exit_code'] if a['exit_code']==0 else 125,execution['wall_s'])
        row.update(native_exit_code=execution['exit_code'],audit_exit_code=a['exit_code'])
        p=OUT/cid/'independent_solid_audit.json';q=json.loads(p.read_text()) if p.exists() else {}
        for channel,prefix in [('route_margins',''),('local_samples','local_')]:
            v=q.get(channel,{});row[prefix+'source_margin_min']=v.get('native_margin_min')
        save(OUT/cid/'summary.json',row);results.append(row)
    positives=[r for r in results if r['expected']=='admit'];negative=[r for r in results if r['expected']=='reject'];admitted=[r for r in positives if r['global_admitted']]
    good=[r for r in positives if r['end_to_end_pass']];times=[r['metrics']['global_s'] for r in admitted]
    first=sum(r['first_gpmp_static_pass'] for r in admitted)
    source_safe=all(r['source_margin_min'] is not None and r['source_margin_min']>=0 and r['raw_solid_margin_min'] is not None and r['raw_solid_margin_min']>=0 for r in admitted)
    local_safe=all(r['local_source_margin_min'] is not None and r['local_source_margin_min']>=0 and r['local_raw_solid_margin_min'] is not None and r['local_raw_solid_margin_min']>=0 and r.get('local_native_rejected_samples',0)==0 for r in results if r['scan_published'])
    gate=dict(calls=53,positive_total=50,positive_passed=len(good),global_admitted=len(admitted),first_gpmp_passed=first,
        first_gpmp_rate_all_positives=first/50,first_gpmp_rate_admitted=first/max(1,len(admitted)),
        illegal_controls=3,illegal_correct_rejections=sum(r['expected_outcome_pass'] for r in negative),
        global_median_s=statistics.median(times) if times else None,global_p95_s=sorted(times)[math.ceil(.95*len(times))-1] if times else None,
        global_max_s=max(times,default=None),zero_admitted_negative_raw_margin=source_safe,zero_published_negative_raw_margin=local_safe,
        selected=manifest['physical_cases'],cpu_limit=2,initialization_excluded_and_reported_separately=True)
    selected_pass=all(any(r['case_id']==cid and r['end_to_end_pass'] for r in positives) for cid in manifest['physical_cases'])
    gate['passed']=bool(len(good)>=48 and gate['illegal_correct_rejections']==3 and source_safe and local_safe and times and statistics.median(times)<=1.5 and first/max(1,len(admitted))>=.9 and selected_pass)
    save(OUT/'offline_gate.json',gate);save(OUT/'matrix_summary.json',dict(version='v285',calls=results,gate=gate))
    save(OUT/'selection.json',dict(physical_admission_passed=gate['passed'],selected=[next(c for c in cases if c['case_id']==cid) for cid in manifest['physical_cases']],cases_manifest_sha256=manifest['cohort_sha256']))
    fields=['case_id','expected','global_admitted','first_gpmp_static_pass','scan_published','end_to_end_pass','source_margin_min','local_source_margin_min','scan_failure_reason']
    with (OUT/'matrix_table.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows({k:r.get(k) for k in fields} for r in results)
    verify();save(OUT/'complete.json',dict(calls=53,all_cases_finished=True,native_manifest_sha256=sha(HERE/'native_manifest.json')))
    print(json.dumps(gate),flush=True)
if __name__=='__main__':main()

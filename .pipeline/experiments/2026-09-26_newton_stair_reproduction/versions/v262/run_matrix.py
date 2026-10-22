"""One scored cold full-chain request per pre-frozen mesh-certified tuple."""
from pathlib import Path
import csv,hashlib,importlib.util,json,math,os,signal,statistics,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'mesh_benchmark_v262'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def verify():
    report=load(HERE.parent/'v261/verify_frozen.py','native_identity').verify()
    m=json.loads((HERE/'manifest.json').read_text())
    assert m['native_manifest_sha256']==report['native_manifest_sha256']
    assert sha(OUT/'cases_manifest.json')==m['cases_manifest_sha256']==sha(HERE/'cases_manifest.json')
    for rel,h in m['source_files'].items():assert sha(HERE/rel)==h,rel
    for cid,h in m['fixtures'].items():
        p=OUT/'cases'/cid/'fixture.json';assert sha(p)==h,cid
        f=json.loads(p.read_text());assert f['physics_steps']==0 and f['max_scan_s']<=.1
        for name,value in f['files'].items():assert sha(p.parent/name)==value,(cid,name)
    assert sha(OUT/'policy_golden.json')==m['policy_golden_sha256']
    assert json.loads((OUT/'policy_golden.json').read_text())['passed']
    return m
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2)+'\n')
def main():
    frozen=verify();manifest=json.loads((HERE/'cases_manifest.json').read_text())
    assert manifest['positive_count']==50 and manifest['distinct_positive_tuples']==50
    metrics=load(HERE.parent/'v257/run_matrix.py','original_metrics');rows=[]
    for c in manifest['cases']:
        cid=c['case_id'];target=OUT/'scored'/cid;target.mkdir(parents=True,exist_ok=False);began=time.monotonic()
        with (target/'stdout.log').open('x') as log:
            p=subprocess.Popen([sys.executable,str(HERE/'probe.py'),'/evaluation/cases/'+cid,
                '/evaluation/scored/'+cid],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:code=p.wait(timeout=180)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGTERM);subprocess.run(['docker','rm','-f','v262-scored-'+cid.lower()],stdout=log,stderr=subprocess.STDOUT);p.wait(timeout=15);code=124
        if (target/'route_margins.csv').exists():
            with (target/'independent_audit.log').open('x') as log:
                q=subprocess.run(['/home/sun/vla_exec/envs/newton_worker/bin/python',str(HERE.parent/'v257/independent_solid_audit.py'),'route',str(target)],stdout=log,stderr=subprocess.STDOUT)
            if q.returncode:code=125
        row=metrics.summarize(target,c,code,time.monotonic()-began);write(target/'summary.json',row)
        rows.append(row);write(OUT/'progress.json',rows)
        print(json.dumps({k:row[k] for k in ('case_id','expected','global_admitted','first_gpmp_static_pass','scan_published','end_to_end_pass')}),flush=True)
    positive=[r for r in rows if r['expected']=='admit'];negative=[r for r in rows if r['expected']=='reject']
    admitted=[r for r in positive if r['global_admitted']];eligible=[r for r in positive if r['end_to_end_pass']]
    hardness=lambda r:(min(r['edge_margin_min'],r['raw_solid_margin_min']),-r['initial_departure_turn_rad'],r['case_id'])
    selected=[]
    def take(ids):
        for cid in ids:
            if cid not in selected and any(r['case_id']==cid for r in eligible):selected.append(cid)
    take(['A04','G05','CU06','D07','S04'])
    for stratum,count,predicate in [('descent',1,lambda r:True),('intermediate',1,lambda r:'start' in r['feature']),('intermediate',1,lambda r:'goal' in r['feature']),('same_floor',1,lambda r:True),('boundary',1,lambda r:True)]:
        take([r['case_id'] for r in sorted([r for r in eligible if r['stratum']==stratum and predicate(r) and r['case_id'] not in selected],key=hardness)][:count])
    times=[r['metrics']['global_s'] for r in admitted];median=statistics.median(times) if times else math.inf
    safe=all(r['raw_solid_margin_min'] is not None and r['raw_solid_margin_min']>=-1e-10 for r in rows if r['global_admitted'])
    total=sum(r['end_to_end_pass'] for r in positive);first=sum(r['first_gpmp_static_pass'] for r in admitted)
    gate=dict(passed=total>=45 and first/max(1,len(admitted))>=.9 and all(r['expected_outcome_pass'] for r in negative) and safe and median<=1.5 and len(selected)==10 and {'A04','G05','CU06','D07','S04'}<=set(selected),
        calls=len(rows),positive_total=50,positive_passed=total,global_admitted=len(admitted),first_gpmp_passed=first,
        illegal_controls=len(negative),illegal_correct_rejections=sum(r['expected_outcome_pass'] for r in negative),
        global_median_s=median,global_max_s=max(times,default=None),global_p95_s=sorted(times)[min(len(times)-1,math.ceil(.95*len(times))-1)] if times else None,
        zero_admitted_negative_raw_margin=safe,selected=selected,physical_attempts=0,
        cpu_limit=2,initialization_excluded_and_reported_separately=True,scope='Cold installed C++ PCT/ENV225/GPMP/static/first SCAN; nominal zero-step sensor fixtures; physical execution separate')
    selection=dict(physical_admission_passed=gate['passed'],selected=[dict(case_id=cid,stratum=next(c['stratum'] for c in manifest['cases'] if c['case_id']==cid),scenario_sha256=next(c['scenario_sha256'] for c in manifest['cases'] if c['case_id']==cid)) for cid in selected],cases_manifest_sha256=sha(HERE/'cases_manifest.json'),ranking='Predeclared A04/G05/back-facing CU06/D07/S04 plus hardest eligible margins in remaining strata')
    write(OUT/'offline_gate.json',gate);write(OUT/'selection.json',selection);write(OUT/'matrix_summary.json',dict(version='v262',native='v261',calls=rows,gate=gate))
    keys=['case_id','stratum','expected','global_admitted','first_gpmp_static_pass','graph_fallback_attempted','scan_published','end_to_end_pass','edge_margin_min','raw_solid_margin_min','local_raw_solid_margin_min','observed_point_margin_min','start_error_m','goal_error_m','goal_yaw_error_rad','scan_failure_reason','global_s','scan_first_publish_s','initialization_s']
    with (OUT/'matrix_table.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:r['metrics'].get(k) if k in ('global_s','scan_first_publish_s','initialization_s') else r.get(k) for k in keys})
    print(json.dumps(gate),flush=True)
if __name__=='__main__':main()

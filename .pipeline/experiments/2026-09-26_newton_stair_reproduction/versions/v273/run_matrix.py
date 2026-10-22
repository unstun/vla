"""Exactly 105 native requests, then independent audits without timing overlap."""
from common import *
import concurrent.futures,csv,math,os,signal,statistics,subprocess,sys,time
PYTHON='/home/sun/vla_exec/envs/newton_worker/bin/python'
def audit(item):
    cohort,cid=item;folder=OUT/cohort/cid
    if not (folder/'route_margins.csv').exists():return dict(cohort=cohort,case_id=cid,code=0,evaluated=False)
    with (folder/'independent_audit.log').open('x') as log:
        code=subprocess.run([PYTHON,str(HERE.parent/'v272/independent_source_audit.py'),'route',str(folder)],stdout=log,stderr=subprocess.STDOUT).returncode
    return dict(cohort=cohort,case_id=cid,code=code,evaluated=True)
def report(cohort,rows):
    positives=[r for r in rows if r['expected']=='admit'];negative=[r for r in rows if r['expected']=='reject']
    admitted=[r for r in positives if r['global_admitted']];times=[r['metrics']['global_s'] for r in admitted]
    eligible=[r for r in positives if r['end_to_end_pass']];selected=[]
    def take(ids):
        for cid in ids:
            if cid not in selected and any(r['case_id']==cid for r in eligible):selected.append(cid)
    if cohort=='clean50':
        take(['A04','G05','CU06','D07','S04'])
        hardness=lambda r:(min(r['edge_margin_min'],r['raw_solid_margin_min']),-r['initial_departure_turn_rad'],r['case_id'])
        for group,predicate in [('descent',lambda r:True),('intermediate',lambda r:'start' in r['feature']),('intermediate',lambda r:'goal' in r['feature']),('same_floor',lambda r:True),('boundary',lambda r:True)]:
            take([r['case_id'] for r in sorted([r for r in eligible if r['stratum']==group and predicate(r) and r['case_id'] not in selected],key=hardness)][:1])
    first=sum(r['first_gpmp_static_pass'] for r in admitted);total=len(eligible);median=statistics.median(times) if times else None
    safe=all(r['raw_solid_margin_min'] is not None and r['raw_solid_margin_min']>=-1e-10 for r in rows if r['global_admitted'])
    local_safe=all(r['local_raw_solid_margin_min'] is not None and r['local_raw_solid_margin_min']>=-1e-10 for r in rows if r['scan_published'])
    gate=dict(calls=len(rows),positive_total=len(positives),positive_passed=total,global_admitted=len(admitted),first_gpmp_passed=first,
        first_gpmp_rate_all_positives=first/max(1,len(positives)),first_gpmp_rate_admitted=first/max(1,len(admitted)),
        illegal_controls=len(negative),illegal_correct_rejections=sum(r['expected_outcome_pass'] for r in negative),
        global_median_s=median,global_max_s=max(times,default=None),global_p95_s=sorted(times)[min(len(times)-1,math.ceil(.95*len(times))-1)] if times else None,
        zero_admitted_negative_raw_margin=safe,zero_published_negative_raw_margin=local_safe,selected=selected,physical_attempts=0,cpu_limit=2,
        initialization_excluded_and_reported_separately=True)
    gate['passed']=bool(cohort=='clean50' and total>=45 and first/max(1,len(admitted))>=.9 and all(r['expected_outcome_pass'] for r in negative) and safe and local_safe and median is not None and median<=1.5 and len(selected)==10 and {'A04','G05','CU06','D07','S04'}<=set(selected))
    write(OUT/cohort/'offline_gate.json',gate);write(OUT/cohort/'matrix_summary.json',dict(version='v273',native='v272',cohort=cohort,calls=rows,gate=gate))
    manifest=json.loads((HERE/(cohort+'.json')).read_text());write(OUT/cohort/'selection.json',dict(physical_admission_passed=gate['passed'],selected=[next(c for c in manifest['cases'] if c['case_id']==cid) for cid in selected],cases_manifest_sha256=sha(HERE/(cohort+'.json'))))
    keys=['case_id','stratum','expected','global_admitted','first_gpmp_static_pass','graph_fallback_attempted','scan_published','end_to_end_pass','expected_outcome_pass','edge_margin_min','raw_solid_margin_min','native_source_margin_min','voxel_control_margin_min','local_raw_solid_margin_min','local_source_margin_min','local_voxel_control_margin_min','start_error_m','goal_error_m','goal_yaw_error_rad','static_rejection_counts','optimizer_reasons','scan_failure_reason','global_s','scan_first_publish_s','initialization_s']
    with (OUT/cohort/'matrix_table.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:r['metrics'].get(k) if k in ('global_s','scan_first_publish_s','initialization_s') else r.get(k) for k in keys})
    print(json.dumps(dict(cohort=cohort,gate=gate)),flush=True)
def main():
    verify();assert not (OUT/'native_ledger.json').exists();OUT.mkdir(parents=True,exist_ok=True);ledger=[];items=[]
    write(OUT/'native_ledger.json',ledger)
    for cohort in COHORTS:
        for case in json.loads((HERE/(cohort+'.json')).read_text())['cases']:
            cid=case['case_id'];folder=OUT/cohort/cid;folder.mkdir(parents=True,exist_ok=False);items.append((cohort,cid))
            entry=dict(cohort=cohort,case_id=cid,state='started',request_sha256=sha(BASE/COHORTS[cohort][1]/'cases'/cid/'endpoints.txt'));ledger.append(entry);write(OUT/'native_ledger.json',ledger)
            began=time.monotonic()
            with (folder/'stdout.log').open('x') as log:
                p=subprocess.Popen([sys.executable,str(HERE/'probe.py'),cohort,cid],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:code=p.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid,signal.SIGTERM);subprocess.run(['docker','rm','-f','v273-'+cohort+'-'+cid.lower()],stdout=log,stderr=subprocess.STDOUT);p.wait(timeout=15);code=124
            entry.update(state='finished',exit_code=code,wall_with_container_s=time.monotonic()-began);write(OUT/'native_ledger.json',ledger)
            metrics={}
            if (folder/'metrics.txt').exists():metrics=dict(l.split('=',1) for l in (folder/'metrics.txt').read_text().splitlines() if '=' in l)
            print(json.dumps(dict(cohort=cohort,case_id=cid,native_code=code,global_admitted=metrics.get('global_admitted'),global_s=metrics.get('global_s'),scan_published=metrics.get('scan_published'))),flush=True)
    verify();audits={};audit_rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for future in concurrent.futures.as_completed([pool.submit(audit,item) for item in items]):
            r=future.result()
            audits[(r['cohort'],r['case_id'])]=r;audit_rows.append(r);write(OUT/'audit_ledger.json',audit_rows)
            print(json.dumps(dict(stage='raw_point_audit',**r)),flush=True)
    metrics=load(HERE.parent/'v257/run_matrix.py','metrics257')
    for cohort in COHORTS:
        rows=[]
        for case in json.loads((HERE/(cohort+'.json')).read_text())['cases']:
            cid=case['case_id'];folder=OUT/cohort/cid;entry=next(r for r in ledger if r['cohort']==cohort and r['case_id']==cid)
            code=entry['exit_code'] if audits[(cohort,cid)]['code']==0 else 125
            row=metrics.summarize(folder,case,code,entry['wall_with_container_s']);row['native_exit_code']=entry['exit_code'];row['audit_exit_code']=audits[(cohort,cid)]['code']
            ap=folder/'independent_solid_audit.json';a=json.loads(ap.read_text()) if ap.exists() else {}
            for channel,prefix in [('route_margins',''),('local_samples','local_')]:
                q=a.get(channel,{});row[prefix+'source_margin_min' if prefix else 'native_source_margin_min']=q.get('native_margin_min');row[prefix+'voxel_control_margin_min']=q.get('voxel_control_min')
            write(folder/'summary.json',row);rows.append(row)
        report(cohort,rows)
    verify();write(OUT/'complete.json',dict(native_calls=len(ledger),all_cases_finished=all(r['state']=='finished' for r in ledger),frozen_manifest_sha256=sha(HERE/'manifest.json'),physical_attempts=0))
if __name__=='__main__':main()

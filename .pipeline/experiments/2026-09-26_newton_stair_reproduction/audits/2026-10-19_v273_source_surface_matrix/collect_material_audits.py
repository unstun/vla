"""Collect derived material-audit receipts without changing frozen native scores."""
from pathlib import Path
import hashlib,json,shutil,statistics
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for version,folder in [('v275','source_point_diagnosis_v275'),('v276','source_point_volume_audit_v276')]:
    source=BASE/folder;complete=json.loads((source/'replay_complete.json').read_text());assert complete['cases']==86 and complete['failures']==0
    dest=HERE/'material_audits'/version;dest.mkdir(parents=True,exist_ok=True);returned={};remote={}
    for p in source.rglob('*'):
        if not p.is_file():continue
        rel=str(p.relative_to(source));record=dict(sha256=sha(p),bytes=p.stat().st_size,remote_path=str(p))
        if p.name in ('audit.json','replay_complete.json','replay_started.json','replay01.log'):
            q=dest/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);returned[rel]=record
        else:remote[rel]=record
    report=dict(audit_version=version,native_version='v272',scored_cohort='v273',new_planning_calls=0,physics_steps=0,original_ledger_retained=True,cohorts={})
    for cohort in ('original52','clean50'):
        old=json.loads((BASE/'source_benchmark_v273'/cohort/'matrix_summary.json').read_text());rows=[]
        for r in old['calls']:
            a=source/'audited'/cohort/r['case_id']/'audit.json';audit=json.loads(a.read_text()) if a.exists() else {}
            gm=audit.get('route_margins',{}).get('minimum_raw_margin');lm=audit.get('local_samples_checked',{}).get('minimum_raw_margin')
            m=r['metrics'];passed=bool(r['native_exit_code']==0 and r['global_admitted'] and r['scan_published'] and m.get('published_independent_status')==0 and m.get('start_live_verdict')==0 and m.get('stale_inputs_ready')==0 and r['local_native_rejected_samples']==0 and all(r[k] is not None and r[k]<1e-6 for k in ('start_error_m','goal_error_m','goal_yaw_error_rad')) and gm is not None and gm>=-1e-10 and lm is not None and lm>=-1e-10)
            rows.append(dict(case_id=r['case_id'],expected=r['expected'],global_admitted=r['global_admitted'],first_gpmp_static_pass=r['first_gpmp_static_pass'],scan_published=r['scan_published'],as_scored_full_pass=r['end_to_end_pass'],derived_full_pass=passed,derived_global_raw_margin=gm,derived_local_raw_margin=lm,global_s=m.get('global_s'),edge_margin_min=r['edge_margin_min']))
        positive=[r for r in rows if r['expected']=='admit'];admitted=[r for r in positive if r['global_admitted']];first=sum(r['first_gpmp_static_pass'] for r in admitted)
        report['cohorts'][cohort]=dict(positive_total=len(positive),as_scored_full_pass=sum(r['as_scored_full_pass'] for r in positive),derived_full_pass=sum(r['derived_full_pass'] for r in positive),first_gpmp_passed=first,first_gpmp_rate_admitted=first/len(admitted),global_median_s=statistics.median(r['global_s'] for r in admitted),minimum_raw_margin=min(r['derived_global_raw_margin'] for r in admitted),illegal_controls=old['gate']['illegal_controls'],illegal_correct_rejections=old['gate']['illegal_correct_rejections'],rows=rows)
    report['offline_gate_passed']=False
    report['blocking_gates']='v272 clean50 first GPMP 43/48 < 90%; global median 2.7436 s > 1.5 s. Derived audit is not a new planner run.'
    (dest/'derived_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    (dest/'return_inventory.json').write_text(json.dumps(dict(returned=returned,remote=remote,derived_summary_sha256=sha(dest/'derived_summary.json')),indent=2)+'\n')
    print(json.dumps(dict(version=version,returned_files=len(returned),returned_bytes=sum(x['bytes'] for x in returned.values()),cohorts={k:{a:b for a,b in v.items() if a!='rows'} for k,v in report['cohorts'].items()})))

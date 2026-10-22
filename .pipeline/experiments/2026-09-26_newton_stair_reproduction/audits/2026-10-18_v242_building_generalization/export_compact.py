"""Exact compact evidence export; no cloud, archive or compilation cache return."""
from pathlib import Path
import csv,hashlib,json,shutil,statistics,subprocess

HERE=Path(__file__).resolve().parent
BASE=Path('/data/sun/vla_mppi_20261009');RAW=BASE/'generalization_v242'
OUT=RAW/'compact_return02'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    matrix=json.loads((RAW/'matrix_summary.json').read_text());calls=matrix['calls']
    assert len(calls)==60 and len(matrix['by_case'])==12
    selection=json.loads((RAW/'selection.json').read_text())
    OUT.mkdir(exist_ok=False)
    paths=[]
    paths += [RAW/name for name in ('matrix_summary.json','matrix_progress.json','cases_manifest.json',
        'selection.json','adapter_controls.json','native_identity.json','policy_golden.json','linked_libraries.txt',
        'endpoint_inspect02.txt')]
    paths += [p for p in RAW.glob('*.log') if not p.name.startswith('export')]
    paths += [p for p in (RAW/'discovery').rglob('*') if p.is_file() and p.suffix in ('.json','.csv','.txt','.png')]
    paths += [p for p in (RAW/'cases').rglob('*') if p.is_file() and p.name in ('scenario.json','endpoints.txt','fixture.json','scan_timing.jsonl','scans.txt')]
    paths += [p for p in (RAW/'scored').rglob('*') if p.is_file() and p.suffix in ('.json','.csv','.txt','.log')]
    paths += [p for p in (RAW/'development').rglob('*') if p.is_file() and p.suffix in ('.csv','.json','.txt','.log')]
    copied={}
    for p in sorted(set(paths)):
        assert p.is_file(),p
        assert not any(part in ('CMakeFiles','build','endpoint_build','warp-cache') for part in p.relative_to(RAW).parts)
        q=OUT/p.relative_to(RAW);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
        assert sha(q)==sha(p)
        copied[str(p.relative_to(RAW))]=dict(bytes=p.stat().st_size,sha256=sha(p))
    report=dict(offline_cases=12,scored_calls=60,global_admitted=sum(r['global_admitted'] for r in calls),
        scan_first_published=sum(r['scan_published'] for r in calls),end_to_end_pass=sum(r['end_to_end_pass'] for r in calls),
        early_pct_no_route=sum(r['metrics'].get('global_error')=='Native PCT: pct_no_route' for r in calls),
        eligible_physical_cases=len(selection['selected']),physical_admission_passed=len(selection['selected'])>=2,
        physical_attempts=0,physical_video_files=[],
        physical_decision='Do not launch: fewer than two eligible cases, as specified in approved design.md',
        boundary_goal_neighborhood_coverage_passed=any(r['case_id'] in ('B08','B09') and r['metrics'].get('reference_goal_search_calls',0)>0 for r in calls),
        parent_native_version='v240',unchanged_policy=True,hard_collision_support_m=.35,sensor_period_s=.1,
        cases_manifest_sha256=sha(RAW/'cases_manifest.json'),matrix_summary_sha256=sha(RAW/'matrix_summary.json'))
    report['attribution_boundary']='endpoint_inspect02 uses actual Search; first endpoint observer GetNeighbors() was a native stub and its neighbor counts are superseded, not evidence'
    (OUT/'evaluation_gate.json').write_text(json.dumps(report,indent=2)+'\n')
    fields=['case_id','direction','calls','global_admitted','scan_first_published','end_to_end_pass',
        'min_extra_edge_m','min_raw_solid_m','global_median_ms','global_max_ms','scan_median_ms','scan_max_ms','reason']
    with (OUT/'matrix_table.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for c in matrix['by_case']:
            g=[v*1000 for v in c['global_time_s'] if v is not None];s=[v*1000 for v in c['local_time_s'] if v is not None]
            writer.writerow(dict(case_id=c['case_id'],direction=c['direction'],calls=c['denominator'],
                global_admitted=c['global_admitted'],scan_first_published=c['scan_first_published'],end_to_end_pass=c['end_to_end_pass'],
                min_extra_edge_m=c['edge_margin_min'] if c['edge_margin_min'] is not None else 'N/A',
                min_raw_solid_m=c['raw_solid_margin_min'] if c['raw_solid_margin_min'] is not None else 'N/A',
                global_median_ms=statistics.median(g),global_max_ms=max(g),
                scan_median_ms=statistics.median(s) if s else 'N/A',scan_max_ms=max(s) if s else 'N/A',
                reason='passed' if c['end_to_end_pass']==5 else 'pct_no_route; GPMP/static/SCAN not reached'))
    after=dict(docker_ps=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}'],text=True),
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,utilization.gpu','--format=csv,noheader'],text=True),
        peer_mutations_by_task=[],physical_runs_started=0)
    (OUT/'host_after.json').write_text(json.dumps(after,indent=2)+'\n')
    final={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in OUT.rglob('*') if p.is_file()}
    assert sum(r['bytes'] for r in final.values())<50*2**20
    receipt=dict(host='gpu5070ti',remote_raw_root=str(RAW),remote_export_root=str(OUT),
        files=final,total_bytes=sum(r['bytes'] for r in final.values()),
        bulk_excluded=['case local/world clouds','native binary/static archives','CMakeFiles','build/endpoint_build','Warp cache'],
        frozen_source_version='v242',actual_physical_attempts=0)
    (OUT/'RETURN_MANIFEST.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(report,indent=2));print('Return bytes',receipt['total_bytes'])

if __name__=='__main__':main()

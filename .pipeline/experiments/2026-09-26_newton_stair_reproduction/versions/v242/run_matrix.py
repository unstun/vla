"""60 scored fresh processes; failed calls remain in stage denominators."""
from pathlib import Path
import csv,hashlib,importlib.util,json,re,subprocess,sys,time

HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
OUT=BASE/'generalization_v242'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')

def read_metrics(folder):
    value={}
    p=folder/'metrics.txt'
    if p.exists():
        for row in p.read_text().splitlines():
            if '=' in row:
                k,v=row.split('=',1)
                try:v=float(v)
                except ValueError:pass
                value[k]=v
    return value

def samples(folder,name):
    p=folder/name
    return list(csv.DictReader(p.open())) if p.exists() else []

def summarize(folder,code,elapsed):
    metrics=read_metrics(folder);log=(folder/'stdout.log').read_text(errors='replace')
    static=samples(folder,'static_request_1.csv');route=samples(folder,'route_margins.csv');local=samples(folder,'local_samples.csv')
    def minimum(rows,key):
        values=[float(r[key]) for r in rows if r.get(key,'')!='']
        return min(values) if values else None
    repairs=sorted(set(map(int,re.findall(r'pct_shared_rejected attempt=(\d+)',log))))
    known=sum(int(r['centers_observed']) for r in local)
    unknown=sum(int(r['centers_unknown']) for r in local)
    outside=sum(int(r['centers_outside']) for r in local)
    summary=dict(exit_code=code,wall_with_container_s=elapsed,metrics=metrics,
        first_gpmp_static_pass=bool(static) and all(int(r['verdict'])==0 for r in static) and 0 not in repairs,
        global_admitted=metrics.get('global_admitted',0)==1,
        rejected_gpmp_attempts=repairs,graph_fallback_attempted=1 in repairs,
        scan_published=metrics.get('scan_published',0)>0 and metrics.get('scan_successes',0)==1,
        edge_margin_min=minimum(route,'edge_margin'),raw_solid_margin_min=minimum(route,'raw_solid_margin'),
        static_margin_samples=len(route),static_unknown_floor_samples=sum(int(r['floor_known'])==0 for r in route),
        static_edge_saturated_samples=sum(float(r['edge_margin'])>=.15-1e-6 for r in route),
        local_edge_margin_min=minimum(local,'edge_margin'),observed_point_margin_min=minimum(local,'observed_point_margin'),
        local_center_coverage=dict(observed=known,unknown=unknown,outside=outside,total=known+unknown+outside),
        local_native_rejected_samples=sum(int(r['live_verdict'])!=0 for r in local),
        hashes={p.name:sha(p) for p in folder.iterdir() if p.is_file() and p.name!='summary.json'})
    summary['end_to_end_pass']=bool(code==0 and summary['global_admitted'] and summary['scan_published'] and
        metrics.get('published_independent_status')==0 and metrics.get('start_live_verdict')==0 and
        metrics.get('stale_inputs_ready')==0 and summary['local_native_rejected_samples']==0)
    return summary

def main():
    manifest=json.loads((OUT/'cases_manifest.json').read_text())
    freeze=json.loads((HERE/'manifest.json').read_text())
    for rel,expected in freeze['source_files'].items():assert sha(HERE/rel)==expected,rel
    assert sha(OUT/'cases_manifest.json')==freeze['cases_manifest_sha256']
    spec=importlib.util.spec_from_file_location('frozen_parent_gate',HERE.parent/'v241/launch.py')
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    source_gate=parent.verify_sources()
    write(OUT/'native_identity.json',dict(parent=source_gate,probe_sha256=sha(OUT/'build/native_probe'),
        frozen_source_manifest=sha(HERE/'manifest.json'),cases_manifest=sha(OUT/'cases_manifest.json')))
    rows=[]
    for case in manifest['cases']:
        folder=OUT/'cases'/case['case_id'];fixture=json.loads((folder/'fixture.json').read_text())
        assert fixture['physics_steps']==0 and fixture['max_scan_s']<=.1
        for name,expected in fixture['files'].items():assert sha(folder/name)==expected,name
        for repetition in range(1,6):
            dest=OUT/'scored'/case['case_id']/f'rep{repetition:02d}';dest.mkdir(parents=True,exist_ok=False)
            command=[sys.executable,str(HERE/'build_remote.py'),'/evaluation/cases/'+case['case_id'],
                '/evaluation/scored/'+case['case_id']+f'/rep{repetition:02d}']
            began=time.monotonic()
            with (dest/'stdout.log').open('x') as log:
                try:code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=120).returncode
                except subprocess.TimeoutExpired:code=124
            result=summarize(dest,code,time.monotonic()-began)
            result.update(case_id=case['case_id'],repetition=repetition)
            write(dest/'summary.json',result);rows.append(result)
            write(OUT/'matrix_progress.json',rows)
            print(json.dumps(dict(case_id=case['case_id'],rep=repetition,global_pass=result['global_admitted'],
                local_pass=result['scan_published'],overall=result['end_to_end_pass'],exit_code=code)),flush=True)
    strata={};excluded=[];selected=[]
    for name,order in (('oblique_entry',['A02','A03','A04']),('new_destination',['G07','G05','G06']),('reverse',['R11','R10','R12'])):
        for case_id in order:
            calls=[r for r in rows if r['case_id']==case_id]
            eligible=len(calls)==5 and all(r['end_to_end_pass'] for r in calls)
            if eligible:
                case=next(c for c in manifest['cases'] if c['case_id']==case_id)
                selected.append(dict(case_id=case_id,stratum=name,scenario_sha256=case['scenario_sha256']))
                break
            excluded.append(dict(case_id=case_id,stratum=name,passed=sum(r['end_to_end_pass'] for r in calls),total=len(calls)))
    write(OUT/'selection.json',dict(selected=selected,excluded=excluded,predeclared_order=True,
        cases_manifest_sha256=sha(OUT/'cases_manifest.json'),scored_calls=len(rows)))
    by_case=[]
    for case in manifest['cases']:
        calls=[r for r in rows if r['case_id']==case['case_id']]
        by_case.append(dict(case_id=case['case_id'],direction=case['direction'],denominator=len(calls),
            first_gpmp_static_pass=sum(r['first_gpmp_static_pass'] for r in calls),
            global_admitted=sum(r['global_admitted'] for r in calls),
            scan_first_published=sum(r['scan_published'] for r in calls),
            end_to_end_pass=sum(r['end_to_end_pass'] for r in calls),
            reference_goal_search_calls=sum(r['metrics'].get('reference_goal_search_calls',0) for r in calls),
            edge_margin_min=min((r['edge_margin_min'] for r in calls if r['edge_margin_min'] is not None),default=None),
            raw_solid_margin_min=min((r['raw_solid_margin_min'] for r in calls if r['raw_solid_margin_min'] is not None),default=None),
            global_time_s=[r['metrics'].get('global_s') for r in calls],
            local_time_s=[r['metrics'].get('scan_first_round_s') for r in calls]))
    write(OUT/'matrix_summary.json',dict(calls=rows,by_case=by_case,selection=selected,
        margin_cap_m=.15,room_coverage='Building top floor is open hall/corridors/corners; distinct rooms unavailable',
        timing_mode='fixed ROS capture epoch; measured steady-clock native durations; no live scheduling claim'))

if __name__=='__main__':main()

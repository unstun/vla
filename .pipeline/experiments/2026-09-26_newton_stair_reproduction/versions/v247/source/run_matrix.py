"""Frozen unchanged v24212x5 protocol, with explicit optimization failures."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
BASE=Path('/data/sun/vla_mppi_20261009')
OUT=BASE/'physical_traversability_v247/evaluation'
WORK=BASE/'physical_traversability_v247/native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')

def summarize(folder,code,elapsed):
    spec=importlib.util.spec_from_file_location('original_protocol',HERE.parent/'v242/run_matrix.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    row=old.summarize(folder,code,elapsed)
    log=(folder/'stdout.log').read_text(errors='replace')
    optimization=sorted(set(map(int,re.findall(r'pct_optimizer_rejected attempt=(\d+)',log))))
    row['optimizer_rejected_attempts']=optimization
    rejected=set(row['rejected_gpmp_attempts'])|set(optimization)
    row['first_gpmp_static_pass'] &= 0 not in rejected
    row['graph_fallback_attempted']=1 in rejected
    if row['global_admitted']:
        route=list(csv.DictReader((folder/'route.csv').open()))
        row['returned_first_xyz']=[float(route[0][k]) for k in ('x','y','z')]
        row['returned_goal_xyz']=[float(route[-1][k]) for k in ('x','y','z')]
    return row

def main():
    frozen=json.loads((HERE/'manifest.json').read_text())
    for rel,h in frozen['source_files'].items():assert sha(HERE/rel)==h,rel
    for name in ('source_inventory','installed_files'):
        for rel,h in json.loads((HERE/'results'/(name+'.json')).read_text()).items():assert sha(WORK/rel)==h,rel
    assert sha(HERE.parent/'v242/cases_manifest.json')==frozen['cases_manifest_sha256']
    policy=BASE/'repo/.pipeline/experiments/2026-09-26_newton_macos_policy/policy/policy_stateless_h10.onnx'
    assert sha(policy)=='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b'
    manifest=json.loads((HERE.parent/'v242/cases_manifest.json').read_text())
    rows=[]
    for case in manifest['cases']:
        cid=case['case_id'];folder=BASE/'generalization_v242/cases'/cid
        fixture=json.loads((folder/'fixture.json').read_text())
        assert fixture['physics_steps']==0 and fixture['max_scan_s']<=.1
        for name,h in fixture['files'].items():assert sha(folder/name)==h,name
        for repetition in range(1,6):
            target=OUT/'scored'/cid/f'rep{repetition:02d}'
            target.mkdir(parents=True,exist_ok=False);began=time.monotonic()
            with (target/'stdout.log').open('x') as log:
                try:code=subprocess.run([sys.executable,str(HERE/'probe.py'),'/task/generalization_v242/cases/'+cid,
                    '/evaluation/scored/'+cid+f'/rep{repetition:02d}'],stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
                except subprocess.TimeoutExpired:code=124
            row=summarize(target,code,time.monotonic()-began)
            row.update(case_id=cid,repetition=repetition)
            if row['global_admitted']:
                goal=case['goal']['ground'][:2]+[case['goal']['ground'][2]+.3]
                row['goal_max_error_m']=max(abs(a-b) for a,b in zip(goal,row['returned_goal_xyz']))
                row['end_to_end_pass'] &= row['goal_max_error_m']<1e-5
            write(target/'summary.json',row);rows.append(row);write(OUT/'matrix_progress.json',rows)
            print(json.dumps(dict(case_id=cid,rep=repetition,global_pass=row['global_admitted'],
                scan_pass=row['scan_published'],overall=row['end_to_end_pass'])),flush=True)
    table=[]
    for case in manifest['cases']:
        calls=[r for r in rows if r['case_id']==case['case_id']]
        minimum=lambda key:min((r[key] for r in calls if r[key] is not None),default=None)
        table.append(dict(case_id=case['case_id'],denominator=len(calls),
            first_gpmp_static_pass=sum(r['first_gpmp_static_pass'] for r in calls),
            global_admitted=sum(r['global_admitted'] for r in calls),
            scan_first_published=sum(r['scan_published'] for r in calls),
            end_to_end_pass=sum(r['end_to_end_pass'] for r in calls),
            graph_fallback_calls=sum(r['graph_fallback_attempted'] for r in calls),
            edge_margin_min=minimum('edge_margin_min'),raw_solid_margin_min=minimum('raw_solid_margin_min'),
            observed_point_margin_min=minimum('observed_point_margin_min'),
            global_time_s=[r['metrics'].get('global_s') for r in calls],
            local_time_s=[r['metrics'].get('scan_first_round_s') for r in calls]))
    selected=[];excluded=[]
    for stratum,order in (('oblique_entry',['A02','A03','A04']),('new_destination',['G07','G05','G06']),('reverse',['R11','R10','R12'])):
        for cid in order:
            item=next(r for r in table if r['case_id']==cid)
            if item['end_to_end_pass']==5:
                case=next(c for c in manifest['cases'] if c['case_id']==cid)
                selected.append(dict(case_id=cid,stratum=stratum,scenario_sha256=case['scenario_sha256']));break
            excluded.append(dict(case_id=cid,stratum=stratum,passed=item['end_to_end_pass']))
    total=sum(r['end_to_end_pass'] for r in rows)
    gate=dict(passed=len(rows)==60 and total>=50 and len(selected)==3,
        calls=len(rows),passed_calls=total,physical_representatives_admitted=len(selected),
        all_cases_passed=total==60,scope='Native static and cold first-local admission; physical and full-goal execution unproven')
    selection=dict(selected=selected,excluded=excluded,predeclared_order=True,
        physical_admission_passed=gate['passed'],cases_manifest_sha256=frozen['cases_manifest_sha256'],scored_calls=len(rows))
    write(OUT/'selection.json',selection);write(OUT/'offline_gate.json',gate)
    write(OUT/'matrix_summary.json',dict(version='v247',control='v242',calls=rows,by_case=table,
        passed_calls=total,scored_calls=len(rows),margin_cap_m=.15,
        timing_mode='Fixed ROS capture epoch; steady-clock component durations; no live scheduling claim'))
    with (OUT/'matrix_table.csv').open('w') as file:
        writer=csv.DictWriter(file,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    print(json.dumps(gate),flush=True)

if __name__=='__main__':main()

"""Unchanged historical and measured requests; no endpoint/yaw invention."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');TAG=sys.argv[1] if len(sys.argv)>1 else 'final';OUT=BASE/('gpmp_fixed_boundary_v277/evaluation/legacy_requests_'+TAG)
assert not OUT.exists();OUT.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('metrics',HERE.parent/'v254/run_matrix.py')
metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)
saved=HERE.parents[1]/'audits/2026-10-18_v251_physical_generalization/results/measured_start02/input.txt'
values=list(map(float,next(line for line in saved.read_text().splitlines() if line.startswith('measured ')).split()[1:]))
folder=OUT/'measured_input';folder.mkdir();(folder/'endpoints.txt').write_text(' '.join(map(str,values))+'\n')
rows=[]
for cid,source,global_only in [('H00','/task/physical_traversability_v247/historical/cases/H00',False),('A02_measured','/evaluation/legacy_requests_'+TAG+'/measured_input',True)]:
    target=OUT/cid;target.mkdir();began=time.monotonic()
    with (target/'stdout.log').open('x') as log:
        result=subprocess.run([sys.executable,str(HERE/'probe.py'),source,'/evaluation/legacy_requests_'+TAG+'/'+cid],env=dict(os.environ,**({'GLOBAL_ONLY':'1'} if global_only else {})),stdout=log,stderr=subprocess.STDOUT,timeout=180)
    if (target/'route_margins.csv').exists():
        with (target/'independent_audit.log').open('x') as log:
            subprocess.run(['/home/sun/vla_exec/envs/newton_worker/bin/python',str(HERE/'independent_source_audit.py'),'route',str(target)],stdout=log,stderr=subprocess.STDOUT,check=True)
    row=metrics.summarize(target,result.returncode,time.monotonic()-began);row['case_id']=cid
    original=BASE/'physical_traversability_v247/historical/cases/H00/endpoints.txt' if cid=='H00' else folder/'endpoints.txt'
    wanted=list(map(float,original.read_text().split()))
    row['start_max_error_m']=max(abs(a-b) for a,b in zip(wanted[:3],row['returned_first_xyz']))
    row['goal_max_error_m']=max(abs(a-b) for a,b in zip(wanted[3:6],row['returned_goal_xyz']))
    row['endpoint_input_sha256']=sha(original)
    assert row['start_max_error_m']<1e-6 and row['goal_max_error_m']<1e-6,row
    assert row['global_admitted'] and row['first_gpmp_static_pass'],row
    if not global_only:assert row['end_to_end_pass'],row
    rows.append(row);(target/'summary.json').write_text(json.dumps(row,indent=2)+'\n')
historical=BASE/'physical_traversability_v247/historical/cases/H00'
(OUT/'receipt.json').write_text(json.dumps(dict(rows=rows,measured_input_sha256=sha(saved),requested_values_unchanged=True,historical_inputs={p.name:sha(p) for p in historical.iterdir() if p.is_file()}),indent=2)+'\n')
print(json.dumps([dict(case_id=r['case_id'],global_admitted=r['global_admitted'],first_gpmp=r['first_gpmp_static_pass']) for r in rows]),flush=True)

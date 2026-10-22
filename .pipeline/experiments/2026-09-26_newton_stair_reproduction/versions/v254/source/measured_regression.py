"""Exact saved v252 request: installed plugin, ENV/GPMP, dense native static review."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'generic_mechanisms_v254/evaluation'
spec=importlib.util.spec_from_file_location('candidate_metrics',HERE/'run_matrix.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
adapter.verify_frozen()
saved=EXP/'audits/2026-10-18_v251_physical_generalization/results/measured_start02'
lines=(saved/'input.txt').read_text().splitlines();values=list(map(float,next(s for s in lines if s.startswith('measured ')).split()[1:]))
original=BASE/'generalization_v242/cases/A02';fixture=OUT/'measured_fixture';fixture.mkdir(exist_ok=False)
for p in original.iterdir():
 if p.is_file() and p.name!='endpoints.txt':os.symlink(p,fixture/p.name)
(fixture/'endpoints.txt').write_text(' '.join(map(str,values))+'\n')
identity=dict(physics_steps=0,scope='Exact recorded global request, native static review only; no nominal-cloud local claim',
 saved_input_sha256=hashlib.sha256((saved/'input.txt').read_bytes()).hexdigest(),
 saved_input_identity_sha256=hashlib.sha256((saved/'input_identity.json').read_bytes()).hexdigest(),
 start=values[:3],goal=values[3:6],yaw=values[6],nominal_fixture_sha256=hashlib.sha256((original/'fixture.json').read_bytes()).hexdigest())
(fixture/'request_identity.json').write_text(json.dumps(identity,indent=2)+'\n')
target=OUT/'measured_start';target.mkdir(exist_ok=False);began=time.monotonic()
with (target/'stdout.log').open('x') as log:
 code=subprocess.run([sys.executable,str(HERE/'probe.py'),'/evaluation/measured_fixture','/evaluation/measured_start'],env=dict(os.environ,GLOBAL_ONLY='1'),stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
row=adapter.summarize(target,code,time.monotonic()-began)
row.update(case_id='A02_recorded_request',scope=identity['scope'],requested_start=values[:3],requested_goal=values[3:6])
if row['global_admitted']:
 row['start_max_error_m']=max(abs(a-b) for a,b in zip(values[:3],row['returned_first_xyz']))
 row['goal_max_error_m']=max(abs(a-b) for a,b in zip(values[3:6],row['returned_goal_xyz']))
 row['passed']=row['first_gpmp_static_pass'] and row['start_max_error_m']<1e-6 and row['goal_max_error_m']<1e-6 and not row['graph_fallback_attempted']
else:row['passed']=False
(target/'summary.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
raise SystemExit(0 if row['passed'] else 1)

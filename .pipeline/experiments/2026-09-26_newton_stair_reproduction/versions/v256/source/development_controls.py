"""One-call original twelve controls plus historical and measured endpoint replay."""
from pathlib import Path
import csv,hashlib,importlib.util,json,os,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'generic_mechanisms_v256/evaluation'
spec=importlib.util.spec_from_file_location('control_metrics',HERE.parent/'v254/run_matrix.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
TAG=os.environ.get('V256_CONTROLS_TAG','controls')
rows=[]
def call(cid,source,global_only=False):
 target=OUT/TAG/cid;target.mkdir(parents=True,exist_ok=False);began=time.monotonic()
 with (target/'stdout.log').open('x') as log:
  try:code=subprocess.run([sys.executable,str(HERE/'probe.py'),source,'/evaluation/'+TAG+'/'+cid],env=dict(os.environ,**({'GLOBAL_ONLY':'1'} if global_only else {})),stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
  except subprocess.TimeoutExpired:code=124
 if (target/'route_margins.csv').exists():
  subprocess.run(['/home/sun/vla_exec/envs/newton_worker/bin/python',str(HERE/'independent_solid_audit.py'),'route',str(target)],check=True,stdout=subprocess.DEVNULL)
 row=old.summarize(target,code,time.monotonic()-began);row['case_id']=cid
 (target/'summary.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
 print(json.dumps(dict(case_id=cid,global_admitted=row['global_admitted'],first_gpmp=row['first_gpmp_static_pass'],scan=row['scan_published'],raw_margin=row['raw_solid_margin_min'])),flush=True)
 (OUT/(TAG+'_progress.json')).write_text(json.dumps(rows,indent=2)+'\n')
for c in json.loads((HERE.parent/'v242/cases_manifest.json').read_text())['cases']:call(c['case_id'],'/task/generalization_v242/cases/'+c['case_id'])
call('H00','/task/physical_traversability_v247/historical/cases/H00')
saved=HERE.parents[1]/'audits/2026-10-18_v251_physical_generalization/results/measured_start02/input.txt'
values=list(map(float,next(line for line in saved.read_text().splitlines() if line.startswith('measured ')).split()[1:]))
f=OUT/(TAG+'_measured_request');f.mkdir();(f/'endpoints.txt').write_text(' '.join(map(str,values))+'\n')
call('A02_measured','/evaluation/'+TAG+'_measured_request',True)
(OUT/(TAG+'_summary.json')).write_text(json.dumps(dict(calls=rows,input_sha256=hashlib.sha256(saved.read_bytes()).hexdigest()),indent=2)+'\n')

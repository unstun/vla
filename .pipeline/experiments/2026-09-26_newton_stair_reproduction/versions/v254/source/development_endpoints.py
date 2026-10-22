"""Unscored development checks; preserve failures before source/evaluator freeze."""
from pathlib import Path
import importlib.util,json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'generic_mechanisms_v254/evaluation'
spec=importlib.util.spec_from_file_location('metrics',HERE/'run_matrix.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
tag=os.environ.get('V254_DEVELOPMENT_TAG','development01');root=OUT/tag;root.mkdir(exist_ok=False)
saved=EXP/'audits/2026-10-18_v251_physical_generalization/results/measured_start02'
values=next(s for s in (saved/'input.txt').read_text().splitlines() if s.startswith('measured ')).split()[1:]
fixture=root/'measured_fixture';fixture.mkdir();(fixture/'endpoints.txt').write_text(' '.join(values)+'\n')
rows=[]
manifest=json.loads((HERE.parent/'v242/cases_manifest.json').read_text())
inputs=[('recorded_A02','/evaluation/'+tag+'/measured_fixture',True)]+[(c['case_id'],'/task/generalization_v242/cases/'+c['case_id'],False) for c in manifest['cases']]
for cid,input_path,global_only in inputs:
 target=root/cid;target.mkdir();began=time.monotonic()
 with (target/'stdout.log').open('x') as log:
  code=subprocess.run([sys.executable,str(HERE/'probe.py'),input_path,'/evaluation/'+tag+'/'+cid],env=dict(os.environ,**({'GLOBAL_ONLY':'1'} if global_only else {})),stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
 row=adapter.summarize(target,code,time.monotonic()-began);row['case_id']=cid;rows.append(row)
 (target/'summary.json').write_text(json.dumps(row,indent=2)+'\n');(root/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps(dict(case=cid,first_gpmp=row['first_gpmp_static_pass'],admitted=row['global_admitted'],overall=row['end_to_end_pass'],code=code)),flush=True)

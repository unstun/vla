"""Unscored unchanged-case native development calls; no physical execution."""
from pathlib import Path
import importlib.util,json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
OUT=BASE/'physical_traversability_v247/evaluation'
spec=importlib.util.spec_from_file_location('original_metrics',HERE.parent/'v242/run_matrix.py')
metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)
tag=os.environ.get('V247_DEVELOPMENT_TAG','development03')
rows=[]
for case in json.loads((HERE.parent/'v242/cases_manifest.json').read_text())['cases']:
 cid=case['case_id'];dest=OUT/tag/cid;dest.mkdir(parents=True,exist_ok=False)
 began=time.monotonic()
 with (dest/'stdout.log').open('x') as log:
  try:code=subprocess.run([sys.executable,str(HERE/'probe.py'),'/task/generalization_v242/cases/'+cid,'/evaluation/'+tag+'/'+cid],stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
  except subprocess.TimeoutExpired:code=124
 row=metrics.summarize(dest,code,time.monotonic()-began);row['case_id']=cid
 (dest/'summary.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
 (OUT/(tag+'_progress.json')).write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps(dict(case_id=cid,global_pass=row['global_admitted'],scan_pass=row['scan_published'],overall=row['end_to_end_pass'],global_s=row['metrics'].get('global_s'),exit_code=code)),flush=True)

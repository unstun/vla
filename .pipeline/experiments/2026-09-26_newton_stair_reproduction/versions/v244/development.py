"""One diagnostic call per unchanged frozen case; excluded from scored60."""
from pathlib import Path
import json,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'endpoint_connectivity_v244/evaluation'
ledger=[]
for c in json.loads((HERE.parent/'v242/cases_manifest.json').read_text())['cases']:
 case=c['case_id'];dest=OUT/'development'/f'{case}_02';dest.mkdir(parents=True,exist_ok=False)
 with (dest/'stdout.log').open('w') as log:
  try:code=subprocess.run([sys.executable,str(HERE/'probe.py'),'/cases/'+case,'/evaluation/development/'+case+'_02'],stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
  except subprocess.TimeoutExpired:code=124
 m={}
 if (dest/'metrics.txt').exists():
  for line in (dest/'metrics.txt').read_text().splitlines():
   if '=' in line:k,v=line.split('=',1);m[k]=v
 row=dict(case_id=case,exit_code=code,metrics=m);ledger.append(row)
 (OUT/'development_summary02.json').write_text(json.dumps(ledger,indent=2)+'\n')
 print(case,code,m.get('global_admitted'),m.get('global_error'),m.get('scan_published'),m.get('global_s'),flush=True)

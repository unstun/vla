"""Development controls; six east failures stay failures, with typed evidence."""
from pathlib import Path
import os,subprocess,sys,json
HERE=Path(__file__).resolve().parent;B=Path('/data/sun/vla_mppi_20261009');out=B/'generic_mechanisms_v260/evaluation/controls04';out.mkdir(exist_ok=False);rows=[]
for cid in ('A04','G05','U11','U12','D09','D10','D11','D13'):
 d=out/cid;d.mkdir()
 with (d/'stdout.log').open('w') as log:
  code=subprocess.run([sys.executable,str(HERE/'probe.py'),'/task/space_coverage_v257/cases/'+cid,'/evaluation/controls04/'+cid],env=dict(os.environ,GLOBAL_ONLY='1'),stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
 m=dict(line.split('=',1) for line in (d/'metrics.txt').read_text().splitlines() if '=' in line)
 row=dict(case_id=cid,code=code,metrics=m);rows.append(row);print(json.dumps(row),flush=True)
(out/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n')
assert all(r['code']==0 for r in rows)
assert all(r['metrics']['global_admitted']==('1' if r['case_id'] in ('A04','G05') else '0') for r in rows)
assert all('pct_optimizer_rejected' not in (out/c/'stdout.log').read_text() for c in ('A04','G05'))

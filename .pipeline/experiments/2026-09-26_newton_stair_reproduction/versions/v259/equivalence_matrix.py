"""Same original52 requests; strict native outcome/route equivalence, no physics."""
from pathlib import Path
import csv,hashlib,json,os,statistics,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'generic_mechanisms_v259/evaluation'
TARGET=OUT/'equivalence52';TARGET.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cases=json.loads((HERE.parent/'v257/cases_manifest.json').read_text())['cases'];rows=[]
for c in cases:
 cid=c['case_id'];folder=TARGET/cid;folder.mkdir()
 with (folder/'stdout.log').open('x') as log:
  code=subprocess.run([sys.executable,str(HERE/'probe.py'),'/task/space_coverage_v257/cases/'+cid,'/evaluation/equivalence52/'+cid],env=dict(os.environ,GLOBAL_ONLY='1'),stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
 metrics=dict(line.split('=',1) for line in (folder/'metrics.txt').read_text().splitlines() if '=' in line)
 prior=BASE/'space_coverage_v257/scored'/cid;old=json.loads((prior/'summary.json').read_text())
 admitted=metrics['global_admitted']=='1';same=code==0 and admitted==old['global_admitted'] and metrics['global_error']==old['metrics']['global_error']
 route_same=sha(folder/'route.csv')==sha(prior/'route.csv') if admitted else None
 new_static={p.name:sha(p) for p in folder.glob('static_request_*.csv')};old_static={p.name:sha(p) for p in prior.glob('static_request_*.csv')}
 same &= new_static==old_static and (route_same is not False)
 row=dict(case_id=cid,code=code,global_admitted=admitted,global_s=float(metrics['global_s']),old_global_s=old['metrics']['global_s'],exact_route_csv=route_same,exact_static_requests=new_static==old_static,equivalent=bool(same),rejection=metrics['global_error'])
 (folder/'comparison.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row);(TARGET/'progress.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
times=[r['global_s'] for r in rows if r['global_admitted']]
receipt=dict(passed=all(r['equivalent'] for r in rows) and statistics.median(times)<=1.5,cases=52,equivalent=sum(r['equivalent'] for r in rows),admitted=len(times),median_global_s=statistics.median(times),max_global_s=max(times),target_median_max_s=1.5,quota_cpus=2,physics_steps=0,scope='Equivalent accelerator regression against original frozen v257; no new floor or yaw treatment')
(TARGET/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
with (TARGET/'table.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps(receipt),flush=True)

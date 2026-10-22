"""Check the legacy-only correction leaves every scored physical route unchanged."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[BASE/('generic_mechanisms_'+v)/'evaluation/matrix_summary.json' for v in ('v253','v254')]
a,b=[json.loads(p.read_text()) for p in paths];pairs=[]
for x,y in zip(a['calls'],b['calls']):
 assert (x['case_id'],x['repetition'])==(y['case_id'],y['repetition'])
 assert x['global_admitted']==y['global_admitted']
 if x['global_admitted']:
  pairs.append(dict(case_id=x['case_id'],repetition=x['repetition'],same_route_bytes=x['hashes']['route.csv']==y['hashes']['route.csv']))
assert len(pairs)==55 and all(p['same_route_bytes'] for p in pairs)
(HERE/'results/native_route_parity.json').write_text(json.dumps(dict(passed=True,compared_calls=60,admitted_routes=55,identical_route_files=55,inputs={str(p):sha(p) for p in paths},pairs=pairs),indent=2)+'\n')
print('55/55 admitted physical-mode route files identical',flush=True)

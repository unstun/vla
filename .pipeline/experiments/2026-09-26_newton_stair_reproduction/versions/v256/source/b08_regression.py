"""Behavioral assertion on original frozen B08 negative-margin admission."""
from pathlib import Path
import csv,json,sys
folder=Path(sys.argv[1]);m={}
for line in (folder/'metrics.txt').read_text().splitlines():
 if '=' in line:k,value=line.split('=',1);m[k]=value
rows=list(csv.DictReader((folder/'route_margins.csv').open()))
witness=min(rows,key=lambda r:float(r['raw_solid_margin']))
receipt=dict(global_admitted=m['global_admitted']=='1',static_rejected=int(m['static_rejected_samples']),witness=witness)
print(json.dumps(receipt,indent=2))
assert not receipt['global_admitted'] or float(witness['raw_solid_margin'])>=0.,'B08 admitted an original-cloud solid collision'

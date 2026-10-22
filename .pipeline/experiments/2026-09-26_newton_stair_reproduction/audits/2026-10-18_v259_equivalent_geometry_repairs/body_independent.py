"""Apply the frozen unpartitioned SciPy oracle to actual recorded body poses."""
from pathlib import Path
import csv,hashlib,json,sys
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1]
source=EXP/'versions/v257/independent_solid_audit.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((source.parent/'manifest.json').read_text())
assert sha(source)==manifest['source_files']['independent_solid_audit.py']
code=source.read_text();seam='\nmode=sys.argv[1];';assert code.count(seam)==1
namespace=dict(__file__=str(source),__name__='frozen_independent_body_oracle')
exec(compile(code.split(seam)[0],str(source),'exec'),namespace)
path=Path(sys.argv[1]);rows=list(csv.DictReader(path.open()));assert rows
errors=[];values=[]
for row in rows:
    body=namespace['np'].array([float(row[k]) for k in ('x','y','z')])
    value=namespace['oracle'](body,float(row['yaw']));values.append(value)
    errors.append(abs(value-float(row['native_solid_margin'])))
    row['independent_solid_margin_m']=value
assert max(errors)<1e-6,(len(rows),max(errors))
with path.open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
receipt=dict(queries=len(rows),minimum_independent_solid_margin_m=min(values),
    collisions=sum(v<=0. for v in values),max_native_error_m=max(errors),tolerance_m=1e-6,
    oracle='Frozen v257 unpartitioned SciPy tree and NumPy formulas; no native queries imported',
    oracle_source_sha256=sha(source),field_sha256=sha(namespace['FIELD']),
    checked_samples_sha256=sha(path),scope='Actual measured body trajectory; atlas and hard support reported separately')
(path.parent/'independent_body_solid_audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)

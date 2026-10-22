from pathlib import Path
import hashlib,shutil,json
B=Path('/data/sun/vla_mppi_20261009');out=B/'generic_mechanisms_v260/evaluation/support';work=B/'generic_mechanisms_v260/native/fixtures/building'
m=dict(line.split('=',1) for line in (out/'metrics.txt').read_text().splitlines() if '=' in line)
assert m['old_typed_mismatch']==m['field_admission_mismatch']=='0'
assert m['snapshot_fnv64']=='15212154834549674106' and m['parity_queries']=='12219'
p=out/'native.support';shutil.copyfile(p,work/p.name)
print(json.dumps(dict(snapshot_fnv64=m['snapshot_fnv64'],sha256=hashlib.sha256(p.read_bytes()).hexdigest(),native_parity=m)),flush=True)

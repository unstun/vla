from pathlib import Path
import json,hashlib,time
R=Path('/home/ubuntu/sun/vla_v289_20261020');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows={}
for label,name in [('native','native_manifest01.json'),('physical','physical_manifest01.json')]:
 m=json.loads((R/'migration'/name).read_text());bad=[rel for rel,h in m['files'].items() if sha(R/rel)!=h]
 assert not bad,bad
 rows[label]=dict(files=len(m['files']),manifest_sha256=sha(R/'migration'/name),mismatches=bad)
(R/'evidence/execution_remote_verification01.json').write_text(json.dumps(dict(passed=True,manifests=rows,physics_steps=0,utc_s=time.time()),indent=2)+'\n')
print(json.dumps(rows))

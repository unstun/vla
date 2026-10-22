"""Return missing compact bindings; keep heavy immutable geometry on ultra9."""
from pathlib import Path
import hashlib
import json
import shutil

R=Path('/home/ubuntu/sun/vla_v290_20261021')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=R/'migration/physical_manifest01.json'
m=json.loads(manifest.read_text())
out=R/'dependency_return01';out.mkdir(exist_ok=False)
request=json.loads((R/'evidence/dependency_request01.json').read_text())
result=dict(physical_manifest_sha256=sha(manifest),returned={},remote_retained={},all_remote_files_verified=False)
for rel,digest in m['files'].items():assert sha(R/rel)==digest,rel
result['all_remote_files_verified']=True
for rel in request:
    p=R/rel;assert sha(p)==m['files'][rel]
    if p.stat().st_size<=256*1024:
        q=out/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
        result['returned'][rel]=sha(q)
    else:
        result['remote_retained'][rel]=dict(sha256=sha(p),bytes=p.stat().st_size,storage=str(p),
            source='Byte-identical private copy of frozen v289 native fixtures; descriptors and original construction sources are retained.')
(out/'return_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
(R/'evidence/dependency_return01.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(returned=len(result['returned']),remote_retained=len(result['remote_retained']),all_remote_files_verified=True)))

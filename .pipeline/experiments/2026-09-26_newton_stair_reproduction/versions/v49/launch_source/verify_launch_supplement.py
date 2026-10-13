"""Verify append-only launch completion without rewriting the original freeze."""
from pathlib import Path
import hashlib,json
v=Path(__file__).resolve().parent
root=v.parents[4]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((v/'launch_supplement.json').read_text())
assert sha(v/'manifest.json')==s['base_manifest_sha256']
for name,digest in s['source_files'].items(): assert sha(root/name)==digest,name
parent=root/s['parent_launcher']
assert sha(parent)==s['parent_sha256']
assert (v/'native_graph.py').read_text()==parent.read_text().replace('v48','v49')
print('v49 append-only launcher identity verified; frozen manifest unchanged')

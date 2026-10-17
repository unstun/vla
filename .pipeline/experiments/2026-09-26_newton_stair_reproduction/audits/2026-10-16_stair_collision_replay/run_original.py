"""Run the unchanged initial ROS 2 map with two explicitly named geometries."""
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from remote_runner import ROOT,run,docker

manifest=json.loads((ROOT/'source/reference_manifest.json').read_text())
for name,entry in manifest.items():
    assert hashlib.sha256((ROOT/'reference'/name).read_bytes()).hexdigest()==entry['sha256'],name
image=json.loads((ROOT/'environment.json').read_text())['image']
if run('original_build01',docker(image,['/audit/source/original/build.sh'])):raise SystemExit(1)
with ThreadPoolExecutor(max_workers=2) as pool:
    codes=list(pool.map(lambda mode:run('original_'+mode+'01',docker(image,['/audit/source/original/run.sh',mode]),900),['author','current']))
raise SystemExit(max(codes))

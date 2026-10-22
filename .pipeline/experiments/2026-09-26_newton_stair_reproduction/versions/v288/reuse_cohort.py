"""Reuse every frozen v283 endpoint, captured scan and start certificate unchanged."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
PARENT=Path('/home/sun/vla_exec/navigation_geometry_v283/cohort')
OUT=Path('/home/sun/vla_exec/local_cost_crash_v288/cohort')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((HERE.parent/'v283/native_manifest.json').read_text())
assert sha(PARENT/'cases_manifest.json')==manifest['cohort_sha256']
for cid,h in manifest['fixtures'].items():
    folder=PARENT/'cases'/cid
    assert sha(folder/'fixture.json')==h
    for rel,value in json.loads((folder/'fixture.json').read_text())['files'].items():
        assert sha(folder/rel)==value,(cid,rel)
assert not OUT.exists()
shutil.copytree(PARENT,OUT,symlinks=False,ignore=shutil.ignore_patterns('warp-cache'))
assert sha(OUT/'cases_manifest.json')==manifest['cohort_sha256']
(OUT/'v288_reuse.json').write_text(json.dumps(dict(parent='v283',all_53_endpoints_and_captures_unchanged=True,
    parent_native_manifest_sha256=sha(HERE.parent/'v283/native_manifest.json'),cohort_sha256=manifest['cohort_sha256'],
    planner_scores_used=False,physics_steps=0),indent=2)+'\n')
print('Reused frozen 50+3 cohort; no endpoint selection or physics')

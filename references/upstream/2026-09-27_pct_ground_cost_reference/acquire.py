"""Import the exact clean generator that produced the already-pinned map."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
CACHE=Path('/Users/sun/tongbu/study/phdproject/machine-dog-nav/references/upstream/2026-09-04_pct_scan_stairs/PCT-SCAN-ROS2')
PIN='1cf45a1c12ca785ce533293302be09d51daf0ccb'
def git(*args):return subprocess.check_output(['git','-C',str(CACHE),*args])
assert git('rev-parse','HEAD').decode().strip()==PIN
assert git('branch','--show-current').decode().strip()=='main'
assert not git('status','--porcelain').strip()
files=['scripts/generate_pct_tomogram.py','LICENSE','LICENSES/GPL-2.0-or-later.txt','THIRD_PARTY_NOTICES.md','src/pct/tomography/tomography/kernels.py','src/pct/tomography/tomography/tomogram.py','src/pct/NOTICE']
records=[]
for name in files:
 raw=git('show',PIN+':'+name);dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 records.append({'path':str(dest.relative_to(HERE)),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'url':'https://raw.githubusercontent.com/yagami-light7/PCT-SCAN-ROS2/'+PIN+'/'+name})
assert records[0]['sha256']=='6de22d1dd7fb3b2295d1d570011ede8b2f16dbcf72b48b1118e5270c300a55b0'
generation=Path('/Users/sun/tongbu/study/phdproject/machine-dog-nav/.pipeline/experiments/2026-09-08_new_building_pct/runs/preflight03/generation.json')
(HERE/'historical_generation.json').write_bytes(generation.read_bytes())
(HERE/'provenance.json').write_text(json.dumps({'repo':'https://github.com/yagami-light7/PCT-SCAN-ROS2','commit':PIN,'branch':'main','clean_checkout_verified':True,'transport_cache':str(CACHE),'license':'PCT-derived tomography: GPL-2.0-or-later; multi-license notices retained','files':records,'modifications':'None. Diagnostic wrapper observes raw-cost local arrays at function return; source untouched.','historical_generation_sha256':hashlib.sha256(generation.read_bytes()).hexdigest()},indent=2)+'\n')
print(len(records))

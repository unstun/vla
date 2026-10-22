"""Record the real v285 defect signal before changing v286 production code."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

HERE=Path(__file__).resolve().parent
VERSION=HERE.parents[1]/'versions/v286'
ROOT=Path('/home/sun/vla_exec/supported_air_refinement_v286')
ROOT.mkdir(parents=True,exist_ok=True)
tag=os.environ.get('V286_PARENT_ID','01');assert len(tag)==2 and tag.isdigit()
receipt=ROOT/f'parent_probe{tag}.json'
assert not receipt.exists()
row=dict(started_utc_s=time.time(),physics_steps=0,stage='building_parent_probe',checks=[],
    probe_source_sha256=hashlib.sha256((VERSION/'repair_probe.cpp').read_bytes()).hexdigest())
receipt.write_text(json.dumps(row,indent=2)+'\n')
for mode in ['repair-build','repair']:
    log=ROOT/f'parent_{mode}{tag}.log'
    with log.open('x') as stream:
        code=subprocess.run(['python3',str(VERSION/'run_native.py'),'--parent',mode],stdout=stream,stderr=subprocess.STDOUT).returncode
    row['checks'].append(dict(mode=mode,returncode=code,log=str(log),sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
    receipt.write_text(json.dumps(row,indent=2)+'\n')
    if mode=='repair-build' and code!=0:break
row.update(stage='parent_probe_closed',finished_utc_s=time.time())
receipt.write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps(row))

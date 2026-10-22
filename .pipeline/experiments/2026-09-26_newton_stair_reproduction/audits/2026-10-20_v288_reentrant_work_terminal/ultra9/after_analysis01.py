"""Close the evidence package after existing recordings have been analyzed."""
from pathlib import Path
import json
import subprocess
import time
R=Path('/home/ubuntu/sun/vla_v288_20261020')
P='/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python'
receipt=R/'evidence/post_analysis01.json'
assert not receipt.exists()
def save(**data):receipt.write_text(json.dumps(data,indent=2)+'\n')
save(stage='waiting_for_existing_analysis',physics_steps=0)
while True:
    p=R/'evidence/after_physics01.json'
    d=json.loads(p.read_text()) if p.exists() else {}
    if d.get('stage')=='analysis_closed':
        assert d['returncode']==0,d
        break
    time.sleep(20)
for script in ('startup_audit.py','input_order_audit.py','boundary_state.py','boundary_witness.py','collect_results.py'):
    save(stage=script,physics_steps=0)
    code=subprocess.run([P,str(R/'migration'/script)]).returncode
    if code:
        save(stage='failed',script=script,returncode=code,physics_steps=0)
        raise SystemExit(code)
save(stage='complete',physics_steps=0)
print('All original-recording evidence collected; no physics rerun',flush=True)

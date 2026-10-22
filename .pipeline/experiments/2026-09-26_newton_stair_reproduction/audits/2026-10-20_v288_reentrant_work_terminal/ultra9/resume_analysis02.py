"""Retry analysis only after a preserved version-label KeyError; never physics."""
from pathlib import Path
import json
import shutil
import subprocess
R=Path('/home/ubuntu/sun/vla_v288_20261020')
P='/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python'
old=R/'evidence/analysis_batch_status.json'
shutil.copy2(old,R/'evidence/analysis_batch_status01_failed.json')
receipt=R/'evidence/after_physics02.json';assert not receipt.exists()
def save(**d):receipt.write_text(json.dumps(d,indent=2)+'\n')
save(stage='closed_recording_analysis',physics_steps=0,original_failure='after_physics01.json')
code=subprocess.run([P,str(R/'migration/analyze_all.py')]).returncode
save(stage='analysis_closed',returncode=code,physics_steps=0,original_failure='after_physics01.json')
if code:raise SystemExit(code)
post=R/'evidence/post_analysis02.json'
for name in ('startup_audit.py','input_order_audit.py','boundary_state.py','boundary_witness.py','collect_results.py'):
    post.write_text(json.dumps(dict(stage=name,physics_steps=0),indent=2)+'\n')
    code=subprocess.run([P,str(R/'migration'/name)]).returncode
    if code:
        post.write_text(json.dumps(dict(stage='failed',script=name,returncode=code,physics_steps=0),indent=2)+'\n')
        raise SystemExit(code)
post.write_text(json.dumps(dict(stage='complete',physics_steps=0),indent=2)+'\n')

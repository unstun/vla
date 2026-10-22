"""After strict53 closure, prepare ten zero-step preflights; stop before physics."""
from pathlib import Path
import subprocess,time,json,hashlib
R=Path('/home/ubuntu/sun/vla_v289_20261020')
out=R/'evidence/after_offline01.json'
assert not out.exists()
state=dict(stage='waiting_for_complete_frozen53',physics_steps=0)
out.write_text(json.dumps(state,indent=2)+'\n')
while not (R/'evidence/offline_matrix01_closed.json').exists():time.sleep(5)
closed=json.loads((R/'evidence/offline_matrix01_closed.json').read_text())
assert closed['returncode']==0 and closed['gate']['passed'],closed
for name,args in [('admission01',['execution_policy.py','--record']),
                  ('physical_preflight01',['batch.py','preflight']),
                  ('physical_freeze01',['physical_setup.py','freeze'])]:
    state['stage']=name;out.write_text(json.dumps(state,indent=2)+'\n')
    log=R/'evidence'/(name+'.log')
    with log.open('x') as f:code=subprocess.run(['python3',str(R/'migration'/args[0]),*args[1:]],stdout=f,stderr=subprocess.STDOUT).returncode
    if code:
        state.update(stage='failed',failed_step=name,returncode=code)
        out.write_text(json.dumps(state,indent=2)+'\n');raise SystemExit(code)
state.update(stage='ready_for_local_manifest_return',physical_manifest_sha256=hashlib.sha256((R/'migration/physical_manifest01.json').read_bytes()).hexdigest())
out.write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(state))

from pathlib import Path
import subprocess,json
R=Path('/home/ubuntu/sun/vla_v289_20261020')
assert json.loads((R/'evidence/build04_closed.json').read_text())['passed']
for name in ('health_group_control03.py','components03.py','bind01.py'):
 code=subprocess.run(['python3',str(R/'migration'/name)]).returncode
 if code:raise SystemExit(code)
with (R/'evidence/geometry_contract01.log').open('x') as f:
 subprocess.run(['python3',str(R/'run_native.py'),'contract'],stdout=f,stderr=subprocess.STDOUT,check=True)

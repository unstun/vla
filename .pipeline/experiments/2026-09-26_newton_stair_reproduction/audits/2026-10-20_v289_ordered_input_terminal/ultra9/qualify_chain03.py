from pathlib import Path
import subprocess,json
R=Path('/home/ubuntu/sun/vla_v289_20261020')
assert json.loads((R/'evidence/components02.json').read_text())['stage']=='passed'
for name in ('build04.py','health_group_control02.py','components03.py'):
 code=subprocess.run(['python3',str(R/'migration'/name)]).returncode
 if code:raise SystemExit(code)

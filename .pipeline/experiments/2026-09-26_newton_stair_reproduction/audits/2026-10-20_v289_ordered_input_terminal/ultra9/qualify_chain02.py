from pathlib import Path
import subprocess
R=Path('/home/ubuntu/sun/vla_v289_20261020')
for name in ('build03.py','components02.py'):
 code=subprocess.run(['python3',str(R/'migration'/name)]).returncode
 if code:raise SystemExit(code)

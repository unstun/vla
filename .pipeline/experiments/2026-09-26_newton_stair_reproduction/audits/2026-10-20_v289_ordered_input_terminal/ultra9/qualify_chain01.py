from pathlib import Path
import subprocess,json,time
R=Path('/home/ubuntu/sun/vla_v289_20261020')
for name in ('build02.py','body_order_control.py','components01.py'):
 code=subprocess.run(['python3',str(R/'migration'/name)]).returncode
 if code:raise SystemExit(code)

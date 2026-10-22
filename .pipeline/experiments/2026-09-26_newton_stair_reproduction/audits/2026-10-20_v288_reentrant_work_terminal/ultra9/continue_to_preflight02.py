"""Continue the same frozen batch under the explicit timing-only exception."""
from pathlib import Path
import json
import subprocess
import time
import execution_policy
R=Path('/home/ubuntu/sun/vla_v288_20261020')
while not (R/'benchmark/complete.json').exists():
    time.sleep(10)
print(json.dumps(execution_policy.verify()), flush=True)
assert json.loads((R/'evidence/trace_probe02.json').read_text())['passed']
subprocess.run(['python3',str(R/'migration/batch.py'),'preflight'],check=True)
subprocess.run(['python3',str(R/'migration/physical_setup.py'),'freeze'],check=True)
print('Physical execution frozen; waiting for local manifest return before any physics',flush=True)

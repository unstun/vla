from pathlib import Path
import json,subprocess,time
R=Path('/home/ubuntu/sun/vla_v287_20261020')
while not (R/'benchmark/complete.json').exists():
 time.sleep(10)
gate=json.loads((R/'benchmark/offline_gate.json').read_text());assert gate['passed'],gate
assert json.loads((R/'evidence/trace_probe01.json').read_text())['passed']
subprocess.run(['python3',str(R/'migration/batch.py'),'preflight'],check=True)
subprocess.run(['python3',str(R/'migration/physical_setup.py'),'freeze'],check=True)
print('Physical execution frozen; waiting for local manifest return before any physics',flush=True)

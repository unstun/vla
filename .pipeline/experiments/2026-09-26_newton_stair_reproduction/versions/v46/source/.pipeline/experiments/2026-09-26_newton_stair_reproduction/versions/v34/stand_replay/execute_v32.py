from pathlib import Path
import json,subprocess,time
p=Path(__file__).resolve().parent;r=json.loads((p/'request_v32.json').read_text());t=time.monotonic()
with (p/'execution_v32.log').open('w') as f:
 result=subprocess.run(r['command'],stdout=f,stderr=subprocess.STDOUT,timeout=r['deadline_s'])
(p/'execution_v32.json').write_text(json.dumps({'exit_code':result.returncode,'wall_s':time.monotonic()-t},indent=2)+'\n')
print(result.returncode)
raise SystemExit(result.returncode)

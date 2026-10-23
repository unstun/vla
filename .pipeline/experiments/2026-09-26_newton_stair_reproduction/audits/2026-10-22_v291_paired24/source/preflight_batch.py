"""Zero-step native/profile/activation barrier before the paired campaign."""
from common import *
import subprocess,sys,time
receipt=CAMPAIGN/'evidence/preflights01.json';assert not receipt.exists();rows=[]
for variant in ('v290','v291'):
 env=dict(os.environ,PAIR_VARIANT=variant)
 out=subprocess.check_output(['/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python',str(BINDING/'newton_episode.py'),'--activation-only'],env=env,text=True)
 (CAMPAIGN/'evidence'/f'{variant}_activation.json').write_text(out)
 for case in ('D07','CD12','S04','A04'):
  log=CAMPAIGN/'evidence'/f'preflight01_{variant}_{case}.log';start=time.monotonic()
  with log.open('x') as f:code=subprocess.run([sys.executable,str(BINDING/'launch.py'),'--preflight-only'],env=dict(env,PAIR_CASE=case,PAIR_REPEAT='1'),stdout=f,stderr=subprocess.STDOUT).returncode
  rows.append(dict(variant=variant,case_id=case,code=code,wall_s=time.monotonic()-start,log_sha256=sha(log),physics_steps=0));receipt.write_text(json.dumps(dict(passed=False,rows=rows),indent=2)+'\n');print(rows[-1],flush=True)
  if code:raise SystemExit(code)
receipt.write_text(json.dumps(dict(passed=True,rows=rows),indent=2)+'\n')

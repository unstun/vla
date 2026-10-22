"""Retry only display generation after fixing a manifest-path adapter; no physics."""
from pathlib import Path
import importlib.util,json,os,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
results=[]
for cid in ('A02','G07','R11'):
 root=HERE/'physical'/cid;old=root/'render_attempt01_source';old.mkdir(exist_ok=False)
 for name in ('source_identity.json','postprocess_case.py','executed_render_run.py','executed_render_adapter.py'):
  if (root/name).exists():shutil.copy2(root/name,old/name)
 env=dict(os.environ,V252_CASE_ID=cid,V252_RENDER_ID='02')
 code="import importlib.util; p="+repr(str(HERE/'postprocess_case.py'))+"; s=importlib.util.spec_from_file_location('render_only',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.render()"
 began=time.time()
 with (BASE/f'v252_{cid}_render02.log').open('x') as log:
  result=subprocess.run([sys.executable,'-c',code],env=env,stdout=log,stderr=subprocess.STDOUT)
 results.append(dict(case_id=cid,exit_code=result.returncode,wall_s=time.time()-began,physics_steps=0))
 (HERE/'results/render_status02.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results[-1]),flush=True)

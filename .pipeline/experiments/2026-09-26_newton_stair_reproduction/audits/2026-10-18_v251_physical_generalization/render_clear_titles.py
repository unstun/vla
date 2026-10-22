"""Display-only title shortening after visual QA; independent case renders in parallel."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,os,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
def render(cid):
 root=HERE/'physical'/cid;old=root/'render_attempt02_source';old.mkdir(exist_ok=False)
 for name in ('source_identity.json','postprocess_case.py','executed_render_run.py','executed_render_adapter.py'):
  if (root/name).exists():shutil.copy2(root/name,old/name)
 code="import importlib.util; p="+repr(str(HERE/'postprocess_case.py'))+"; s=importlib.util.spec_from_file_location('render_only',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.render()"
 began=time.time()
 with (BASE/f'v252_{cid}_render03.log').open('x') as log:
  code=subprocess.run([sys.executable,'-c',code],env=dict(os.environ,V252_CASE_ID=cid,V252_RENDER_ID='03'),stdout=log,stderr=subprocess.STDOUT).returncode
 return dict(case_id=cid,exit_code=code,wall_s=time.time()-began,physics_steps=0)
rows=[]
with ThreadPoolExecutor(max_workers=3) as pool:
 futures=[pool.submit(render,c) for c in ('A02','G07','R11')]
 for future in as_completed(futures):
  row=future.result();rows.append(row);(HERE/'results/render_status03.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)

from pathlib import Path
import json,os,subprocess,sys
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
rows=json.loads((HERE/'results/batch_status.json').read_text());assert len(rows)==1 and rows[0]['stage']!='running'
with (BASE/'v255_A02_postprocess01.log').open('x') as log:
 code=subprocess.run([sys.executable,str(HERE/'postprocess_case.py')],env=dict(os.environ,V255_CASE_ID='A02'),stdout=log,stderr=subprocess.STDOUT).returncode
(HERE/'results/postprocess_status.json').write_text(json.dumps(dict(case_id='A02',returncode=code,physics_steps=0),indent=2)+'\n')
raise SystemExit(code)

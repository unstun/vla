"""Unscored pre-freeze development checks; never overwrite the formal 53 ledger."""
from pathlib import Path
import json
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/sun/vla_exec/static_continuity_v284')
assert not (HERE/'native_manifest.json').exists()
output=ROOT/'development04'
output.mkdir(exist_ok=False)
for case in ('A04','D07','S04','CD12','CE03'):
    folder=output/case
    folder.mkdir()
    with (folder/'stdout.log').open('x') as log:
        code=subprocess.run([sys.executable,str(HERE/'run_native.py'),'case',str(ROOT/'cohort/cases'/case),str(folder)],
            stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
    metrics=dict(line.split('=',1) for line in (folder/'metrics.txt').read_text().splitlines() if '=' in line)
    row=dict(case_id=case,unscored_development=True,exit_code=code,metrics={k:metrics[k] for k in ('global_s','global_admitted','scan_first_publish_s','scan_published','global_error')})
    (folder/'development.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)

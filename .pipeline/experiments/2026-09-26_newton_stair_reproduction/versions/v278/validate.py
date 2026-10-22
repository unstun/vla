"""Sequential candidate build, regression and hard-route timing controls."""
from pathlib import Path
import json, os, subprocess, sys
HERE=Path(__file__).resolve().parent
BASE=Path('/data/sun/vla_mppi_20261009/source_free_index_v278')
tag=sys.argv[1];assert tag.isdigit()
BASE.mkdir(parents=True,exist_ok=True)
def run(name,args,env=None):
    p=BASE/(name+tag+'.log')
    with p.open('x') as log:
        subprocess.run([sys.executable,*map(str,args)],stdout=log,
            stderr=subprocess.STDOUT,env=env,check=True)
run('prepare',[HERE/'prepare.py'])
run('prepare_surface',[HERE/'prepare_surface.py'])
run('build',[HERE/'build.py'])
for name,operation in [('probe_build','build'),('surface','surface'),('unit','test'),
                       ('rotation','rotation'),('differential','differential'),
                       ('support_differential','support_differential'),
                       ('environmental_differential','environmental_differential')]:
    run(name,[HERE/'probe.py',operation])
run('regressions',[HERE/'regressions.py'])
controls=[]
for case in ('A04','G05','D07','S04','E02','E03'):
    target=BASE/'evaluation'/('controls'+tag)/case
    run(case+'_profile',[HERE/'probe.py','/task/space_coverage_v257/cases/'+case,
        '/evaluation/controls'+tag+'/'+case],env=dict(os.environ,GLOBAL_ONLY='1'))
    metrics=dict(line.split('=',1) for line in (target/'metrics.txt').read_text().splitlines() if '=' in line)
    controls.append(dict(case_id=case,metrics=metrics))
p=BASE/'evaluation'/('controls'+tag)/'receipt.json'
p.write_text(json.dumps(controls,indent=2)+'\n')
run('legacy_requests',[HERE/'legacy_requests.py',tag])
print(json.dumps(controls),flush=True)

"""Recorded worst soft-margin witnesses; no new route or physics call."""
from pathlib import Path
import csv,json,os,subprocess
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'v282_analysis_preflight'
rows=[]
for cohort,cid in [('clean50','CE03'),('original52','E03')]:
 p=BASE/'source_integrated_benchmark_v281'/cohort/cid/'route_margins.csv';r=min(csv.DictReader(p.open()),key=lambda r:float(r['edge_margin']));rows.append(dict(case_id=cid,cohort=cohort,record=r))
with (OUT/'edge_witnesses.txt').open('w') as f:
 for r in rows:f.write(' '.join([r['case_id']]+[r['record'][k] for k in ('x','y','z','yaw')])+'\n')
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /work/install/setup.bash && cmake -S /source -B /audit/build -DCMAKE_BUILD_TYPE=Release && cmake --build /audit/build --target edge_diagnostic -j1 && /audit/build/edge_diagnostic /audit/edge_witnesses.txt > /audit/edge_diagnostic.jsonl'
with (OUT/'edge_diagnostic01.log').open('x') as f:
 subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=1','--memory=2g','-v',str(BASE)+':/task:ro','-v',str(BASE/'source_physical_integration_v280/native')+':/work:ro','-v',str(HERE)+':/source:ro','-v',str(OUT)+':/audit:rw','--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],stdout=f,stderr=subprocess.STDOUT,check=True)
answers=[json.loads(l) for l in (OUT/'edge_diagnostic.jsonl').read_text().splitlines()]
assert len(answers)==2
for r,a in zip(rows,answers):assert abs(float(r['record']['edge_margin'])-a['ENV_edge_m'])<1e-12 and a['hard_radius_m']==.35 and a['hard_support_verdict']==0
(OUT/'edge_diagnostic_receipt.json').write_text(json.dumps(dict(witnesses=rows,answers=answers,planning_calls=0,physics_steps=0),indent=2)+'\n');print(json.dumps(answers))

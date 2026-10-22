"""Same new behavioral assertion against immutable old installed PCT; expect red."""
from pathlib import Path
import os,subprocess,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_physical_integration_v280'
cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g',
 '-v',str(BASE)+':/task:ro','-v',str(BASE/'source_surface_precompute_v272/native')+':/work:ro',
 '-v',str(OUT/'evaluation')+':/evaluation:ro','--entrypoint','/bin/bash',
 'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4',
 '/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v280/native.sh','gpmp_boundaries']
p=OUT/'parent272_boundary_red.log'
with p.open('x') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
r=dict(line.split('=',1) for line in p.read_text().splitlines() if '=' in line)
assert r['boundary_cases']=='6' and int(r['boundary_preserved'])<6 and code==1
receipt=dict(parent='v272',actual_installed_parent_read_only=True,cases=6,boundaries_preserved=int(r['boundary_preserved']),expected_red=True,exit_code=code)
(OUT/'parent272_boundary_red.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

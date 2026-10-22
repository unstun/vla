"""Isolated CPU2 component build/query, no ROS, planner install or simulation."""
from pathlib import Path
import os,subprocess,sys
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_surface_native_v270';OUT.mkdir(exist_ok=True)
source='/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v270'
operation=sys.argv[1]
if operation=='build':shell=f'cmake -S {source} -B /work/build -DCMAKE_BUILD_TYPE=Release && cmake --build /work/build -j2'
elif operation=='query':shell='exec /work/build/surface_probe "$1" "$2" < "${3:-/work/queries.txt}" > "${4:-/work/answers.txt}"'
else:raise ValueError(operation)
cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--network=none','--cpus=2','--memory=6g','-v',str(BASE)+':/task:ro','-v',str(OUT)+':/work:rw',
 '--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4',
 '-c',shell,'v270',*sys.argv[2:]]
raise SystemExit(subprocess.run(cmd).returncode)

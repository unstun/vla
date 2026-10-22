"""Separate post-score graph observer; no frozen install/build mutations."""
from pathlib import Path
import os,subprocess
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'space_coverage_v257'
AUDIT=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v256_static_solids_and_space_coverage'
(OUT/'diagnosis').mkdir(exist_ok=True)
command=r'''
set -e
source /opt/ros/foxy/setup.bash
source /task/recovery_v188/install/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
source /task/cooperative_search_v240/install/setup.bash
source /task/physical_traversability_v247/native/install/setup.bash
source /work/install/setup.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python3 - <<'PY'
from pathlib import Path
import shlex,subprocess
old=Path('/task/generic_mechanisms_v256/evaluation/build/CMakeFiles/graph_probe.dir')
flags=(old/'flags.make').read_text().splitlines()
args=[]
for key in ('CXX_DEFINES = ','CXX_INCLUDES = ','CXX_FLAGS = '):
 args.extend(shlex.split(next(x[len(key):] for x in flags if x.startswith(key))))
source='/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v256_static_solids_and_space_coverage/failure_graph_probe.cpp'
subprocess.run(['/usr/bin/c++',*args,'-c',source,'-o','/evaluation/diagnosis/probe.o'],check=True)
link=shlex.split((old/'link.txt').read_text());link[link.index('-o')+1]='/evaluation/diagnosis/probe'
link=[('/evaluation/diagnosis/probe.o' if x=='CMakeFiles/graph_probe.dir/graph_probe.cpp.o' else x) for x in link]
subprocess.run(link,check=True)
PY
/evaluation/diagnosis/probe U11 U12 U13 D09 D13 D14 E02
'''
with (OUT/'diagnosis/graph.log').open('x') as log:
 subprocess.run(['docker','run','--rm','--pull=never','--name','v257-failure-observer','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','-v',str(BASE)+':/task:ro','-v',str(BASE/'generic_mechanisms_v256/native')+':/work:ro','-v',str(OUT)+':/evaluation:rw','--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',command],stdout=log,stderr=subprocess.STDOUT,check=True)

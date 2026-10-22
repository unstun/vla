"""Inspect native endpoint indices after the fixed scored matrix; no repairs."""
from pathlib import Path
import os,subprocess

HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
OUT=BASE/'generalization_v242'
image='sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4'
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /work/install/setup.bash'
shell+=' && cmake -S /audit -B /evaluation/endpoint_build && cmake --build /evaluation/endpoint_build -j2'
shell+=' && /evaluation/endpoint_build/endpoint_inspect /evaluation/cases/*/endpoints.txt > /evaluation/endpoint_inspect02.txt'
command=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
    '--cpus=6','--memory=6g','-v',str(BASE)+':/task:ro',
    '-v',str(BASE/'cooperative_search_v240')+':/work:ro',
    '-v',str(BASE/'callback_failure_v232/fixtures')+':/work/fixtures:ro',
    '-v',str(HERE)+':/audit:ro','-v',str(OUT)+':/evaluation:rw',
    '--entrypoint','/bin/bash',image,'-c',shell]
subprocess.run(command,check=True)

"""Run the installed-v240 observer; heavy graphs stay on gpu5070ti."""
from pathlib import Path
import os,subprocess
BASE=Path('/data/sun/vla_mppi_20261009')
HERE=Path(__file__).resolve().parent
OUT=BASE/'endpoint_connectivity_v244/diagnostic'
OUT.mkdir(parents=True,exist_ok=True)
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /work/install/setup.bash'
shell+=' && cmake -S /observer -B /evaluation/build && cmake --build /evaluation/build -j2'
shell+=' && /evaluation/build/graph_dump /cases/*/endpoints.txt > /evaluation/search.log'
subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--cpus=6','--memory=6g','-v',str(BASE)+':/task:ro',
 '-v',str(BASE/'cooperative_search_v240')+':/work:ro',
 '-v',str(BASE/'callback_failure_v232/fixtures')+':/work/fixtures:ro',
 '-v',str(HERE)+':/observer:ro','-v',str(OUT)+':/evaluation:rw',
 '-v',str(BASE/'generalization_v242/cases')+':/cases:ro',
 '--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],check=True)

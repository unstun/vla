"""Build a read-only installed-field probe; evaluate retained body poses, no physics."""
from pathlib import Path
import os,subprocess,sys
HERE=Path(__file__).resolve().parent
BASE=Path('/data/sun/vla_mppi_20261009')
IMAGE='sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4'
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /work/install/setup.bash && cmake -S /audit -B /audit/work/build && cmake --build /audit/work/build -j2'
for v in ('v219','v231'):
 shell+=' && /audit/work/build/body_margin /work/fixtures/building/environment225.env 10040917858432847476 /audit/work/'+v+'_linux_full_attempt01_poses.txt /audit/work/'+v+'_linux_full_attempt01_margins.csv'
command=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '-v',str(BASE)+':/task:ro','-v',str(BASE/'blocked_feedback_v230')+':/work:ro','-v',str(HERE)+':/audit:rw',
 '--entrypoint','/bin/bash',IMAGE,'-c',shell]
subprocess.run(command,check=True)
subprocess.run([sys.executable,str(HERE/'margin_summary.py')],check=True)

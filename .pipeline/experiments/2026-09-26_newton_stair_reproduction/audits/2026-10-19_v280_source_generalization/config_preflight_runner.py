"""Read-only installed-package and actual profile checks; no physical admission."""
from pathlib import Path
import os,subprocess,sys
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'v282_analysis_preflight';OUT.mkdir(exist_ok=True)
tag=sys.argv[1];assert tag.isdigit()
version='/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v282'
audit='/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-19_v280_source_generalization'
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /work/install/setup.bash && source /task/physical_traversability_v248/native/install/local_setup.bash'
shell+=' && python3 '+version+'/preflight.py > /audit/native_package'+tag+'.json && python3 '+audit+'/config_preflight.py'
with (OUT/('configuration'+tag+'.log')).open('x') as log:
 subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=1','--memory=2g','-e','ROS_HOME=/audit/ros_home','-e','ROS_LOG_DIR=/audit/ros_logs','-e','CONFIG_PREFLIGHT_TAG='+tag,'-v',str(BASE)+':/task:ro','-v',str(BASE)+':'+str(BASE)+':ro','-v',str(BASE/'source_physical_integration_v280/native')+':/work:ro','-v',str(BASE/'geometry_physical_v282/fixtures')+':/work/fixtures:ro','-v',str(OUT)+':/audit:rw','--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],stdout=log,stderr=subprocess.STDOUT,check=True)
print('native packages and numerical source profile passed; no process/physics claim')

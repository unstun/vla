from pathlib import Path
import os,subprocess
BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'physical_traversability_v248/native'
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /task/cooperative_search_v240/install/setup.bash && source /task/physical_traversability_v247/native/install/setup.bash && source /work/install/setup.bash'
shell+=' && export V248_SOURCE=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v248 && export PYTHONPATH=/work/src/lite3_nav2_bridge:$PYTHONPATH && export TERRAIN_TEST_MANIFEST=/task/physical_traversability_v247/native/fixtures/building/terrain.json && python3 -m pytest -q /work/src/lite3_nav2_bridge/test/test_navigation_readiness.py /work/src/lite3_nav2_bridge/test/test_mission_bridge.py /work/src/lite3_nav2_bridge/test/test_binding_profile.py --junitxml=/work/readiness_tests.xml'
subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--cpus=2','--memory=2g','-e','ROS_HOME=/work/ros_home','-e','ROS_LOG_DIR=/work/ros_logs','--network=host','-e','ROS_DOMAIN_ID=143','-e','ROS_LOCALHOST_ONLY=1',
 '-v',str(BASE)+':/task:ro','-v',str(WORK)+':/work:rw','--entrypoint','/bin/bash',
 'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],check=True)

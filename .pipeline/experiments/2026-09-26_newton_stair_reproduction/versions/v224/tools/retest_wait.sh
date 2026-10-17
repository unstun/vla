#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /work/install/setup.bash
export TERRAIN_TEST_PROFILE=/work/fixtures/component.yaml
export PYTHONFAULTHANDLER=1
python3 -m pytest -q -o cache_dir=/work/evidence/wait_retry_cache /work/src/lite3_nav2_bridge/test/test_wait_recovery.py --junit-xml=/work/evidence/wait_retry01.xml

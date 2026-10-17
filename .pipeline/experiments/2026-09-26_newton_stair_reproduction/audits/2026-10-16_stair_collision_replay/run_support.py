import json
from remote_runner import ROOT,run,docker
image=json.loads((ROOT/'environment.json').read_text())['image']
if run('support_build01',docker(image,['/audit/source/build.sh'])):raise SystemExit(1)
script='set -eo pipefail\nsource /opt/ros/foxy/setup.bash\nsource /task/command_continuity_v206_20261015/install/setup.bash\nsource /task/starvation_recovery_v219/install/setup.bash\n/audit/build/support_probe --ros-args --params-file /audit/input/planner.yaml --log-level error\n'
(ROOT/'source/run_support.sh').write_text(script)
raise SystemExit(run('support_probe01',docker(image,['/audit/source/run_support.sh'])))

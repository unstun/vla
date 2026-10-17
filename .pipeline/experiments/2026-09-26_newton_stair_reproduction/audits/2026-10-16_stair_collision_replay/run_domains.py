"""Call already verified native binaries on the common region grid."""
from concurrent.futures import ThreadPoolExecutor
import json
from remote_runner import ROOT,run,docker
image=json.loads((ROOT/'environment.json').read_text())['image']
def execute(mode):
    script='set -eo pipefail\nexport REPLAY_INPUT=/audit/domain_input\nexport REPLAY_OUTPUT=/audit/output/domain_'+mode+'\nsource /opt/ros/foxy/setup.bash\n'
    if mode=='native':
        script+='source /task/command_continuity_v206_20261015/install/setup.bash\nsource /task/starvation_recovery_v219/install/setup.bash\n/audit/build/collision_probe'
    else:script+='export AUTHOR_GEOMETRY=1\n/audit/build_original/original_probe'
    script+=' --ros-args --params-file /audit/domain_input/planner.yaml --log-level error\n'
    p=ROOT/'source'/('run_domain_'+mode+'.sh');p.write_text(script)
    return run('domain_'+mode+'01',docker(image,['/audit/source/'+p.name]),900)
with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(execute,['native','original']))
raise SystemExit(max(codes))

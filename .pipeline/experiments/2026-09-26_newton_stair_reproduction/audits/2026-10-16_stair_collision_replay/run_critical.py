"""Execute bounded identical-query comparison using already built executables."""
import json
from concurrent.futures import ThreadPoolExecutor
from remote_runner import ROOT, docker, run

image=json.loads((ROOT/'environment.json').read_text())['image']
def command(mode):
    if mode=='native':
        script='source /opt/ros/foxy/setup.bash\nsource /task/command_continuity_v206_20261015/install/setup.bash\nsource /task/starvation_recovery_v219/install/setup.bash\n/audit/build/collision_probe'
    else:
        script='source /opt/ros/foxy/setup.bash\n'
        if mode=='original_author':script+='export AUTHOR_GEOMETRY=1\n'
        script+='/audit/build_original/original_probe'
    script+=' --ros-args --params-file /audit/critical_input/planner.yaml --log-level error\n'
    path=ROOT/'source'/('critical_'+mode+'.sh')
    path.write_text('set -eo pipefail\nexport REPLAY_INPUT=/audit/critical_input\nexport REPLAY_OUTPUT=/audit/output/critical_'+mode+'\n'+script)
    return docker(image,['/audit/source/'+path.name])
with ThreadPoolExecutor(max_workers=3) as pool:
    codes=list(pool.map(lambda mode:run('critical_'+mode+'02',command(mode),900),['native','original_author','original_current']))
raise SystemExit(max(codes))

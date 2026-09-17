"""Inspect the existing native PCT ABI in its isolated, read-only runtime."""

import json
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
HOST = 'gpu5070ti'
REMOTE = '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b'
PCT_ROOT = '/home/sun/machine-dog-nav-runs/2026-09-08_pct_scan_retest'
IMAGE = '40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555'


def main():
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', HOST]
    subprocess.run(ssh + [shlex.join(['mkdir', '-p', REMOTE + '/qualification'])], check=True)
    code = '''import json,sys,hashlib,subprocess
from pathlib import Path
from pct_planner import planner_wrapper
from pct_planner.lib import a_star,ele_planner,traj_opt
modules={}
for m in [planner_wrapper,a_star,ele_planner,traj_opt]:
 p=Path(m.__file__).resolve()
 modules[m.__name__]={'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 if p.suffix=='.so':
  modules[m.__name__]['ldd']=subprocess.run(['ldd',str(p)],capture_output=True,text=True).stdout
print(json.dumps({'python':sys.version,'modules':modules},indent=2))
'''
    inner = ('set -e\nexport ROS_LOG_DIR=/qualification/ros_logs\n'
             'source /io/workspace_retry01/scripts/_pct_scan_env.sh\n'
             'python3 -c ' + shlex.quote(code))
    command = ssh + [shlex.join(['podman', 'run', '--rm', '--pull=never', '--network=none',
                                '-e', 'PYTHONDONTWRITEBYTECODE=1', '-v', PCT_ROOT + ':/io:ro',
                                '-v', REMOTE + '/qualification:/qualification',
                                IMAGE, 'bash', '-c', inner])]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (HERE / 'pct_runtime_inspection.log').write_text(result.stdout + result.stderr)
    record = {'command': command, 'image_id': IMAGE, 'exit_code': result.returncode}
    if result.returncode == 0:
        record['inspection'] = json.loads(result.stdout)
    (HERE / 'pct_runtime_inspection.json').write_text(json.dumps(record, indent=2) + '\n')
    print(result.stdout or result.stderr)
    result.check_returncode()


if __name__ == '__main__':
    main()

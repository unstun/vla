"""Run the inherited native evaluator once per input against v290 only."""
from pathlib import Path
import argparse
import os
import subprocess

R = Path('/home/ubuntu/sun/vla_v290_20261021')
P = Path('/home/ubuntu/sun/vla_v289_20261020')
parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['case', 'contract'])
parser.add_argument('case', nargs='?')
parser.add_argument('output', nargs='?')
args = parser.parse_args()
shell = ('source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && '
    'export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=154 ROS_LOCALHOST_ONLY=1 '
    'REPLAY_INPUT=/work/fixtures/building PCT_INPUT=/work/fixtures/building/native_original.pct && '
    'source /work/fixtures/probe271.env && ')
command = ['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}',
    '--cpus=2', '--memory=6g', '--network=host', '-e', 'ROS_HOME=/evaluation/ros_home',
    '-e', 'ROS_LOG_DIR=/evaluation/ros_logs', '-v', str(P)+':/task:ro',
    '-v', str(R/'native')+':/work:ro', '-v', str(P/'native/fixtures')+':/work/fixtures:ro',
    '-v', str(R/'evaluation')+':/evaluation:rw']
if args.mode == 'case':
    assert args.case and args.output
    case, out = Path(args.case).resolve(), Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert not (out/'metrics.txt').exists(), 'Never overwrite a scored native call'
    command += ['--name', 'v290-case-'+case.name.lower(), '-v', str(case)+':/case:ro', '-v', str(out)+':/result:rw']
    shell += ('export CASE_INPUT=/case PROBE_OUTPUT=/result STATIC_SUPPORT_INPUT=/work/fixtures/building/native.support '
        'STATIC_SUPPORT_FNV=15212154834549674106 && /evaluation/build/native_probe')
else:
    shell += '/evaluation/build/geometry_contract_probe'
shell += ' --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level info'
command += ['--entrypoint', '/bin/bash', 'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343', '-c', shell]
raise SystemExit(subprocess.run(command).returncode)

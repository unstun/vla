"""Reuse the qualified owned install for a bounded original Newton corner run."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
PYTHON=BASE.parent/'2026-09-26_newton_macos_policy/runtime/.venv/bin/python'
IMAGE='sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
parser=argparse.ArgumentParser()
parser.add_argument('--workspace',type=Path,required=True)
parser.add_argument('--build-receipt',type=Path,required=True)
parser.add_argument('--seconds',type=float,default=90)
parser.add_argument('--trials',type=int,choices=(1,2),default=1)
parser.add_argument('--attempt',type=int,required=True)
args=parser.parse_args()
assert sys.platform=='darwin' and 20<=args.seconds<=90
evidence=HERE/'mac_trials'/f'attempt{args.attempt:02d}'
evidence.mkdir(parents=True,exist_ok=False)
temporary=Path(tempfile.mkdtemp(prefix='vla_newton_v82_',dir='/private/tmp'))
workspace=args.workspace.resolve()
assert workspace.parents[1].parent==Path('/private/tmp') and workspace.parents[1].name.startswith('vla_safe_mapping_')
cache=Path('/private/tmp/vla_newton_v70_cache_RGHNyI/runtime/warp-cache')
assert cache.is_dir()
shutil.copytree(cache,temporary/'runtime/warp-cache')
(temporary/'scripts').mkdir()
(temporary/'scripts/run_bounded.py').symlink_to(HERE/'mac_supervisor.py')
shutil.copyfile(args.build_receipt,evidence/'build_receipt.json')
container='vla-v82-mac-corner-%02d'%args.attempt
env=os.environ.copy()
env.update(DOCKER_CONTEXT='desktop-linux',PATH='/Users/sun/.local/bin:'+env['PATH'],
    V82_TEMP_ROOT=str(temporary),V82_NATIVE_CONTAINER=container,V82_BUILD_EVIDENCE=str(evidence),
    V82_PHYSICAL_FLOOR=str(temporary/'physical_floor.f32'),PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',
    PYTHONPATH=str(BASE/'runtime_sources/bridge')+':'+env.get('PYTHONPATH',''))
for port in (46200,46201,46202,46203):
    with socket.socket() as probe:probe.bind(('127.0.0.1',port))
command=['docker','run','-d','--rm','--pull=never','--platform=linux/amd64','--name',container,
    '--memory=6g','--cpus=6','-e','ROS_DOMAIN_ID=214','-e','ROS_LOCALHOST_ONLY=1',
    '-e','PYTHONDONTWRITEBYTECODE=1','-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',
    '-p','127.0.0.1:46202:46202','-p','127.0.0.1:46203:46203',
    '-v',str(ROOT)+':'+str(ROOT)+':ro','-v',str(workspace)+':/workspace:rw',
    '-v',str(workspace)+':/task/workspace/v82:rw',
    '-v',str(temporary)+':'+str(temporary)+':rw','-v',str(evidence)+':'+str(evidence)+':rw']
for number in range(1,args.trials+1):
    run='v82_mac_trial%02d_attempt%02d'%(number,args.attempt)
    command+=['--tmpfs',str(temporary/'runs'/run/'artifacts/external_episode')+':rw,size=8m']
command+=['--entrypoint','/bin/bash',IMAGE,'-c','exec sleep infinity']
request={'version':'v82','host':'Mac','scene':'original Building corner_start','seconds':args.seconds,
    'trials':args.trials,'temporary_root':str(temporary),'workspace':str(workspace),'container':container,
    'command':command,'manifest_sha256':sha(HERE/'manifest.json'),
    'remote_storage_root':'/home/sun/vla_artifacts/2026-10-05_safe_mapping_repair','gpu_job_started':False}
(evidence/'request.json').write_text(json.dumps(request,indent=2)+'\n')
created=False;rows=[];started=time.monotonic()
try:
    subprocess.run(command,env=env,capture_output=True,text=True,timeout=30,check=True);created=True
    subprocess.run([str(PYTHON),str(HERE/'derive_mac_floor.py'),'--output',env['V82_PHYSICAL_FLOOR']],env=env,check=True,timeout=30)
    for number in range(1,args.trials+1):
        if number>1:subprocess.run(command,env=env,capture_output=True,text=True,timeout=30,check=True)
        run='v82_mac_trial%02d_attempt%02d'%(number,args.attempt)
        episode=[str(PYTHON),str(HERE/'mac_managed.py'),'--run-id',run,'--deadline','540','--retention','archive','--',
            str(PYTHON),str(HERE/'run_local_episode.py'),'--backend-executor','single','--applied-transport','zmq',
            '--geometry-obstacles','--scene','building_full','--building-route','corner_start','--goal-wall-budget','180',
            '--startup-mode','factory_pd','--stance-hold','--integration-version','v82','--real-time-factor','1',
            '--recording-sim-seconds',str(args.seconds)]
        with (evidence/(run+'.log')).open('w') as stream:
            process=subprocess.run(episode,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=580)
        rows.append({'run':run,'exit_code':process.returncode,'raw_root':str(temporary/'runs'/run)})
        (evidence/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(json.dumps(rows[-1]),flush=True)
        if process.returncode:break
finally:
    if created:subprocess.run(['docker','rm','-f',container],env=env,capture_output=True,text=True,timeout=30)
    result={'passed':len(rows)==args.trials and all(row['exit_code']==0 for row in rows),
        'trials':rows,'wall_s':time.monotonic()-started,'temporary_root':str(temporary),
        'claim':'Execution completion only; physics, continuity, safety and timing acceptance require artifact analysis.'}
    (evidence/'execution.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
if not result['passed']:raise SystemExit(1)

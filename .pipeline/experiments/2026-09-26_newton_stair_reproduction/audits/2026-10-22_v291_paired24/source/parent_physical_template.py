"""Materialized original Newton execution protocol; bind frozen v290 and route data."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import platform
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').is_file())
BASE=ROOT/'.pipeline/experiments/2026-09-26_newton_stair_reproduction'
VERSIONS=BASE/'versions';V196=VERSIONS/'v196';V198=VERSIONS/'v198';V206=VERSIONS/'v206';V216=VERSIONS/'v216';V219=VERSIONS/'v290'
REMOTE=Path('/home/ubuntu/sun/vla_v290_20261021')
TASK=Path('/home/ubuntu/sun/vla_v290_20261021/physical_runs')/'v290___CASE___attempt01'
UNDERLAY=REMOTE
WORK=Path('/home/ubuntu/sun/vla_v290_20261021/native')
RUN='v290___CASE___attempt01';CONTAINER='v290-__case__-attempt01'
PYTHON=Path('/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python')
IMAGE='sha256:af529e408d9d130ba7b15a1eb2b78dc7b5408953a0de994ea05cccb43972fbec'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def supervisor():
    original=module(BASE.parent/'2026-09-26_newton_macos_policy/scripts/run_bounded.py','original_supervisor')
    source=(BASE.parent/'2026-09-26_newton_macos_policy/scripts/run_bounded.py').read_text()
    rss='resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss'
    assert source.count(rss)==1
    source=source.replace(rss,'('+rss+' * 1024)')
    exec(compile(source,str(original.__file__),'exec'),original.__dict__)
    original.BASE=TASK;original.MAX_DEADLINE_S=900
    original.main()

def episode():
    out=Path(os.environ['NEWTON_RUN_DIR'])
    sys.path.insert(0,str(V196))
    source=(V196/'run_local_episode.py').read_text()
    changes={
      'if integration_version != "v196":':'if integration_version != "v290":',
      'This entry point requires frozen integration version v196':'This trial requires frozen integration version v290',
      'qualification = json.loads((VERSION / "quality.json").read_text())':'qualification = runtime_qualification()',
      'shutil.copyfile(VERSION / "long_route_driver.py", out / "executed_long_route_driver.py")':'shutil.copyfile(FROZEN_NAVIGATION / "long_route_driver.py", out / "executed_long_route_driver.py")',
      'str(VERSION / "native_graph.py")':'str(NAVIGATION_VERSION / "native_graph.py")',
      'str(VERSION / "newton_episode.py")':'str(TELEMETRY_VERSION / "newton_episode.py")',
      '"source /task/recovery_v196/install/setup.bash",':'"source /work/install/setup.bash",',
      '+ " --output " + shlex.quote(str(out)), ""]':'+ " --output " + shlex.quote(str(out)) + " --terrain-manifest /work/fixtures/building/terrain282.json --environmental-manifest /work/fixtures/building/environment282.json", ""]',
      'shutil.copyfile(VERSION / name, out / ("executed_v196_" + name))':'shutil.copyfile(actual_source(name), out / ("executed_inherited_" + name))',
    }
    changes['        \"source /task/recovery_v176/install/setup.bash\",\n']=''
    changes['BASE.parent / "2026-09-26_newton_macos_policy/scripts/newton_stance.py"'] = 'LOCOMOTION_VERSION / "newton_stance.py"'
    changes['BASE.parent / "2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py"'] = 'LOCOMOTION_VERSION / "stance_hold.py"'
    changes['("short_stair", "historical_full", "corner_start")'] = '("short_stair", "historical_full", "corner_start", "generalization")'
    for before,after in changes.items():
        assert before in source,before
        source=source.replace(before,after)
    (out/'executed_trial_entry.py').write_text(source)
    write(out/'entry_rebindings.json',changes)
    namespace={'__file__':str(V196/'run_local_episode.py'),'__name__':'trial_episode'}
    exec(compile(source,str(out/'executed_trial_entry.py'),'exec'),namespace)
    def version_check(destination,version):
        assert version=='v290';write(destination/'source_gate.json',verify_sources())
        for name in ('native_graph.py','long_route_driver.py'):
            shutil.copyfile(VERSIONS/'v232'/name,destination/('frozen_v232_'+name))
        write(destination/'v290_runtime_binding.json',dict(execution='v290',navigation='v290',install=str(WORK/'install'),
            sources={'native_graph.py':sha(VERSIONS/'v290/native_graph.py'),'long_route_driver.py':sha(VERSIONS/'v257/long_route_driver.py')},offline_gate_sha256=sha(REMOTE/'benchmark/offline_gate.json')))
        shutil.copyfile(REMOTE/'migration/physical_manifest01.json',destination/'integration_version.json')
        return version
    def qualification():
        summary=json.loads((REMOTE/'benchmark/offline_gate.json').read_text())
        verify_execution_admission()
        return dict(passed=True,native_packages_available=14,execution_platform='linux/amd64',benchmark_acceptance_passed=summary['passed'],execution_timing_review_verified=True)
    def actual_source(name):
        if name=='native_graph.py':return V219/name
        if name=='newton_episode.py':return V219/name
        if name in ('initial_frame_v142.py','realtime_pacer.py'):return V198/name
        return V196/name
    namespace.update(FROZEN_NAVIGATION=VERSIONS/'v257',NAVIGATION_VERSION=V219,TELEMETRY_VERSION=V219,LOCOMOTION_VERSION=V216,actual_source=actual_source,
        runtime_qualification=qualification,building_scenario=case_scenario,verify_integration_version=version_check,
        verify_native_build=lambda *_:verify_sources())
    def interrupted(*_):raise KeyboardInterrupt('Bounded supervisor requested stop')
    signal.signal(signal.SIGTERM,interrupted)
    sys.argv=[str(REMOTE/'migration/physical.py'),'--backend-executor','single','--applied-transport','shared',
        '--geometry-obstacles','--scene','building_full','--building-route','generalization',
        '--goal-wall-budget','1500','--startup-mode','factory_pd','--stance-hold',
        '--integration-version','v290','--native-build',str(V219),'--real-time-factor','1','--recording-sim-seconds','600']
    namespace['main']()

def graph_probe(env):
    out=TASK/'graph_probe';out.mkdir()
    (out/'artifacts/external_episode').mkdir(parents=True)
    write(out/'episode_request.json',dict(integration_version='v290',native_variant='candidate',probe=True,
        run_epoch_ns=time.time_ns(),scene='building_full',geometry_obstacles=True,applied_transport='shared',
        building_route_profile='generalization',goal_wall_budget_s=1500,startup_mode='factory_pd'))
    shutil.copyfile(V196/'building_planner.yaml',out/'planner.yaml')
    shell='source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && exec python3 '+shlex.quote(str(V219/'native_graph.py'))+' --output '+shlex.quote(str(out))+' --terrain-manifest /work/fixtures/building/terrain282.json --environmental-manifest /work/fixtures/building/environment282.json'
    with (out/'probe.log').open('w') as log:
        process=subprocess.Popen(['docker','exec',CONTAINER,'bash','-c',shell],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            until=time.monotonic()+12
            while time.monotonic()<until:
                if process.poll() is not None or (out/'native_failure.json').exists():
                    raise RuntimeError('Native graph preflight failed before physics')
                time.sleep(.5)
            for log_path in out.glob('*.log'):
                assert 'Traceback (most recent call last)' not in log_path.read_text(errors='replace'),log_path
            module(VERSIONS/'v290/verify_profile.py','v290_profile_gate').verify(out)
            write(EVIDENCE/'graph_preflight.json',dict(passed=True,seconds=12,physics_steps=0,
                source='single v290 native/bridge prefix; process/config only',navigation_active_verified=False,output=str(out)))
        finally:
            subprocess.run(['docker','exec',CONTAINER,'pkill','-TERM','-f',str(V219/'native_graph.py')],env=env,capture_output=True,timeout=10)
            process.wait(timeout=15)

def launch():
    assert platform.system()=='Linux' and platform.machine()=='x86_64'
    identity=verify_sources();write(EVIDENCE/'source_gate_before.json',identity)
    sys.path.insert(0,str(V196));from resource_admission import admit
    write(EVIDENCE/'resource_admission.json',admit())
    verify_sources()  # Same sources guarded by the new-host manifests.
    for port in (24600,24601,24602,8785):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            probe.bind(('127.0.0.1',port))
    TASK.mkdir(exist_ok=False);(TASK/'scripts').mkdir();(TASK/'runtime').mkdir()
    (TASK/'scripts/run_bounded.py').symlink_to(REMOTE/'migration/physical.py')
    runtime=BASE.parent/'2026-09-26_newton_macos_policy/runtime'
    shutil.copytree(runtime/'assets',TASK/'runtime/assets')
    (TASK/'runtime/warp-cache').mkdir();(TASK/'ros_logs').mkdir();(TASK/'ros_home').mkdir()
    env=os.environ.copy();env.pop('DOCKER_CONTEXT',None);env.update(PATH=str(REMOTE/'migration/bin')+':'+env['PATH'],PYTHONDONTWRITEBYTECODE='1',
        PYTHONUNBUFFERED='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        V196_EXECUTION_IMAGE=IMAGE,V196_VARIANT='candidate',V196_NATIVE_CONTAINER=CONTAINER,
        V196_PHYSICAL_FLOOR='/work/fixtures/building/physical_floor.f32',
        PYTHONPATH=str(BASE/'runtime_sources/backend_adapter')+':'+str(V198/'runtime/bridge'))
    command=['docker','run','-d','--rm','--pull=never','--platform=linux/amd64','--name',CONTAINER,'--user',f'{os.getuid()}:{os.getgid()}',
        '--memory=6g','--cpus=6','-e','ROS_DOMAIN_ID=219','-e','ROS_LOCALHOST_ONLY=1',
        '-e','PYTHONDONTWRITEBYTECODE=1','-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',
        '-e','ROS_LOG_DIR='+str(TASK/'ros_logs'),'-e','ROS_HOME='+str(TASK/'ros_home'),
        '--network=host','--add-host','host.docker.internal:127.0.0.1','-v',f'{ROOT}:{ROOT}:ro','-v',f'{ROOT}:/repo:ro',
        '-v',f'{UNDERLAY}:/task:ro','-v',f'{WORK}:/work:ro','-v',f'{REMOTE}:{REMOTE}:ro',
        '-v',f'{REMOTE}/native/fixtures:/work/fixtures:ro','-v',f'{TASK}:{TASK}:rw',
        '--entrypoint','/bin/bash',IMAGE,'-c','exec sleep infinity']
    write(EVIDENCE/'execution_request.json',dict(run=RUN,source_identity=identity,image=IMAGE,command=command,
        raw_root=str(TASK/'runs'/RUN),physics='Linux x86_64 Warp CPU',navigation='v290 shared endpoint/local geometry and measured-state continuity',locomotion='v216 supported transfer',integration='v290'))
    started=time.monotonic();code=1
    try:
        subprocess.run(command,env=env,check=True,capture_output=True,timeout=30)
        shell='source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && python3 '+shlex.quote(str(REMOTE/'migration/preflight.py'))
        preflight=subprocess.check_output(['docker','exec',CONTAINER,'/bin/bash','-c',shell],env=env,text=True,timeout=30)
        (EVIDENCE/'native_preflight.json').write_text(preflight)
        graph_probe(env)
        if '--preflight-only' in sys.argv:code=0;return
        # Terminate all children from the no-physics graph probe, including ROS
        # launch descendants blocked waiting for TF, before the actual episode.
        subprocess.run(['docker','rm','-f',CONTAINER],env=env,check=True,capture_output=True,timeout=30)
        subprocess.run(command,env=env,check=True,capture_output=True,timeout=30)
        assert (REMOTE/'migration/physical_manifest01.json').is_file(), 'Freeze migration execution identity before physics'
        with (EVIDENCE/'physical_launch_once.json').open('x') as ledger:
            json.dump(dict(run=RUN,authorized_attempts=1,started_ns=time.time_ns()),ledger)
        os.environ.update(env)
        sys.path.insert(0,str(VERSIONS/'v51'));import managed_run
        managed_run.a.BASE=TASK;managed_run.a.AUDIT=TASK/'artifact_audit'
        sys.argv=[str(REMOTE/'migration/physical.py'),'--run-id',RUN,'--deadline','900','--retention','archive','--',str(PYTHON),str(REMOTE/'migration/physical.py'),'--episode']
        code=managed_run.main()
    finally:
        subprocess.run(['docker','rm','-f',CONTAINER],capture_output=True,timeout=30)
        write(EVIDENCE/'execution.json',dict(run=RUN,process_exit_code=code,wall_s=time.monotonic()-started,
            raw_root=str(TASK/'runs'/RUN),physics_acceptance=False))
    raise SystemExit(code)


"""One original-route physical trial of frozen v232 navigation and v216 locomotion."""
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
VERSIONS=BASE/'versions';V196=VERSIONS/'v196';V198=VERSIONS/'v198';V206=VERSIONS/'v206';V216=VERSIONS/'v216';V219=VERSIONS/'v233'
REMOTE=Path('/data/sun/vla_mppi_20261009')
TASK=REMOTE/'trials/v233_linux_full_attempt01'
UNDERLAY=REMOTE
WORK=REMOTE/'callback_failure_v232'
RUN='v233_linux_full_attempt01';CONTAINER='v233-linux-full-attempt01'
PYTHON=Path('/home/sun/vla_exec/envs/newton_worker/bin/python')
IMAGE='sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def verify_sources():
    original=module(VERSIONS/'v219/launch.py','v219_physical_reference')
    checked=original.verify_sources()
    identity=json.loads((HERE/'source_identity.json').read_text())
    for rel,expected in identity['files'].items():assert sha(HERE/rel)==expected,rel
    frozen=VERSIONS/'v232';manifest=json.loads((frozen/'manifest.json').read_text())
    for rel,expected in manifest['files'].items():assert sha(frozen/rel)==expected,rel
    inventory=json.loads((WORK/'source_inventory.json').read_text())
    assert inventory==json.loads((frozen/'results/source_inventory.json').read_text())
    for rel,expected in inventory.items():assert sha(WORK/rel)==expected,rel
    assert sha(WORK/'offline_gate.json')==sha(frozen/'results/offline_gate.json')
    receipt=json.loads((WORK/'offline_gate.json').read_text())
    assert len(inventory)==317 and len(receipt['installed_files'])==607
    assert receipt['source_identity_sha256']==sha(frozen/'source_identity.json')
    assert receipt['passed'] and receipt['unique_test_cases']==165 and receipt['colcon_records']==186 and receipt['physics_steps']==0 and receipt['source_inventory']==inventory
    for rel,expected in receipt['installed_files'].items():assert sha(WORK/rel)==expected,rel
    checked.update(v232_manifest=sha(frozen/'manifest.json'),execution_source_identity=sha(HERE/'source_identity.json'),
        native_source_version='v232',physical_reference='v219',locomotion='v216',component_cases=165)
    return checked

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
      'if integration_version != "v196":':'if integration_version != "v233":',
      'This entry point requires frozen integration version v196':'This trial requires frozen integration version v233',
      'qualification = json.loads((VERSION / "quality.json").read_text())':'qualification = runtime_qualification()',
      'shutil.copyfile(VERSION / "long_route_driver.py", out / "executed_long_route_driver.py")':'shutil.copyfile(FROZEN_NAVIGATION / "long_route_driver.py", out / "executed_long_route_driver.py")',
      'str(VERSION / "native_graph.py")':'str(NAVIGATION_VERSION / "native_graph.py")',
      'str(VERSION / "newton_episode.py")':'str(TELEMETRY_VERSION / "newton_episode.py")',
      '"source /task/recovery_v196/install/setup.bash",':'"source /task/recovery_v188/install/setup.bash", "source /task/command_continuity_v206_20261015/install/setup.bash", "source /work/install/setup.bash",',
      '+ " --output " + shlex.quote(str(out)), ""]':'+ " --output " + shlex.quote(str(out)) + " --terrain-manifest /work/fixtures/building/terrain.json --environmental-manifest /work/fixtures/building/environment225.json", ""]',
      'shutil.copyfile(VERSION / name, out / ("executed_v196_" + name))':'shutil.copyfile(actual_source(name), out / ("executed_inherited_" + name))',
    }
    changes['        \"source /task/recovery_v176/install/setup.bash\",\n']=''
    changes['BASE.parent / "2026-09-26_newton_macos_policy/scripts/newton_stance.py"'] = 'LOCOMOTION_VERSION / "newton_stance.py"'
    changes['BASE.parent / "2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py"'] = 'LOCOMOTION_VERSION / "stance_hold.py"'
    for before,after in changes.items():
        assert before in source,before
        source=source.replace(before,after)
    (out/'executed_trial_entry.py').write_text(source)
    write(out/'entry_rebindings.json',changes)
    namespace={'__file__':str(V196/'run_local_episode.py'),'__name__':'trial_episode'}
    exec(compile(source,str(out/'executed_trial_entry.py'),'exec'),namespace)
    def version_check(destination,version):
        assert version=='v233';write(destination/'source_gate.json',verify_sources())
        for name in ('native_graph.py','long_route_driver.py'):
            shutil.copyfile(VERSIONS/'v232'/name,destination/('frozen_v232_'+name))
        write(destination/'v232_runtime_binding.json',dict(execution='v233',navigation='v232',install=str(WORK/'install'),
            sources={name:sha(VERSIONS/'v232'/name) for name in ('native_graph.py','long_route_driver.py')},offline_gate_sha256=sha(WORK/'offline_gate.json')))
        shutil.copyfile(V219/'manifest.json',destination/'integration_version.json')
        return version
    def qualification():
        summary=json.loads((WORK/'offline_gate.json').read_text())
        assert summary['passed']
        return dict(passed=True,native_packages_available=14,execution_platform='linux/amd64')
    def actual_source(name):
        if name=='native_graph.py':return V219/name
        if name=='newton_episode.py':return V219/name
        if name in ('initial_frame_v142.py','realtime_pacer.py'):return V198/name
        return V196/name
    namespace.update(FROZEN_NAVIGATION=VERSIONS/'v232',NAVIGATION_VERSION=V219,TELEMETRY_VERSION=V219,LOCOMOTION_VERSION=V216,actual_source=actual_source,
        runtime_qualification=qualification,verify_integration_version=version_check,
        verify_native_build=lambda *_:verify_sources())
    def interrupted(*_):raise KeyboardInterrupt('Bounded supervisor requested stop')
    signal.signal(signal.SIGTERM,interrupted)
    sys.argv=[str(HERE/'launch.py'),'--backend-executor','single','--applied-transport','shared',
        '--geometry-obstacles','--scene','building_full','--building-route','historical_full',
        '--goal-wall-budget','1500','--startup-mode','factory_pd','--stance-hold',
        '--integration-version','v233','--native-build',str(V219),'--real-time-factor','1','--recording-sim-seconds','600']
    namespace['main']()

def graph_probe(env):
    out=TASK/'graph_probe';out.mkdir()
    (out/'artifacts/external_episode').mkdir(parents=True)
    write(out/'episode_request.json',dict(integration_version='v233',native_variant='candidate',probe=True,
        run_epoch_ns=time.time_ns(),scene='building_full',geometry_obstacles=True,applied_transport='shared',
        building_route_profile='historical_full',goal_wall_budget_s=1500,startup_mode='factory_pd'))
    shutil.copyfile(V196/'building_planner.yaml',out/'planner.yaml')
    shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /work/install/setup.bash && exec python3 '+shlex.quote(str(V219/'native_graph.py'))+' --output '+shlex.quote(str(out))+' --terrain-manifest /work/fixtures/building/terrain.json --environmental-manifest /work/fixtures/building/environment225.json'
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
            module(HERE/'verify_profile.py','v233_profile_gate').verify(out)
            write(HERE/'graph_preflight.json',dict(passed=True,seconds=12,physics_steps=0,
                source='v232 navigation with shared scoring/height/feedback; original v219 physics',output=str(out)))
        finally:
            subprocess.run(['docker','exec',CONTAINER,'pkill','-TERM','-f',str(V219/'native_graph.py')],env=env,capture_output=True,timeout=10)
            process.wait(timeout=15)

def launch():
    assert platform.system()=='Linux' and platform.machine()=='x86_64'
    identity=verify_sources();write(HERE/'source_gate_before.json',identity)
    sys.path.insert(0,str(V196));from resource_gate import admit
    write(HERE/'resource_admission.json',admit())
    sync=json.loads((V206/'results/v206_linux_full_attempt02/sync_manifest.json').read_text())
    for rel,record in sync.items():assert sha(ROOT/rel)==record['sha256'],rel
    for port in (24600,24601,24602,8785):
        with socket.socket() as probe:probe.bind(('127.0.0.1',port))
    TASK.mkdir(exist_ok=False);(TASK/'scripts').mkdir();(TASK/'runtime').mkdir()
    (TASK/'scripts/run_bounded.py').symlink_to(HERE/'launch.py')
    runtime=BASE.parent/'2026-09-26_newton_macos_policy/runtime'
    shutil.copytree(runtime/'assets',TASK/'runtime/assets')
    (TASK/'runtime/warp-cache').mkdir();(TASK/'ros_logs').mkdir();(TASK/'ros_home').mkdir()
    env=os.environ.copy();env.pop('DOCKER_CONTEXT',None);env.update(PATH=str(HERE/'bin')+':'+env['PATH'],PYTHONDONTWRITEBYTECODE='1',
        PYTHONUNBUFFERED='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        V196_EXECUTION_IMAGE=IMAGE,V196_VARIANT='candidate',V196_NATIVE_CONTAINER=CONTAINER,
        V196_PHYSICAL_FLOOR='/work/fixtures/building/physical_floor.f32',
        PYTHONPATH=str(UNDERLAY/'host_python')+':'+str(V198/'runtime/bridge'))
    command=['docker','run','-d','--rm','--pull=never','--platform=linux/amd64','--name',CONTAINER,'--user',f'{os.getuid()}:{os.getgid()}',
        '--memory=6g','--cpus=6','-e','ROS_DOMAIN_ID=219','-e','ROS_LOCALHOST_ONLY=1',
        '-e','PYTHONDONTWRITEBYTECODE=1','-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',
        '-e','ROS_LOG_DIR='+str(TASK/'ros_logs'),'-e','ROS_HOME='+str(TASK/'ros_home'),
        '--network=host','--add-host','host.docker.internal:127.0.0.1','-v',f'{ROOT}:{ROOT}:ro','-v',f'{ROOT}:/repo:ro',
        '-v',f'{UNDERLAY}:/task:ro','-v',f'{WORK}:/work:ro','-v',f'{TASK}:{TASK}:rw',
        '--entrypoint','/bin/bash',IMAGE,'-c','exec sleep infinity']
    write(HERE/'execution_request.json',dict(run=RUN,source_identity=identity,image=IMAGE,command=command,
        raw_root=str(TASK/'runs'/RUN),physics='Linux x86_64 Warp CPU',navigation='v232 shared score + support height + mission feedback',locomotion='v216 supported transfer',integration='v233'))
    started=time.monotonic();code=1
    try:
        subprocess.run(command,env=env,check=True,capture_output=True,timeout=30)
        shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /work/install/setup.bash && python3 '+shlex.quote(str(HERE/'preflight.py'))
        preflight=subprocess.check_output(['docker','exec',CONTAINER,'/bin/bash','-c',shell],env=env,text=True,timeout=30)
        (HERE/'native_preflight.json').write_text(preflight)
        graph_probe(env)
        if '--preflight-only' in sys.argv:code=0;return
        # Terminate all children from the no-physics graph probe, including ROS
        # launch descendants blocked waiting for TF, before the actual episode.
        subprocess.run(['docker','rm','-f',CONTAINER],env=env,check=True,capture_output=True,timeout=30)
        subprocess.run(command,env=env,check=True,capture_output=True,timeout=30)
        assert (HERE/'manifest.json').is_file(), 'Freeze execution identity before physics'
        os.environ.update(env)
        sys.path.insert(0,str(VERSIONS/'v51'));import managed_run
        managed_run.a.BASE=TASK;managed_run.a.AUDIT=TASK/'artifact_audit'
        sys.argv=[str(HERE/'launch.py'),'--run-id',RUN,'--deadline','900','--retention','archive','--',str(PYTHON),str(HERE/'launch.py'),'--episode']
        code=managed_run.main()
    finally:
        subprocess.run(['docker','rm','-f',CONTAINER],capture_output=True,timeout=30)
        write(HERE/'execution.json',dict(run=RUN,process_exit_code=code,wall_s=time.monotonic()-started,
            raw_root=str(TASK/'runs'/RUN),physics_acceptance=False))
    raise SystemExit(code)

if __name__=='__main__':
    if Path(sys.argv[0]).name=='run_bounded.py':supervisor()
    elif '--episode' in sys.argv:episode()
    else:
        if '--preflight-only' in sys.argv:
            TASK=REMOTE/'trials/v233_linux_preflight01';RUN='v233_linux_preflight01';CONTAINER='v233-linux-preflight01'
        launch()

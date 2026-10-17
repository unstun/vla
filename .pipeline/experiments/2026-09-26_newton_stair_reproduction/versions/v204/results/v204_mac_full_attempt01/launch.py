"""Trial-only binding of frozen v204 components to the original Mac physical harness."""
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
VERSIONS=BASE/'versions';V196=VERSIONS/'v196';V198=VERSIONS/'v198';V204=VERSIONS/'v204'
TASK=Path('/private/tmp/vla_v204_physics_20261015')
UNDERLAY=Path('/private/tmp/vla_navigation_refactor_20261014/underlay')
WORK=UNDERLAY.parent/'workspaces/v204'
RUN='v204_mac_full_attempt01';CONTAINER='v204-mac-full-attempt01'
PYTHON=BASE.parent/'2026-09-26_newton_macos_policy/runtime/.venv/bin/python'
IMAGE='sha256:a6326521265b857c85799c5d24eb8d9a78cbb19a25d2b1e5e1d01943cea3524e'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def verify_sources():
    checked={}
    for version in (V198,V204):
        manifest=json.loads((version/'manifest.json').read_text())
        for rel,expected in manifest['source_files'].items():
            assert sha(version/rel)==expected,(version.name,rel)
        checked[version.name]=sha(version/'manifest.json')
    frozen=json.loads((V196/'manifest.json').read_text())
    for rel,expected in frozen['source_files'].items():
        assert sha(ROOT/rel)==expected,rel
    checked['v196']=sha(V196/'manifest.json')
    inventory=json.loads((V204/'verification/source_inventory.json').read_text())
    for rel,expected in inventory.items():assert sha(WORK/rel)==expected,rel
    checked['composed_source_files']=len(inventory)
    return checked

def supervisor():
    original=module(BASE.parent/'2026-09-26_newton_macos_policy/scripts/run_bounded.py','original_supervisor')
    original.BASE=TASK;original.MAX_DEADLINE_S=900
    original.main()

def episode():
    out=Path(os.environ['NEWTON_RUN_DIR'])
    sys.path.insert(0,str(V196))
    source=(V196/'run_local_episode.py').read_text()
    changes={
      'if integration_version != "v196":':'if integration_version != "v204":',
      'This entry point requires frozen integration version v196':'This trial requires frozen integration version v204',
      'qualification = json.loads((VERSION / "quality.json").read_text())':'qualification = runtime_qualification()',
      'str(VERSION / "native_graph.py")':'str(NAVIGATION_VERSION / "native_graph.py")',
      'str(VERSION / "newton_episode.py")':'str(TELEMETRY_VERSION / "newton_episode.py")',
      '"source /task/recovery_v196/install/setup.bash",':'"source /task/recovery_v196/install/setup.bash", "source /work/install/setup.bash",',
      '+ " --output " + shlex.quote(str(out)), ""]':'+ " --output " + shlex.quote(str(out)) + " --terrain-manifest /work/fixtures/building/terrain.json", ""]',
      'shutil.copyfile(VERSION / name, out / ("executed_v196_" + name))':'shutil.copyfile(actual_source(name), out / ("executed_inherited_" + name))',
    }
    for before,after in changes.items():
        assert before in source,before
        source=source.replace(before,after)
    (out/'executed_trial_entry.py').write_text(source)
    write(out/'entry_rebindings.json',changes)
    namespace={'__file__':str(V196/'run_local_episode.py'),'__name__':'trial_episode'}
    exec(compile(source,str(out/'executed_trial_entry.py'),'exec'),namespace)
    def version_check(destination,version):
        assert version=='v204';write(destination/'source_gate.json',verify_sources())
        shutil.copyfile(V204/'manifest.json',destination/'integration_version.json')
        return version
    def qualification():
        summary=json.loads((V204/'verification/summary.json').read_text())
        assert summary['failures']==0 and summary['unique_ros_component_cases']==106
        return dict(passed=True,native_packages_available=14,execution_platform='linux/arm64')
    def actual_source(name):
        if name=='native_graph.py':return V204/name
        if name in ('newton_episode.py','initial_frame_v142.py','realtime_pacer.py'):return V198/name
        return V196/name
    namespace.update(NAVIGATION_VERSION=V204,TELEMETRY_VERSION=V198,actual_source=actual_source,
        runtime_qualification=qualification,verify_integration_version=version_check,
        verify_native_build=lambda *_:verify_sources())
    def interrupted(*_):raise KeyboardInterrupt('Bounded supervisor requested stop')
    signal.signal(signal.SIGTERM,interrupted)
    sys.argv=[str(HERE/'launch.py'),'--backend-executor','single','--applied-transport','shared',
        '--geometry-obstacles','--scene','building_full','--building-route','historical_full',
        '--goal-wall-budget','1500','--startup-mode','factory_pd','--stance-hold',
        '--integration-version','v204','--native-build',str(V204),'--real-time-factor','1','--recording-sim-seconds','600']
    namespace['main']()

def launch():
    assert platform.system()=='Darwin' and platform.machine()=='arm64'
    identity=verify_sources();write(HERE/'source_gate_before.json',identity)
    assert shutil.disk_usage('/private/tmp').free>10*1024**3
    for port in (24600,24601,24602,8785):
        with socket.socket() as probe:probe.bind(('127.0.0.1',port))
    TASK.mkdir(exist_ok=False);(TASK/'scripts').mkdir();(TASK/'runtime').mkdir()
    (TASK/'scripts/run_bounded.py').symlink_to(HERE/'launch.py')
    runtime=BASE.parent/'2026-09-26_newton_macos_policy/runtime'
    shutil.copytree(runtime/'assets',TASK/'runtime/assets')
    (TASK/'runtime/warp-cache').mkdir()
    env=os.environ.copy();env.update(DOCKER_CONTEXT='desktop-linux',PYTHONDONTWRITEBYTECODE='1',
        PYTHONUNBUFFERED='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        V196_EXECUTION_IMAGE=IMAGE,V196_VARIANT='candidate',V196_NATIVE_CONTAINER=CONTAINER,
        V196_PHYSICAL_FLOOR='/work/fixtures/building/physical_floor.f32',
        PYTHONPATH=str(UNDERLAY/'host_python')+':'+str(V198/'runtime/bridge'))
    command=['docker','run','-d','--rm','--pull=never','--platform=linux/arm64','--name',CONTAINER,
        '--memory=6g','--cpus=6','-e','ROS_DOMAIN_ID=204','-e','ROS_LOCALHOST_ONLY=1',
        '-e','PYTHONDONTWRITEBYTECODE=1','-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',
        '-e','ROS_LOG_DIR='+str(TASK/'ros_logs'),'-e','ROS_HOME='+str(TASK/'ros_home'),
        '-p','127.0.0.1:24602:24602','-v',f'{ROOT}:{ROOT}:ro','-v',f'{ROOT}:/repo:ro',
        '-v',f'{UNDERLAY}:/task:ro','-v',f'{WORK}:/work:ro','-v',f'{TASK}:{TASK}:rw',
        '--entrypoint','/bin/bash',IMAGE,'-c','exec sleep infinity']
    write(HERE/'execution_request.json',dict(run=RUN,source_identity=identity,image=IMAGE,command=command,
        raw_root=str(TASK/'runs'/RUN),physics='Mac ARM64 Warp CPU',navigation='v204 ARM64 Foxy'))
    started=time.monotonic();code=1
    try:
        subprocess.run(command,env=env,check=True,capture_output=True,timeout=30)
        shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v196/install/setup.bash && source /work/install/setup.bash && python3 '+shlex.quote(str(HERE/'preflight.py'))
        preflight=subprocess.check_output(['docker','exec',CONTAINER,'/bin/bash','-c',shell],env=env,text=True,timeout=30)
        (HERE/'native_preflight.json').write_text(preflight)
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
    else:launch()

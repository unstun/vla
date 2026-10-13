"""Build upstream planning and run its authorized Newton comparison on Mac."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,shlex,shutil,socket,subprocess,sys,tempfile,time

HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
NATIVE=BASE/'runtime/scan83_upstream_probe_v71'
PYTHON=BASE.parent/'2026-09-26_newton_macos_policy/runtime/.venv/bin/python'
IMAGE='sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb'
DOCKER='/Users/sun/.local/bin/docker'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def freeze(receipt_path):
    """Freeze upstream transport experiment; no navigation success claim."""
    if (HERE/'manifest.json').exists():
        manifest=json.loads((HERE/'manifest.json').read_text())
        assert manifest['mac_build_receipt_sha256']==sha(receipt_path)
        return manifest
    parent=json.loads((BASE/'versions/v76/manifest.json').read_text())
    selected=dict(parent['source_files']);locations=dict(parent['snapshot_locations'])
    assert all(sha(ROOT/name)==h and sha(ROOT/locations[name])==h for name,h in selected.items())
    owned=[p for p in HERE.iterdir() if p.is_file() and p.name not in ('manifest.json','RESULTS.md')]
    owned += [p for p in NATIVE.rglob('*') if p.is_file()]
    for path in owned:
        name=str(path.relative_to(ROOT));h=sha(path)
        if selected.get(name)==h:continue
        inherited=str((BASE/'versions/v76'/path.name).relative_to(ROOT))
        if path.parent==HERE and parent['source_files'].get(inherited)==h:
            location=parent['snapshot_locations'][inherited]
        else:
            target=HERE/'source'/name;target.parent.mkdir(parents=True,exist_ok=True)
            assert not target.exists();shutil.copyfile(path,target);location=str(target.relative_to(ROOT))
        selected[name]=h;locations[name]=location
    receipt=json.loads(receipt_path.read_text())
    smoke=receipt_path.parent/'native_transport_smoke.json'
    manifest={'version':'v77','parent':'v76','native_source_parent':'PCT-SCAN-ROS2@1cf45a1c12ca785ce533293302be09d51daf0ccb',
        'runtime_source_parent':'v59','parent_manifest_sha256':sha(BASE/'versions/v76/manifest.json'),
        'status':'frozen_user_authorized_upstream_comparison_pending',
        'source_files':dict(sorted(selected.items())),'snapshot_locations':dict(sorted(locations.items())),
        'native_source_sha256':receipt['native_source_sha256'],'native_install_sha256':receipt['native_install_sha256'],
        'mac_build_receipt_sha256':sha(receipt_path),'transport_smoke_sha256':sha(smoke),
        'native_transport_smoke_passed':json.loads(smoke.read_text())['passed'],
        'component_passed':False,'physics_run':False,'navigation_validated':False,'full_scene_30hz_validated':False,
        'claim_boundary':'Upstream ROS2 planning integration on Mac; original planning/terrain rules differ from local v63; transport/build qualification is not navigation acceptance.'}
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--attempt',type=int,required=True)
    p.add_argument('--trials',type=int,choices=(1,2),default=1)
    p.add_argument('--seconds',type=float,default=40.)
    p.add_argument('--reuse-workspace',type=Path)
    args=p.parse_args();assert sys.platform=='darwin' and 20<=args.seconds<=90
    evidence=HERE/'mac_trials'/f'attempt{args.attempt:02d}';evidence.mkdir(parents=True,exist_ok=False)
    assert shutil.disk_usage(HERE).free>12*1024**3
    for port in (46200,46201,46202,46203):
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    temp=Path(tempfile.mkdtemp(prefix='vla_newton_v77_',dir='/private/tmp'))
    workspace=args.reuse_workspace.resolve() if args.reuse_workspace else temp/'native_workspace'
    if args.reuse_workspace:
        assert workspace.parent.parent==Path('/private/tmp') and workspace.parent.name.startswith('vla_newton_')
        assert (workspace/'install').is_dir() and (workspace/'src').is_dir()
    else:workspace.mkdir()
    cache=Path(os.environ['V77_PREPARED_WARP_CACHE']).resolve()
    assert cache.is_dir() and cache.name=='warp-cache' and cache.parent.parent.parent==Path('/private/tmp')
    shutil.copytree(cache,temp/'runtime/warp-cache')
    (temp/'scripts').mkdir();(temp/'scripts/run_bounded.py').symlink_to(HERE/'mac_supervisor.py')
    container=f'vla-v77-mac-physics-{args.attempt:02d}'
    env=os.environ.copy();env.update(DOCKER_CONTEXT='desktop-linux',
        PATH='/Users/sun/.local/bin:'+env['PATH'],V77_TEMP_ROOT=str(temp),
        V77_NATIVE_CONTAINER=container,V77_BUILD_EVIDENCE=str(evidence),
        V77_PHYSICAL_FLOOR=str(temp/'physical_floor.f32'),
        PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',
        PYTHONPATH=str(BASE/'runtime_sources/bridge')+':'+env.get('PYTHONPATH',''))
    request={'host':'Mac','gpu5070ti_used':False,'started_utc':datetime.now(timezone.utc).isoformat(),
        'authorization':'Dr Sun: initialize and start the simulation right near that specific corner/scene','version':'v77','native_parent':'PCT-SCAN-ROS2@1cf45a1',
        'runtime_parent':'v59','trials':args.trials,'simulation_seconds_per_trial':args.seconds,'route_profile':'corner_start',
        'upstream_comparison':True,'prepared_warp_cache':str(cache),'upstream_planning_core_unchanged':True,'current_backend_stop_rules_unchanged':True,
        'bulk_root':str(temp),'compact_return_root':str(evidence),'bulk_is_outside_repository':True,
        'temporary_native_workspace':str(workspace),'reuse_workspace':bool(args.reuse_workspace),
        'source_manifest_sha256':sha(NATIVE/'source_sha256.json'),
        'retention':'Lossless closed raw archive at temporary Mac root; compact reports/plot/video only in repo',
        'claim_boundary':'Actual Mac Newton trial; no gpu5070ti timing equivalence or full qualification promotion'}
    (evidence/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    started=time.monotonic();result={'passed':False,'trials':[]};created=False
    try:
        cmd=[DOCKER,'run','-d','--rm','--pull=never','--platform=linux/amd64',
            '--name',container,'--memory=6g','--cpus=6',
            '-e','CMAKE_BUILD_PARALLEL_LEVEL=2','-e','MAKEFLAGS=-j2',
            '-e','ROS_DOMAIN_ID=214','-e','ROS_LOCALHOST_ONLY=1',
            '-e','PYTHONDONTWRITEBYTECODE=1','-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',
            '-p','127.0.0.1:46202:46202','-p','127.0.0.1:46203:46203',
            '-v',str(ROOT)+':'+str(ROOT)+':ro','-v',str(NATIVE)+':/candidate:ro',
            '-v',str(evidence)+':/evidence:rw','-v',str(evidence)+':'+str(evidence)+':rw',
            '-v',str(temp)+':'+str(temp)+':rw','--entrypoint','/bin/bash',IMAGE,
            '-c','exec sleep infinity']
        for trial in range(1,args.trials+1):
            run=f'v77_mac_trial{trial:02d}_attempt{args.attempt:02d}'
            index=cmd.index('--entrypoint')
            cmd[index:index]=['--tmpfs',str(temp/'runs'/run/'artifacts/external_episode')+':rw,size=8m']
        index=cmd.index('--entrypoint');cmd[index:index]=['-v',str(workspace)+':/workspace:rw']
        request['container_command']=cmd;(evidence/'request.json').write_text(json.dumps(request,indent=2)+'\n')
        subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30,check=True);created=True
        if not args.reuse_workspace:
            with (evidence/'build_driver.log').open('w') as log:
                subprocess.run([DOCKER,'exec',container,'/bin/bash',str(HERE/'mac_build_inside.sh')],
                    env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200,check=True)
            shutil.copyfile(evidence/'build_receipt.json',workspace.parent/'native_build_receipt.json')
        else:
            shutil.copyfile(workspace.parent/'native_build_receipt.json',evidence/'build_receipt.json')
        smoke_script='source /opt/ros/humble/setup.bash && source /workspace/install/setup.bash && exec python3 '+shlex.quote(str(HERE/'transport_smoke.py'))+' --output '+shlex.quote(str(evidence))
        with (evidence/'transport_smoke_driver.log').open('w') as log:
            subprocess.run([DOCKER,'exec',container,'/bin/bash','-c',smoke_script],env=env,
                stdout=log,stderr=subprocess.STDOUT,timeout=45,check=True)
        subprocess.run([str(PYTHON),str(HERE/'derive_mac_floor.py'),'--output',env['V77_PHYSICAL_FLOOR']],
            env=env,capture_output=True,text=True,timeout=30,check=True)
        shutil.copyfile(temp/'physical_floor.provenance.json',evidence/'physical_floor_provenance.json')
        from mac_native_gate import verify
        receipt_path=evidence/'build_receipt.json'
        receipt=json.loads(receipt_path.read_text())
        provisional={'native_source_sha256':receipt['native_source_sha256'],
            'mac_build_receipt_sha256':sha(receipt_path),
            'transport_smoke_sha256':sha(evidence/'native_transport_smoke.json')}
        os.environ.update({key:env[key] for key in ('DOCKER_CONTEXT','PATH','V77_BUILD_EVIDENCE','V77_NATIVE_CONTAINER')})
        verify(NATIVE,provisional)
        manifest=freeze(receipt_path)
        result['integration_manifest_sha256']=sha(HERE/'manifest.json')
        from mac_native_gate import verify
        os.environ.update({key:env[key] for key in ('DOCKER_CONTEXT','PATH','V77_BUILD_EVIDENCE','V77_NATIVE_CONTAINER')})
        (evidence/'entry_gate.json').write_text(json.dumps(verify(NATIVE,manifest),indent=2)+'\n')
        for trial in range(1,args.trials+1):
            if trial>1:
                subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30,check=True)
            run=f'v77_mac_trial{trial:02d}_attempt{args.attempt:02d}'
            command=[str(PYTHON),str(HERE/'mac_managed.py'),'--run-id',run,'--deadline','540',
                '--retention','archive','--',str(PYTHON),str(HERE/'run_local_episode.py'),
                '--backend-executor','single','--applied-transport','zmq','--geometry-obstacles',
                '--scene','building_full','--building-route','corner_start',
                '--goal-wall-budget','180','--startup-mode','factory_pd','--stance-hold',
                '--integration-version','v77','--real-time-factor','1',
                '--recording-sim-seconds',str(args.seconds)]
            with (evidence/(run+'.execution.log')).open('w') as log:
                process=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=580)
            row={'run':run,'exit_code':process.returncode,'raw_run_root':str(temp/'runs'/run)}
            for filename in ('request.json','process.json','result.json','retention_result.json','state_copyback.json',
                             'factory_handoff.json','factory_events.json','navigation_clock_anchor.json'):
                path=temp/'runs'/run/filename
                if path.is_file():
                    destination=evidence/run/filename;destination.parent.mkdir(exist_ok=True)
                    shutil.copyfile(path,destination)
            subprocess.run([str(PYTHON),str(HERE/'closeout.py'),'--run-root',row['raw_run_root'],'--evidence',str(evidence/run)],env=env,check=True,timeout=1400)
            result['trials'].append(row)
            (evidence/'progress.json').write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(row),flush=True)
            if process.returncode:break
        result['passed']=len(result['trials'])==args.trials and all(not x['exit_code'] for x in result['trials'])
    except Exception as error:
        result['error']=repr(error)
    finally:
        if created:
            cleanup=subprocess.run([DOCKER,'rm','-f',container],env=env,capture_output=True,text=True,timeout=25)
            result['container_cleanup']={'exit_code':cleanup.returncode,'stdout':cleanup.stdout,'stderr':cleanup.stderr}
        checked=subprocess.run([DOCKER,'container','inspect',container],env=env,capture_output=True,text=True,timeout=20)
        result['owned_container_absent']=checked.returncode!=0 and 'No such container' in checked.stderr
        result['wall_s']=time.monotonic()-started;result['finished_utc']=datetime.now(timezone.utc).isoformat()
        result['claim_boundary']='Process completion only; semantic acceptance needs analysis of actual physics/planner artifacts'
        (evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        records={str(p.relative_to(temp)):{'sha256':sha(p),'bytes':p.stat().st_size}
                 for p in temp.rglob('*') if p.is_file() and not p.is_symlink()}
        (evidence/'bulk_locator.json').write_text(json.dumps({'host':'Mac','temporary_root':str(temp),
            'files':records,'logical_bytes':sum(x['bytes'] for x in records.values()),
            'outside_repository':True,
            'retention':'Preserve until reviewed remote archive or regeneration is available'},indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':main()

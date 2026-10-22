"""Analyze and render every actual new-endpoint attempt, including failures."""
from pathlib import Path
import csv,hashlib,importlib.util,json,math,os,shutil,subprocess,sys
import numpy as np

HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];VERSIONS=EXP/'versions'
PREFIX=Path('/data/sun/vla_mppi_20261009');CASE=os.environ['V243_CASE_ID']
RUN=f'v243_{CASE}_attempt01';TASK=PREFIX/'trials'/RUN;RAW=TASK/'runs'/RUN
CASEOUT=HERE/'physical'/CASE;RESULTS=CASEOUT/'results'
EVIDENCE=PREFIX/'generalization_v243'/CASE
PARENT=EXP/'audits/2026-10-18_v240_gpu5070ti_physical'
sys.path[:0]=[str(VERSIONS/'v196'),str(VERSIONS/'v243'),str(EXP/'audits/2026-10-17_v237_terminal_approach')]
from analyze_remote import Capture,analyze,core
from pause_metrics import low_speed_intervals,summarize
from trajectory_coverage import active_gaps

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as stream:
        for block in iter(lambda:stream.read(4*2**20),b''):h.update(block)
    return h.hexdigest()

def save(name,value):
    (RESULTS/name).write_text(json.dumps(value,indent=2)+'\n')

def load_parent(name):
    p=PARENT/name;code=p.read_text()
    code=code.replace('v241_linux_full_attempt01',RUN).replace('v241-linux-full-attempt01',f'v243-{CASE.lower()}-attempt01')
    code=code.replace("(HERE.parents[1]/'versions/v241/execution.json')","EXECUTION")
    scope=dict(__file__=str(p),__name__='case_parent_'+p.stem,
        EXECUTION=EVIDENCE/'execution.json')
    exec(compile(code,str(p),'exec'),scope)
    scope.update(HERE=CASEOUT,BASE=EXP,VERSIONS=VERSIONS,PREFIX=PREFIX,TASK=TASK,
        RAW=RAW,RUN=RUN,OUT=RESULTS)
    (CASEOUT/('executed_'+name)).write_text(code)
    return scope

def preserve():
    assert json.loads((EVIDENCE/'execution.json').read_text())['run']==RUN
    names=subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).splitlines()
    assert f'v243-{CASE.lower()}-attempt01' not in names
    load_parent('preserve.py')['main']()

def analyze_case():
    capture=Capture(RAW)
    try:
        analyze(RAW,RESULTS,metrics_only=True);analysis_code=0
    except Exception as error:
        analysis_code=1
        save('analysis_error.json',dict(error=repr(error)))
        # Do not synthesize a recorder result. These are display-only diagnostic
        # inputs for a retained prefix whose original result remains absent.
        terminal=None
        try:terminal=capture.json('result.json').get('finish_request')
        except (FileNotFoundError,KeyError):pass
        save('metrics.json',dict(full_qualification=False,sustained_30hz_validated=False,
            diagnostic_only=True,terminal=terminal,planning={},analysis_error=repr(error)))
        (RESULTS/'latency.csv').write_text('wall_s_host,solve_ms,success,ros_s\n')
    save('analysis_status.json',dict(returncode=analysis_code,analyzer_sha256=sha(VERSIONS/'v196/analyze_remote.py')))
    from verify_case import verify
    try:route=verify(RAW)
    except Exception as error:route=dict(passed=False,case_id=CASE,error=repr(error),run=RUN)
    save('full_route_verification.json',route)
    (RAW/'full_route_verification.json').write_text(json.dumps(route,indent=2)+'\n')
    try:actual=capture.json('result.json')
    except (FileNotFoundError,KeyError):actual=None
    rows=capture.json('video_states.json');telemetry=capture.rows('telemetry.jsonl')
    terminal=(actual.get('finish_request') or {}).get('backend_terminal_status') if actual else None
    snapshot=json.loads((RESULTS/'capture_snapshot.json').read_text())
    outcome=dict(run=RUN,case_id=CASE,host='gpu5070ti',navigation_source='v240',execution_package='v243',
        locomotion='v216',overall_result='PASSED' if route['passed'] else 'FAILED',
        full_route_gate_passed=route['passed'],terminal_status=terminal or ('PHYSICAL_FALL' if actual and actual.get('fallen') else 'RECORDER_FAILED' if actual is None else 'BOUNDED_END'),
        recorded_backend_terminal_status=terminal,fallen=actual.get('fallen',False) if actual else None,
        physics_duration_s=rows[-1]['physics_time_s'],raw_root=str(RAW),
        archive_sha256=snapshot['archive_sha256'],archive_bytes=snapshot['archive_bytes'],
        result_json_present=actual is not None,goal_sent=any(r.get('goal_sent') for r in rows),
        process_failure=dict(present=False,display_marker_physics_s=None),
        claim='One new-endpoint physical attempt, no retry; endpoint/map coverage only; selected baseline unchanged')
    save('outcome.json',outcome)
    scan=capture.rows('scan_timing.jsonl');complete=[r for r in scan if 'total_s' in r]
    assert all(r['period_s']==.1 for r in scan)
    save('scanner_timing_summary.json',dict(jobs=len(scan),completed=len(complete),period_s=.1,
        deadline_failures=sum(r.get('deadline_failed',False) for r in scan),
        maximum_total_ms=max((r['total_s'] for r in complete),default=0)*1000))
    suffix=[]
    for r in reversed(telemetry):
        if r.get('stance_mode')!='FIXED_STAND':break
        suffix.append(r)
    suffix.reverse()
    duration=suffix[-1]['physics_time_s']-suffix[0]['physics_time_s'] if suffix else 0.
    save('terminal_pd_hold.json',dict(passed=bool(route['passed'] and duration>=2.),
        duration_s=duration,samples=len(suffix),source='Consecutive measured final FIXED_STAND suffix; original v232 driver requires 2s'))
    spec=importlib.util.spec_from_file_location('original_profile',VERSIONS/'v233/verify_profile.py')
    profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
    save('actual_profile_equivalence.json',profile.verify(RAW))
    receipts=RESULTS/'execution_receipts';receipts.mkdir(exist_ok=True)
    for p in EVIDENCE.glob('*.json'):shutil.copy2(p,receipts/p.name)
    for name in ('episode_request.json','result.json','initial_state.json','nav2_params.yaml','nav2_params.scan.yaml',
        'planner.yaml','backend_config.json','factory_handoff.json','locomotion_activation.json','v240_runtime_binding.json',
        'artifacts/stair_driver_result.json','artifacts/external_episode/finish_request.json','native_process_failure.json'):
        try:(receipts/name.replace('/','__')).write_text(capture.read(name))
        except (FileNotFoundError,KeyError):pass
    identity=json.loads((VERSIONS/'v243/source_identity.json').read_text())
    for name,expected in identity['files'].items():assert sha(VERSIONS/'v243'/name)==expected,name
    save('post_run_execution_parity.json',dict(passed=True,source_identity_sha256=sha(VERSIONS/'v243/source_identity.json')))
    return capture

def margins(capture):
    poses=CASEOUT/'body_poses.txt'
    with poses.open('w') as stream:
        for row in capture.rows('sensor.jsonl'):
            pose=row['body_sensor'];w,x,y,z=pose['quaternion']
            yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
            stream.write(' '.join(map(str,[row['sim_time_s']]+pose['position']+[yaw]))+'\n')
    image='sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4'
    shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /work/install/setup.bash'
    shell+=' && cmake -S /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v240_gpu5070ti_physical -B /audit/margin_build && cmake --build /audit/margin_build -j2'
    shell+=' && /audit/margin_build/body_margin /work/fixtures/building/environment225.env 10040917858432847476 /audit/body_poses.txt /audit/results/body_margins.csv'
    command=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
        '--cpus=6','--memory=6g','-v',str(PREFIX)+':/task:ro',
        '-v',str(PREFIX/'cooperative_search_v240')+':/work:ro',
        '-v',str(PREFIX/'callback_failure_v232/fixtures')+':/work/fixtures:ro',
        '-v',str(CASEOUT)+':/audit:rw','--entrypoint','/bin/bash',image,'-c',shell]
    with (RESULTS/'margin_build.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)

def windows(capture):
    rows=capture.rows('telemetry.jsonl');samples=[(r['physics_time_s'],math.hypot(*r['body_sensor']['linear_world'][:2])) for r in rows]
    intervals=low_speed_intervals(samples);scenario=capture.json('inputs/stair_scenario.json');goal=scenario['goal_ground_xyz_m']
    distance=lambda r:math.dist(r['body_sensor']['position'][:2],goal[:2])
    goal_event=None
    try:goal_event=next(r for r in capture.json('artifacts/stair_driver_result.json')['journal'] if r['event']=='goal_request')
    except (KeyError,FileNotFoundError,StopIteration):pass
    nav_start=goal_event['initial_snapshot']['sim_time_s'] if goal_event else samples[0][0]
    approach=[r for r in rows if r['physics_time_s']>=nav_start and distance(r)<=4.5 and abs(r['body_sensor']['position'][2]-(goal[2]+.3))<.5]
    terminal=next((r['physics_time_s'] for r in approach if distance(r)<=.25 and r.get('stance_mode') in ('STAND_SETTLING','STAND_TRANSITION','FIXED_STAND')),None)
    nav_end=terminal if terminal is not None else samples[-1][0]
    events=capture.rows('artifacts/reactive_observations.jsonl')
    curves=[];emergency=[]
    for event in events:
        if event.get('event')!='bspline':continue
        d=event['data'];stamp=d['start_time'];pub=event['clock_ns']*1e-9
        curves.append(dict(publication_s=pub,start_s=stamp['sec']+stamp['nanosec']*1e-9,
            duration_s=d['knots'][len(d['pos_pts'])]-d['knots'][d['order']],emergency=int(d['emergency_stop'])))
        if d['emergency_stop']:emergency.append(pub)
    class Log:
        def read_text(self):return capture.read('nav2.log')
    _,rounds=core.parse_rounds(Log())
    # The critical geometry is the same physical region as the v24145-55s
    # control, found from its actual body coordinates, independent of new timing.
    historical=Capture(PREFIX/'trials/v241_linux_full_attempt01/runs/v241_linux_full_attempt01')
    baseline=[r['body_sensor']['position'] for r in historical.rows('sensor.jsonl') if 45<=r['sim_time_s']<55]
    lower=np.min(baseline,axis=0)-.25;upper=np.max(baseline,axis=0)+.25
    critical=[r['physics_time_s'] for r in rows if np.all(np.array(r['body_sensor']['position'])>=lower) and np.all(np.array(r['body_sensor']['position'])<=upper)]
    windows={'navigation_before_terminal':(nav_start,nav_end),'raw_45_55':(45.,55.),'raw_109_115':(109.,115.)}
    if approach:windows['route_relative_approach']=(approach[0]['physics_time_s'],nav_end)
    if critical:windows['critical_stair_geometry']=(critical[0],critical[-1])
    # A separate full floor-transition interval includes staircase platforms.
    z0=scenario['spawn_ground_xyz_m'][2]+.3;z1=goal[2]+.3
    transition=[r['physics_time_s'] for r in rows if min(z0,z1)+.15<r['body_sensor']['position'][2]<max(z0,z1)-.15]
    if transition:windows['cross_floor_transition']=(transition[0],transition[-1])
    margin=list(csv.DictReader((RESULTS/'body_margins.csv').open()))
    result={}
    for name,(lo,hi) in windows.items():
        if hi<=lo:continue
        part=[r for r in rounds if lo<=r.get('ros_s',-1)<hi]
        band=[r for r in margin if lo<=float(r['time_s'])<hi];known=[r for r in band if int(r['floor_known'])]
        result[name]=dict(measured=summarize(intervals,lo,hi),recording_covers_window=samples[-1][0]>=hi,
            successful_rounds=sum(r['success'] for r in part),completed_rounds=len(part),
            emergency_times_s=[t for t in emergency if lo<=t<hi],
            active_curve_gaps=active_gaps(curves,lo,min(hi,nav_end)) if min(hi,nav_end)>lo and samples[-1][0]>=hi else None,
            edge_margin=dict(samples=len(band),known=len(known),unknown=len(band)-len(known),
                minimum_m=min((float(r['extra_edge_margin_m']) for r in known),default=None),
                saturated_ge_015_samples=sum(float(r['extra_edge_margin_m'])>=.15-1e-6 for r in known)))
    save('window_audit.json',dict(case_id=CASE,windows=result,critical_geometry_bounds=[lower.tolist(),upper.tolist()],
        geometry_source='Original v241 sensor body coordinates during45-55s, expanded0.25m; full floor-transition also reported',
        low_speed_definition='20ms measured horizontal speed <0.05m/s; startup/finalPD outside navigation window; raw time windows retained'))

def render():
    outcome=json.loads((RESULTS/'outcome.json').read_text())
    name='render_run.py' if outcome['result_json_present'] else 'render_partial.py'
    code=(PARENT/name).read_text().replace('v241','v243')
    code=code.replace('v243_linux_full_attempt01',RUN)
    code=code.replace("BASE/'versions/v243/execution_request.json'","EVIDENCE/'execution_request.json'")
    # The nested v220 module derives BASE from __file__; case output adds two
    # directory levels, so pass the same explicit experiment root after load.
    seam=";exec(compile(code,str(HERE/'executed_render_adapter.py'),'exec'),ns)"
    if name=='render_run.py':
        assert code.count(seam)==1
        code=code.replace(seam,seam+";ns.update(BASE=BASE,ROOT=BASE.parents[2],HERE=HERE)")
    else:
        seam="    exec(compile(code, str(HERE / 'render_partial.py'), 'exec'), namespace)"
        assert code.count(seam)==1
        code=code.replace(seam,seam+"\n    namespace.update(BASE=BASE,ROOT=BASE.parents[2],HERE=HERE)")
    code=code.replace('version_label = " | v240 / run v243"',f'version_label = " | v240 / v243 case {CASE}"')
    scope=dict(__file__=str(PARENT/name),__name__='v243_case_render',EVIDENCE=EVIDENCE)
    exec(compile(code,str(CASEOUT/('executed_'+name)),'exec'),scope)
    root=TASK/'video_v243_render01'
    scope.update(HERE=CASEOUT,BASE=EXP,TASK=TASK,SOURCE=RAW,ROOT=root,OUT=root/'runs/full01')
    (CASEOUT/('executed_'+name)).write_text(code)
    shutil.copy2(Path(__file__),CASEOUT/'postprocess_case.py')
    (CASEOUT/'source_identity.json').write_text(json.dumps(dict(
        files={p.name:sha(p) for p in CASEOUT.glob('*.py')},
        parent_display_adapter_sha256=sha(PARENT/name),adapted_display_sha256=hashlib.sha256(code.encode()).hexdigest(),
        execution_manifest_sha256=sha(VERSIONS/'v243/manifest.json'),physics_steps=0),indent=2)+'\n')
    if json.loads((RESULTS/'analysis_status.json').read_text())['returncode']:
        diag=RESULTS/'diagnostic_metrics';diag.mkdir(exist_ok=True)
        for n in ('metrics.json','latency.csv'):shutil.copy2(RESULTS/n,diag/n)
    (CASEOUT/'delivered').mkdir(exist_ok=True)
    scope['main']()
    source=next((CASEOUT/'delivered').glob('*.mp4'))
    destination=HERE/'delivered'/f'v243_{CASE}_full_attempt01.mp4'
    shutil.copy2(source,destination)
    save('local_video_delivery.json',dict(case_id=CASE,source_recording=RUN,
        full_recorded_attempt=True,planned_route_completed=outcome['full_route_gate_passed'],
        video=str(destination),bytes=destination.stat().st_size,sha256=sha(destination)))

def main():
    RESULTS.mkdir(parents=True,exist_ok=True)
    preserve();capture=analyze_case();margins(capture);windows(capture);render()
    print(json.dumps(json.loads((RESULTS/'outcome.json').read_text())),flush=True)

if __name__=='__main__':main()

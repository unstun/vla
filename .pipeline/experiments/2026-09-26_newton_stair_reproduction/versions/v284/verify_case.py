"""Original full-route numerical gates, replacing only expected case identity."""
from pathlib import Path
import hashlib,json,sys,math
from case_binding import CASE,SCENARIO

HERE=Path(__file__).resolve().parent
EXP=HERE.parents[1]
PARENT=EXP/'audits/2026-10-18_v240_gpu5070ti_physical/verify_full_route.py'

def verify(root):
    sys.path.insert(0,str(HERE.parent/'v196'))
    code=PARENT.read_text()
    before="    original_path = BASE / 'inputs/historical_full_building.json'\n    identity = json.loads((HERE / 'full_route_input.json').read_text())"
    after="    original_path = SCENARIO\n    identity = dict(json.loads(SCENARIO.read_text()),source_sha256=hashlib.sha256(SCENARIO.read_bytes()).hexdigest())"
    assert code.count(before)==1
    code=code.replace(before,after).replace("'historical_full'","'generalization'").replace("'v241'","'v284'")
    ns=dict(__file__=str(PARENT),__name__='v284_case_verifier',SCENARIO=SCENARIO)
    exec(compile(code,str(HERE/'adapted_case_verifier.py'),'exec'),ns)
    report=ns['verify'](root)
    from analyze_remote import Capture
    capture=Capture(root)
    assert capture.json('backend_config.json')['map']['pct_layer'] is None
    requested=json.loads(SCENARIO.read_text());driver=capture.json('artifacts/stair_driver_result.json')
    submitted=next(r for r in driver['journal'] if r['event']=='goal_request')['payload']
    assert submitted['target_yaw_rad']==requested['goal_yaw_rad']
    routes=[r['data'] for r in capture.rows('artifacts/reactive_observations.jsonl') if r['event']=='pct_route']
    q=routes[0]['poses'][-1]['pose']['orientation'];yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
    assert abs(math.remainder(yaw-requested['goal_yaw_rad'],2*math.pi))<1e-6
    report.update(requested_goal_yaw_rad=requested['goal_yaw_rad'],explicit_heading_submitted=True,published_heading_matches_request=True)

    # Preserve frozen startup code. Independently audit height relative to this
    # floor, since its old absolute-world-Z check is uninformative upstairs.
    handoff=capture.json('factory_handoff.json');rows=capture.json('video_states.json')
    row=min(rows,key=lambda r:abs(r['physics_time_s']-handoff['physics_time_s']))
    ground=json.loads(SCENARIO.read_text())['spawn_ground_xyz_m'][2]
    relative=float(row['joint_q'][2])-ground
    report.update(native_navigation='v284 execution / v284 PCT+SCAN / v216 locomotion',case_id=CASE,configured_pct_layer=None,factory_handoff_relative_height_m=relative,
        factory_relative_height_audit_passed=relative>=.25,
        inherited_verifier_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),
        adapted_verifier_sha256=hashlib.sha256(code.encode()).hexdigest(),
        claim='One new-endpoint same-map physical attempt; original arrival/PD gates; no reliability claim')
    assert relative>=.25,'Factory handoff height relative to selected floor insufficient'
    return report

if __name__=='__main__':
    root=Path(sys.argv[1])
    try:report=verify(root)
    except Exception as e:report=dict(passed=False,case_id=CASE,error=repr(e),run=root.name)
    (root/'full_route_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    raise SystemExit(0 if report['passed'] else 1)

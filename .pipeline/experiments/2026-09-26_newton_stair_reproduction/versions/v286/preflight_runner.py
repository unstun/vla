"""Case-owned scanner/identity receipts and original actual graph gate."""
from pathlib import Path
import json,os,subprocess,sys,time
from case_binding import CASE,record

HERE=Path(__file__).resolve().parent
BASE=Path('/data/sun/vla_mppi_20261009')
OUT=BASE/'generalization_v286'/CASE

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    fixture=json.loads((Path('/home/sun/vla_exec/supported_air_refinement_v286/cohort/cases')/CASE/'fixture.json').read_text())
    assert fixture['scenario_sha256']==record['scenario_sha256']
    assert fixture['physics_steps']==0 and fixture['max_scan_s']<=.1
    assert json.loads((Path('/home/sun/vla_exec/supported_air_refinement_v286/cohort/policy_golden.json')).read_text())['passed']
    tag=os.environ.get('V286_PREFLIGHT_ID','01');assert tag.isdigit() and len(tag)==2
    steps=[]
    for name,command in [('deadline_tests',[sys.executable,str(HERE.parent/'v237/test_scan_deadline.py')]),
                         ('graph',[sys.executable,str(HERE/'launch.py'),'--preflight-only'])]:
        began=time.monotonic()
        with (OUT/(name+('_'+tag if tag!='01' else '')+'.log')).open('x') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=300)
        steps.append(dict(name=name,exit_code=result.returncode,wall_s=time.monotonic()-began))
        (OUT/('preflight_steps_'+tag+'.json')).write_text(json.dumps(steps,indent=2)+'\n')
        if result.returncode:raise SystemExit(result.returncode)
    (OUT/'preflight_passed.json').write_text(json.dumps(dict(passed=True,case_id=CASE,physics_steps=0,
        case_scan_fixture=fixture['scenario_sha256'],maximum_scan_ms=fixture['max_scan_s']*1000,
        original_policy_golden_passed=True,navigation_active_checked_at_real_goal_dispatch=True,zero_step_scope='package/profile/process/scanner; no fake TF or ACTIVE claim',steps=steps),indent=2)+'\n')

if __name__=='__main__':main()

"""Bind the materialized parent execution protocol to frozen v290 navigation."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import types

R=Path('/home/ubuntu/sun/vla_v290_20261021')
P=Path('/home/ubuntu/sun/vla_v289_20261020')
M=R/'migration'
VERSIONS=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
VERSION=VERSIONS/'v290'
CASE=os.environ['V290_CASE_ID']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(M))
import benchmark


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def admission():
    import execution_policy
    return execution_policy.verify()


def verify_sources():
    benchmark.verify()
    result=admission()
    path=M/'physical_manifest01.json'
    if path.exists():
        frozen=json.loads(path.read_text())
        for rel,digest in frozen['files'].items():assert sha(R/rel)==digest,rel
        result['physical_manifest_sha256']=sha(path)
    result.update(passed=True,native_source_version='v290',bridge_source_version='v290',execution='v290',
        host='ultra9',explicit_goal_heading=True,driver_source_sha256=sha(VERSIONS/'v257/long_route_driver.py'))
    return result


def resource_admit():
    source=(VERSION/'resource_admission.py').read_text()
    old="OUTPUT_ROOT=Path('/home/sun/vla_exec/physical_runs_v290')"
    assert source.count(old)==1
    source=source.replace(old,'OUTPUT_ROOT=Path('+repr(str(R/'physical_runs'))+')')
    scope=dict(__file__=str(VERSION/'resource_admission.py'))
    exec(compile(source,str(VERSION/'resource_admission.py'),'exec'),scope)
    return scope['admit']()


def verify_profile(folder):
    parent=(VERSIONS/'v233/verify_profile.py').read_text()
    parent=parent.replace("REMOTE=Path('/data/sun/vla_mppi_20261009')",'REMOTE=Path('+repr(str(R))+')')
    parent=parent.replace("baseline=REMOTE/'trials/v219_linux_full_attempt01/runs/v219_linux_full_attempt01'",
        'baseline=Path('+repr(str(R/'profile_reference'))+')')
    parent=parent.replace("REMOTE/'callback_failure_v232/fixtures/building/environment225.env'","REMOTE/'native/fixtures/building/environment225.env'")
    source=(VERSION/'verify_profile.py').read_text().replace('source=PARENT.read_text()','source=profile_source')
    source=source.replace('/data/sun/vla_mppi_20261009/geometry_physical_v282/fixtures/building',str(R/'native/fixtures/building'))
    # Geometry is byte-identical to the parent; keep its original descriptor
    # metadata separate from the official v290 navigation manifest identity.
    geometry=json.loads((VERSIONS/'v289/native_manifest.json').read_text())
    source=source.replace("json.loads((HERE/'native_manifest.json').read_text())",'profile_native_metadata')
    scope=dict(__file__=str(VERSION/'verify_profile.py'),profile_source=parent,profile_native_metadata=geometry)
    exec(compile(source,str(VERSION/'verify_profile.py'),'exec'),scope)
    return scope['verify'](folder)


def bind_case():
    cohort=json.loads((R/'cohort/cases_manifest.json').read_text())
    ids=json.loads((R/'source/native_manifest.json').read_text())['physical_cases']
    assert ids==cohort['physical_cases'] and len(ids)==10
    record=next(c for c in cohort['cases'] if c['case_id']==CASE)
    scenario=R/'cohort/cases'/CASE/'scenario.json'
    assert sha(scenario)==record['scenario_sha256']
    def case_scenario(profile,wall_budget):
        assert profile=='generalization' and sha(scenario)==record['scenario_sha256']
        value=json.loads(scenario.read_text());assert value['case_id']==CASE and 'goal_yaw_rad' in value
        value.update(max_sim_seconds=600.,max_wall_seconds=wall_budget,
            navigation_input='native PCT, original geometric LiDAR and measured simulator localization')
        return value
    return types.SimpleNamespace(CASE=CASE,record=record,SCENARIO=scenario,case_scenario=case_scenario)


def main():
    case=bind_case()
    sys.modules['case_binding']=case
    sys.modules['resource_admission']=types.SimpleNamespace(admit=resource_admit)
    source=(M/'physical_template.py').read_text().replace('__CASE__',CASE).replace('__case__',CASE.lower())
    preflight='--preflight-only' in sys.argv
    tag=os.environ.get('V290_PREFLIGHT_ID','01');assert len(tag)==2 and tag.isdigit()
    output=R/'generalization_v290'/CASE/('preflight'+tag if preflight else 'execution')
    output.mkdir(parents=True,exist_ok=True)
    derived=output/'bound_launch.py'
    if derived.exists():assert derived.read_text()==source
    else:derived.write_text(source)
    scope=dict(__file__=str(VERSION/'launch.py'),__name__='v290_materialized_execution',EVIDENCE=output,
        case_scenario=case.case_scenario,verify_sources=verify_sources,verify_execution_admission=admission)
    exec(compile(source,str(derived),'exec'),scope)
    original_module=scope['module']
    scope['module']=lambda path,name: types.SimpleNamespace(verify=verify_profile) if path==VERSION/'verify_profile.py' else original_module(path,name)
    if '--derive-only' in sys.argv:
        print(json.dumps(dict(passed=True,physics_steps=0,scope='Materialized parent protocol and route-data binding')))
        return
    if Path(sys.argv[0]).name=='run_bounded.py':scope['supervisor']()
    elif '--episode' in sys.argv:scope['episode']()
    else:
        if preflight:scope.update(TASK=R/'physical_runs'/f'v290_{CASE}_preflight{tag}',
            RUN=f'v290_{CASE}_preflight{tag}',CONTAINER=f'v290-{CASE.lower()}-preflight{tag}')
        scope['launch']()


if __name__=='__main__':main()

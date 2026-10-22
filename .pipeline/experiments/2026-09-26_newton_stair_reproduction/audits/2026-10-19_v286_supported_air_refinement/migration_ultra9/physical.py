"""Host-only v286 physical binding; preserve frozen v241/v237 execution logic."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import types

ROOT = Path('/home/ubuntu/sun/vla_v286_20261020')
VERSIONS = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
VERSION = VERSIONS / 'v286'
MIGRATION = ROOT / 'migration'
CASE = os.environ['V286_CASE_ID']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0, str(MIGRATION))
import offline02 as offline

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def admission():
    manifest = offline.verify()
    gate = json.loads((ROOT / 'benchmark/offline_gate.json').read_text())
    complete = json.loads((ROOT / 'benchmark/complete.json').read_text())
    assert complete['all_cases_finished'] and complete['calls'] == 53
    assert complete['native_manifest_sha256'] == sha(VERSION / 'native_manifest.json')
    assert gate['passed'] and gate['positive_passed'] >= 48 and gate['illegal_correct_rejections'] == 3
    assert gate['global_median_s'] <= 1.5
    audits = json.loads((ROOT / 'benchmark/audit_ledger.json').read_text())
    assert len(audits) == 53 and all(r['exit_code'] == 0 for r in audits)
    return dict(physical_execution_authorized=True, authorized_attempts_per_case=1,
        original_native_manifest_sha256=sha(VERSION / 'native_manifest.json'),
        new_host_native_manifest_sha256=sha(offline.MANIFEST),
        strict_offline_gate_sha256=sha(ROOT / 'benchmark/offline_gate.json'),
        benchmark_acceptance_passed=True, same_53_requests=True, hard_radius_m=.35, sensor_period_s=.1)

def verify_sources():
    result = admission()
    receipt = json.loads((ROOT / 'evidence/bridge248_01.json').read_text())
    assert receipt['passed']
    for group in ('source_files', 'installed_files'):
        for rel, digest in receipt[group].items():
            assert sha(ROOT / 'bridge248/native' / rel) == digest, rel
    frozen = MIGRATION / 'physical_manifest01.json'
    if frozen.exists():
        manifest = json.loads(frozen.read_text())
        for rel, digest in manifest['files'].items():
            assert sha(ROOT / rel) == digest, rel
        result['physical_manifest_sha256'] = sha(frozen)
    result.update(passed=True, native_source_version='v286', bridge_source_version='v248',
        execution='v286', host='ultra9', explicit_goal_heading=True,
        driver_source_sha256=sha(VERSIONS / 'v257/long_route_driver.py'))
    return result

def resource_admit():
    original = (VERSION / 'resource_admission.py').read_text()
    old = "OUTPUT_ROOT=Path('/home/sun/vla_exec/physical_runs_v286')"
    assert original.count(old) == 1
    original = original.replace(old, 'OUTPUT_ROOT=Path(' + repr(str(ROOT / 'physical_runs')) + ')')
    namespace = dict(__file__=str(VERSION / 'resource_admission.py'))
    exec(compile(original, str(VERSION / 'resource_admission.py'), 'exec'), namespace)
    return namespace['admit']()

def verify_profile(folder):
    parent = (VERSIONS / 'v233/verify_profile.py').read_text()
    parent = parent.replace("REMOTE=Path('/data/sun/vla_mppi_20261009')", 'REMOTE=Path(' + repr(str(ROOT)) + ')')
    old = "baseline=REMOTE/'trials/v219_linux_full_attempt01/runs/v219_linux_full_attempt01'"
    assert parent.count(old) == 1
    parent = parent.replace(old, 'baseline=Path(' + repr(str(ROOT / 'profile_reference')) + ')')
    parent = parent.replace("REMOTE/'callback_failure_v232/fixtures/building/environment225.env'", "REMOTE/'native/fixtures/building/environment225.env'")
    source = (VERSION / 'verify_profile.py').read_text()
    assert source.count('source=PARENT.read_text()') == 1
    source = source.replace('source=PARENT.read_text()', 'source=profile_source')
    source = source.replace('/data/sun/vla_mppi_20261009/geometry_physical_v282/fixtures/building', str(ROOT / 'native/fixtures/building'))
    namespace = dict(__file__=str(VERSION / 'verify_profile.py'), profile_source=parent)
    exec(compile(source, str(VERSION / 'verify_profile.py'), 'exec'), namespace)
    return namespace['verify'](folder)

def bind_case():
    if '--derive-only' in sys.argv:
        cohort = json.loads((ROOT / 'cohort/cases_manifest.json').read_text())
        selected = [next(c for c in cohort['cases'] if c['case_id'] == cid) for cid in cohort['physical_cases']]
    else:
        selected = json.loads((ROOT / 'benchmark/selection.json').read_text())['selected']
    assert len(selected) == 10 and [c['case_id'] for c in selected] == json.loads(offline.MANIFEST.read_text())['physical_cases']
    record = next(c for c in selected if c['case_id'] == CASE)
    scenario = ROOT / 'cohort/cases' / CASE / 'scenario.json'
    assert sha(scenario) == record['scenario_sha256']
    def case_scenario(profile, wall_budget):
        assert profile == 'generalization'
        assert sha(scenario) == record['scenario_sha256']
        value = json.loads(scenario.read_text())
        assert value['case_id'] == CASE and 'goal_yaw_rad' in value
        value.update(max_sim_seconds=600., max_wall_seconds=wall_budget,
            navigation_input='native PCT, original geometric LiDAR and measured simulator localization')
        return value
    return types.SimpleNamespace(CASE=CASE, record=record, SCENARIO=scenario, case_scenario=case_scenario)

def adapt_host(source):
    changes = {
        '/data/sun/vla_mppi_20261009': str(ROOT),
        '/home/sun/vla_exec/supported_air_refinement_v286/native': str(ROOT / 'native'),
        '/home/sun/vla_exec/physical_runs_v286': str(ROOT / 'physical_runs'),
        '/home/sun/vla_exec/envs/newton_worker/bin/python': offline.PRIVATE_PYTHON,
        offline.IMAGE.replace('ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343', '5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4'): offline.IMAGE,
        '/task/physical_traversability_v248/native/': '/task/bridge248/native/',
        '{REMOTE}/geometry_physical_v282/fixtures:/work/fixtures:ro': '{REMOTE}/native/fixtures:/work/fixtures:ro',
        "VERSIONS/'v286/results/offline_gate.json'": "REMOTE/'benchmark/offline_gate.json'",
        "str(VERSIONS/'v233/bin')": "str(REMOTE/'migration/bin')",
        "str(UNDERLAY/'host_python')": "str(BASE/'runtime_sources/backend_adapter')",
        "str(HERE/'preflight.py')": "str(REMOTE/'migration/preflight.py')",
        "str(HERE/'launch.py')": "str(REMOTE/'migration/physical.py')",
        "symlink_to(HERE/'launch.py')": "symlink_to(REMOTE/'migration/physical.py')",
        "assert (HERE/'manifest.json').is_file(), 'Freeze execution identity before physics'": "assert (REMOTE/'migration/physical_manifest01.json').is_file(), 'Freeze migration execution identity before physics'",
        "shutil.copyfile(V219/'manifest.json',destination/'integration_version.json')": "shutil.copyfile(REMOTE/'migration/physical_manifest01.json',destination/'integration_version.json')",
    }
    for before, after in changes.items():
        assert before in source, before
        source = source.replace(before, after)
    for name in ('recovery_v188', 'command_continuity_v206_20261015'):
        source = source.replace('source /task/' + name + '/install/setup.bash && ', '')
        source = source.replace('"source /task/' + name + '/install/setup.bash", ', '')
    old = "    sync=json.loads((V206/'results/v206_linux_full_attempt02/sync_manifest.json').read_text())\n    for rel,record in sync.items():assert sha(ROOT/rel)==record['sha256'],rel"
    assert source.count(old) == 1
    source = source.replace(old, '    verify_sources()  # Same sources guarded by the new-host manifests.')
    old = "'-v',f'{UNDERLAY}:/task:ro','-v',f'{WORK}:/work:ro',"
    assert source.count(old) == 1
    source = source.replace(old, old + "'-v',f'{REMOTE}:{REMOTE}:ro',")
    # A container invokes the same launcher for the worker and supervisor. Every
    # recursive entry therefore uses this adapter; frozen sources stay read-only.
    output = ROOT / 'generalization_v286' / CASE / ('preflight' + os.environ.get('V286_PREFLIGHT_ID', '01') if '--preflight-only' in sys.argv else 'execution')
    output.mkdir(parents=True, exist_ok=True)
    name = 'derived_launch_' + ('preflight' if '--preflight-only' in sys.argv else 'execution') + '.py'
    path = output / name
    if path.exists():
        assert path.read_text() == source
    else:
        path.write_text(source)
    return source

def main():
    case = bind_case()
    sys.modules['case_binding'] = case
    sys.modules['identity'] = types.SimpleNamespace(verify_sources=verify_sources)
    sys.modules['execution_admission'] = types.SimpleNamespace(verify=admission)
    sys.modules['resource_admission'] = types.SimpleNamespace(admit=resource_admit)
    frozen = VERSION / 'launch.py'
    source = frozen.read_text()
    source = source[:source.rindex("if __name__=='__main__':")]
    needle = "exec(compile(source,str(HERE/'adapted_v241_launch.py'),'exec'),namespace)"
    assert source.count(needle) == 1
    source = source.replace(needle, 'source=adapt_host(source)\n' + needle)
    source = source.replace("Path('/data/sun/vla_mppi_20261009/generalization_v286')", 'Path(' + repr(str(ROOT / 'generalization_v286')) + ')')
    source = source.replace("('preflight' if '--preflight-only' in sys.argv else 'execution')", "('preflight'+os.environ.get('V286_PREFLIGHT_ID','01') if '--preflight-only' in sys.argv else 'execution')")
    namespace = dict(__file__=str(frozen), __name__='new_host_frozen_launch', adapt_host=adapt_host)
    exec(compile(source, str(frozen), 'exec'), namespace)
    runner = namespace['namespace']
    original_module = runner['module']
    def module(path, name):
        if path == VERSION / 'verify_profile.py':
            return types.SimpleNamespace(verify=verify_profile)
        return original_module(path, name)
    runner['module'] = module
    if '--derive-only' in sys.argv:
        print(json.dumps(dict(passed=True, scope='Compile definitions and explicit host rebindings only', physics_steps=0)))
        return
    if Path(sys.argv[0]).name == 'run_bounded.py':
        runner['supervisor']()
    elif '--episode' in sys.argv:
        runner['episode']()
    else:
        if '--preflight-only' in sys.argv:
            tag = os.environ.get('V286_PREFLIGHT_ID', '01')
            assert len(tag) == 2 and tag.isdigit()
            runner.update(TASK=ROOT / 'physical_runs' / f'v286_{CASE}_preflight{tag}',
                RUN=f'v286_{CASE}_preflight{tag}', CONTAINER=f'v286-{CASE.lower()}-preflight{tag}')
        runner['launch']()

if __name__ == '__main__':
    main()

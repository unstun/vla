import importlib.util
import json
from pathlib import Path
import stat
import sys

import pytest


HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'native_suite/scan_fix_native_suite'
DIAGNOSIS = HERE.parent / 'scan_replan_diagnosis'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rc = load(PACKAGE / 'scripts/run_cases.py', 'suite_run_cases_test')
cs = load(HERE / 'container_suite.py', 'container_suite_test')


def test_legacy_case_produces_the_diagnosis_command():
    cases = {c['id']: c for c in json.loads((DIAGNOSIS / 'inputs/cases.json').read_text())['cases']}
    recorded = json.loads((DIAGNOSIS / 'runs/native_original_20260916T180500Z/returned_artifacts/cases_result.json').read_text())
    for entry in recorded:
        command = entry['command']
        ours = rc.build_command(command[0], '/inputs/planner.yaml', cases[entry['id']], 101)
        assert ours == command


def test_suite_fields_map_to_flags():
    case = {'start': [-1.2, -4.5, 1.86], 'target': [0.35, -4.49, 1.91], 'random_poly': True, 'seed': 7,
            'occupied_boxes': 'boxes/a.json', 'follow_up_offsets_s': [0.3, 0.6], 'dump_samples': True}
    command = rc.build_command('/exe', '/p.yaml', case, 101, fixtures_root='/inputs/fixtures', print_samples=False)
    assert command[command.index('--random-poly') + 1] == 'true'
    assert command[command.index('--seed') + 1] == '7'
    assert command[command.index('--occupied-boxes') + 1] == '/inputs/fixtures/boxes/a.json'
    assert command[command.index('--follow-up-offsets') + 1] == '0.3,0.6'
    assert command[command.index('--dump-samples') + 1] == 'true'
    assert command[command.index('--print-samples') + 1] == 'false'
    assert command[-3:] == ['--ros-args', '--params-file', '/p.yaml']
    plain = rc.build_command('/exe', '/p.yaml', dict(case, occupied_boxes=None, follow_up_offsets_s=[],
                                                     dump_samples=False), 101)
    assert '--occupied-boxes' not in plain and '--follow-up-offsets' not in plain and '--dump-samples' not in plain
    with pytest.raises(ValueError):
        rc.build_command('/exe', '/p.yaml', case, 101)
    with pytest.raises(ValueError):
        rc.build_command('/exe', '/p.yaml', dict(case, follow_up_offsets_s=[0.6, 0.3]), 101, fixtures_root='/f')


def test_every_frozen_fixture_run_builds_a_command():
    doc = json.loads((HERE / 'fixtures/suite_cases.json').read_text())
    commands = [rc.build_command('/exe', '/p.yaml', run, 101, fixtures_root='/inputs/fixtures', print_samples=False)
                for run in doc['runs']]
    assert len(commands) == 834
    assert sum('--occupied-boxes' in c for c in commands) == 546
    assert sum('--follow-up-offsets' in c for c in commands) == 15
    assert sum('--dump-samples' in c for c in commands) == 3


def test_validate_source_passes():
    module = load(PACKAGE / 'scripts/validate_source.py', 'suite_validate_source_test')
    assert module.main() == 0


def test_cpp_keeps_the_original_options_and_lines():
    ours = (PACKAGE / 'src/rebound_replan_suite.cpp').read_text()
    original = (DIAGNOSIS / 'native_repro/scan_replan_native_repro/src/rebound_replan_repro.cpp').read_text()
    for token in ('"--start"', '"--start-vel"', '"--start-acc"', '"--target"', '"--target-vel"', '"--poly-init"',
                  '"--random-poly"', '"--seed"', '"--samples"', 'INPUT start=', 'PARAMETERS manager.max_vel=',
                  'NATIVE_FIRST_CALL_NOTE', 'POLY_INIT_DIAGNOSTICS', 'REBOUND_REPLAN_RESULT success=',
                  'TRAJECTORY traj_id=', 'SUMMARY max_vel_norm=', 'REBOUND_REPLAN_REPRO_ERROR'):
        assert token in original and token in ours, token
    for flag in ('"--occupied-boxes"', '"--follow-up-offsets"', '"--dump-samples"', '"--print-samples"'):
        assert flag in ours


FAKE = '''#!{python}
import sys, time
args = sys.argv[1:]
value = lambda flag: args[args.index(flag) + 1] if flag in args else None
if value('--seed') == '9':
    time.sleep(3)
print('SUITE_CALL_BEGIN call=0 attempt=0')
print('SUITE_CALL_END call=0 attempt=0 success=%s' % ('true' if value('--random-poly') == 'false' else 'false'))
print('ARGS ' + ' '.join(args))
sys.exit(0 if value('--random-poly') == 'false' else 2)
'''


def test_container_runner_with_fake_executable(tmp_path, monkeypatch):
    exe = tmp_path / 'fake_exe'
    exe.write_text(FAKE.format(python=sys.executable))
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    fixtures = tmp_path / 'fixtures'
    (fixtures / 'boxes').mkdir(parents=True)
    runs = [
        {'label': 'a', 'start': [0, 0, 1], 'target': [1, 0, 1], 'random_poly': False, 'seed': 0,
         'occupied_boxes': 'boxes/a.json'},
        {'label': 'b', 'start': [0, 0, 1], 'target': [1, 0, 1], 'random_poly': True, 'seed': 1,
         'follow_up_offsets_s': [0.3]},
        {'label': 'c', 'start': [0, 0, 1], 'target': [1, 0, 1], 'random_poly': True, 'seed': 9},
    ]
    (fixtures / 'suite_cases.json').write_text(json.dumps({'runs': runs}))
    monkeypatch.setattr(cs, 'CASE_CEILING_S', 1)
    out = tmp_path / 'out'
    code = cs.main(['--build', 'candidate', '--fixtures', str(fixtures / 'suite_cases.json'), '--params', '/p.yaml',
                    '--executable', str(exe), '--run-cases', str(PACKAGE / 'scripts/run_cases.py'), '--out', str(out)])
    results = {r['label']: r for r in json.loads((out / 'cases_result.json').read_text())}
    assert [results[k]['returncode'] for k in 'abc'] == [0, 2, 124]
    assert code == 1
    log = (out / 'a.log').read_text()
    assert '--occupied-boxes %s' % (fixtures / 'boxes/a.json') in log and '--print-samples false' in log
    assert '--follow-up-offsets 0.3' in (out / 'b.log').read_text()
    assert results['a']['build'] == 'candidate' and results['a']['command'][0] == str(exe)

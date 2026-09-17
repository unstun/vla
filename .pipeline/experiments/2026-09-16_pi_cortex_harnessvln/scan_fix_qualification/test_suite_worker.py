import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, str(HERE / (name + '.py')))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sw = load('suite_worker')
sr = sys.modules['suite_remote']
SCAN03_CPP = sw.BUILDS / 'scan_03' / sw.MANAGER_REL
DIAGNOSIS_RESULT = HERE.parent / 'scan_replan_diagnosis/runs/native_original_20260916T180500Z/returned_artifacts/result.json'
RUN_ID = 'native_suite_20260917T000000Z'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def candidate_bytes(original, line=171, old=b'evaluateAcc(t)', new=b'evaluateAcc(time)'):
    lines = original.splitlines(keepends=True)
    lines[line - 1] = lines[line - 1].replace(old, new)
    return b''.join(lines)


def write_build(root, name, cpp, fix=True):
    build = root / name
    (build / sw.MANAGER_REL).parent.mkdir(parents=True)
    (build / sw.MANAGER_REL).write_bytes(cpp)
    other = build / 'src/plan_env/CMakeLists.txt'
    other.parent.mkdir(parents=True)
    other.write_bytes(b'project(plan_env)\n')
    ids = {'src/plan_env/CMakeLists.txt': sha(other.read_bytes()), sw.MANAGER_REL: sha(cpp)}
    (build / 'source_sha256.json').write_text(json.dumps(ids))
    (build / 'build_result.json').write_text(json.dumps({'passed': True}))
    if name == 'scan_03':
        (build / 'install/plan_env/lib').mkdir(parents=True)
        (build / 'install/plan_env/lib/libplan_env.a').write_bytes(b'archive')
        (build / 'install_identity.json').write_text(json.dumps(
            {'installed_files': {'install/plan_env/lib/libplan_env.a': sha(b'archive')}}))
    elif fix:
        (build / 'terminal_accel_fix_manifest.json').write_text(json.dumps(
            {'before_sha256': sw.BASE_SHA256, 'after_sha256': sha(cpp)}))
    return build


@pytest.fixture
def builds(tmp_path):
    original = SCAN03_CPP.read_bytes()
    assert sha(original) == sw.BASE_SHA256
    root = tmp_path / 'builds'
    return (write_build(root, 'scan_03', original), write_build(root, 'scan_04', candidate_bytes(original)))


def args_for(tmp_path, builds, *extra):
    return ['--run-id', RUN_ID, '--original-build-dir', str(builds[0]), '--candidate-build-dir', str(builds[1]),
            '--local-runs-root', str(tmp_path / 'runs'), *extra]


@pytest.fixture
def no_subprocess(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError('subprocess must not be called: %r' % (args,))
    monkeypatch.setattr(sw.subprocess, 'run', refuse)


def test_dry_run_prints_commands_and_counts_and_writes_nothing(tmp_path, builds, capsys, no_subprocess):
    assert sw.main(args_for(tmp_path, builds, '--dry-run')) == 0
    out = json.loads(capsys.readouterr().out)
    assert not (tmp_path / 'runs').exists()
    assert out['mode'] == 'dry_run' and out['preflight_passed'] and out['failed_checks'] == []
    assert out['runs_per_build'] == 834 and out['process_runs_total'] == 1668
    assert out['planned_steps_per_build'] == 864
    assert out['ceilings_s'] == {'build_each': 180, 'replay_each': 900, 'case_each': 20, 'remote_total': 2280}
    commands = out['commands']
    remote = '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/scan_fix_qualification/' + RUN_ID
    assert commands['remote_run'] == remote
    assert commands['remote_candidate_build'].endswith('/p2b/builds/scan_04')
    assert commands['mkdir'][:6] == ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', 'gpu5070ti']
    assert 'assert not p.exists()' in commands['mkdir'][-1] and remote in commands['mkdir'][-1]
    assert commands['sync'][:2] == ['rsync', '-a'] and commands['sync'][2].startswith('--files-from=')
    assert commands['sync'][-1] == 'gpu5070ti:%s/' % remote
    assert commands['run'][-1] == 'timeout --kill-after=30 2280 python3 %s/suite_remote.py' % remote
    assert commands['collect'][-2] == 'gpu5070ti:%s/artifacts/' % remote
    build = commands['remote_container_commands']['candidate']['build']
    assert build[:5] == ['podman', 'run', '--rm', '--pull=never', '--network=none']
    assert sw.IMAGE in build and '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03:/scan_03:ro' in build
    assert '-DSCAN_MANAGER_CPP=/managers/candidate/planner_manager.cpp' in build[-1]
    replay = commands['remote_container_commands']['original']['replay'][-1]
    assert 'python3 /container_suite.py --build original' in replay


def test_build_script_matches_the_diagnosis_flags():
    recorded = json.loads(DIAGNOSIS_RESULT.read_text())['build']['command'][-1]
    ours = sr.build_script('original').replace('/managers/original/planner_manager.cpp', '/manager/planner_manager.cpp')
    assert ours == recorded


def test_dry_run_reports_missing_candidate_build(tmp_path, builds, capsys, no_subprocess):
    (builds[1] / 'build_result.json').unlink()
    (builds[1] / 'source_sha256.json').unlink()
    assert sw.main(args_for(tmp_path, builds, '--dry-run')) == 0
    out = json.loads(capsys.readouterr().out)
    assert not out['preflight_passed']
    assert set(out['failed_checks']) == {'candidate_manager_in_source_manifest', 'candidate_build_passed',
                                         'source_manifests_differ_only_in_manager'}


def test_default_prepares_an_immutable_package(tmp_path, builds, capsys, no_subprocess):
    assert sw.main(args_for(tmp_path, builds)) == 0
    assert json.loads(capsys.readouterr().out)['mode'] == 'prepared'
    run = tmp_path / 'runs' / RUN_ID
    manifest = json.loads((run / 'package_manifest.json').read_text())
    assert all(sha((run / p).read_bytes()) == h for p, h in manifest.items())
    for required in ('request.json', 'suite_remote.py', 'container_suite.py', 'inputs/planner.yaml',
                     'inputs/fixtures/suite_cases.json', 'inputs/fixtures/boxes/failed_run_resume__near_box.json',
                     'inputs/scan_source_identity.json', 'inputs/scan_install_identity.json',
                     'inputs/candidate_source_identity.json', 'managers/original/planner_manager.cpp',
                     'managers/candidate/planner_manager.cpp', 'managers/manager_identity.json',
                     'native_suite/scan_fix_native_suite/src/rebound_replan_suite.cpp',
                     'native_suite/scan_fix_native_suite/scripts/run_cases.py'):
        assert required in manifest, required
    assert len([p for p in manifest if p.startswith('inputs/fixtures/boxes/')]) == 42
    synced = (run / 'sync_files.txt').read_text().split()
    assert sorted(synced) == sorted(list(manifest) + ['package_manifest.json'])
    request = json.loads((run / 'request.json').read_text())
    assert request['default_execute'] is False
    assert request['execute_requires'] == ['--execute', '--lead-authorized-execute']
    assert request['fixtures']['runs_per_build'] == 834
    assert request['thresholds']['sha256'] == sha((HERE / 'thresholds.json').read_bytes())
    identity = json.loads((run / 'managers/manager_identity.json').read_text())
    assert identity['one_line_diff']['ok'] and identity['one_line_diff']['changed_lines'] == [171]
    assert identity['original']['sha256'] == sw.BASE_SHA256
    assert not (run / 'return_verdict.json').exists()
    with pytest.raises(sw.Refused):
        sw.main(args_for(tmp_path, builds))


def test_prepared_package_passes_the_remote_source_gate(tmp_path, builds, capsys, no_subprocess, monkeypatch):
    sw.main(args_for(tmp_path, builds))
    run = tmp_path / 'runs' / RUN_ID
    request = json.loads((run / 'request.json').read_text())
    request.update(remote_original_build=str(builds[0]), remote_candidate_build=str(builds[1]))
    monkeypatch.setattr(sr, 'ROOT', run)
    gate = sr.source_gate(request)[0]
    assert gate['all_match'], gate
    (builds[1] / sw.MANAGER_REL).write_bytes(b'changed')
    assert not sr.source_gate(request)[0]['all_match']


def test_execute_requires_lead_authorization(tmp_path, builds, no_subprocess):
    with pytest.raises(sw.Refused):
        sw.main(args_for(tmp_path, builds, '--execute'))
    assert not (tmp_path / 'runs').exists()
    with pytest.raises(sw.Refused):
        sw.main(args_for(tmp_path, builds, '--execute', '--dry-run', '--lead-authorized-execute'))


def test_preflight_refuses_a_second_changed_line(tmp_path, no_subprocess):
    original = SCAN03_CPP.read_bytes()
    changed = candidate_bytes(candidate_bytes(original), line=170, old=b'(0)', new=b'(0.0)')
    root = tmp_path / 'builds'
    builds = (write_build(root, 'scan_03', original), write_build(root, 'scan_04', changed))
    gate = sw.preflight(builds[0], builds[1], sw.FIXTURES, sw.analyze_suite.THRESHOLDS, sw.analyze_suite.PLAN)
    failed = {c['name'] for c in gate['checks'] if not c['passed']}
    assert 'manager_one_line_diff' in failed and gate['diff']['changed_lines'] == [170, 171]
    with pytest.raises(sw.Refused):
        sw.main(args_for(tmp_path, builds))


def test_one_line_diff_rules():
    original = SCAN03_CPP.read_bytes()
    assert sw.one_line_diff(original, candidate_bytes(original))['ok']
    assert sw.one_line_diff(original, original)['reason'].startswith('changed lines')
    lines = original.splitlines(keepends=True)
    ending = lines[170][len(lines[170].rstrip(b'\r\n')):]
    other = b'\n' if ending == b'\r\n' else b'\r\n'
    lines[170] = lines[170].rstrip(b'\r\n').replace(b'evaluateAcc(t)', b'evaluateAcc(time)') + other
    assert sw.one_line_diff(original, b''.join(lines))['reason'] == 'line terminator changed'
    wrong = candidate_bytes(original, new=b'evaluateAcc(t + ts)')
    assert sw.one_line_diff(original, wrong)['reason'] == 'line text is not the recorded change'
    assert sw.one_line_diff(original, original + b'\n')['reason'] == 'line count differs'


def test_alternate_fixtures_and_run_id(tmp_path, builds, capsys, no_subprocess):
    mf = load('make_fixtures')
    doc, boxes = mf.from_journals([make_returned(tmp_path)])
    mf.write_outputs(tmp_path / 'replay', doc, boxes)
    run_id = 'native_replay_c5_20260917T010000Z'
    argv = args_for(tmp_path, builds, '--fixtures', str(tmp_path / 'replay/suite_cases.json'))
    argv[1] = run_id
    assert sw.main(argv) == 0
    out = json.loads(capsys.readouterr().out)
    assert out['runs_per_build'] == 15 and out['process_runs_total'] == 30
    request = json.loads((tmp_path / 'runs' / run_id / 'request.json').read_text())
    assert request['run_id'] == run_id and request['fixtures']['runs_per_build'] == 15
    assert request['remote_run'].endswith('/scan_fix_qualification/' + run_id)


def make_returned(tmp_path):
    returned = tmp_path / 'two_goal_y' / 'returned_artifacts'
    returned.mkdir(parents=True)
    entry = {'request_id': 'two_goal_y-goal-a-attempt-2', 'goal_id': 'goal-a', 'ok': True,
             'request': {'start_xyz_m': [-1.2, -4.5, 1.51], 'target_xyz_m': [0.39, -4.46, 1.56]},
             'waypoints_m': [[0.3546, -4.4868, 1.9105]], 'z_semantics': 'lite3_body_reference_no_display_offset'}
    (returned / 'pilot_journal.json').write_text(json.dumps({'events': [{'state': {'pct': {'plan_history': [entry]}}}]}))
    (returned / 'artifact_hashes.json').write_text(json.dumps(
        {'pilot_journal.json': sha((returned / 'pilot_journal.json').read_bytes())}))
    (returned / 'resolved_backend_config.json').write_text(
        json.dumps({'resolved_config': {'map': {'nominal_body_height_m': 0.35}}}))
    return returned


def test_invalid_run_id_and_ceiling_are_refused(tmp_path, builds, no_subprocess):
    argv = args_for(tmp_path, builds, '--dry-run')
    argv[1] = '../escape'
    with pytest.raises(sw.Refused):
        sw.main(argv)
    with pytest.raises(sw.Refused):
        sw.main(args_for(tmp_path, builds, '--dry-run', '--replay-ceiling-s', '5'))


def fake_remote(run, commands):
    """Simulate the remote side: produce artifacts with a hash manifest for the collect step."""
    returned = run / 'returned_artifacts'
    (returned / 'original').mkdir(parents=True)
    (returned / 'original/x.log').write_text('log\n')
    (returned / 'result.json').write_text(json.dumps({'source_gate': {'all_match': True}, 'replay_completed': True,
                                                     'owned_containers_absent': True}))
    hashes = {p.relative_to(returned).as_posix(): sha(p.read_bytes()) for p in returned.rglob('*') if p.is_file()}
    (returned / 'artifact_hashes.json').write_text(json.dumps(hashes))


def test_execute_runs_the_four_steps_and_verifies_returns(tmp_path, builds, capsys, monkeypatch):
    sw.main(args_for(tmp_path, builds))
    run = tmp_path / 'runs' / RUN_ID
    calls = []

    def fake(label, command, log_path, timeout):
        calls.append((label, command, timeout))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(label)
        if label == 'collect':
            fake_remote(run, command)

    monkeypatch.setattr(sw, 'run_command', fake)
    assert sw.main(args_for(tmp_path, builds, '--execute', '--lead-authorized-execute')) == 0
    assert [c[0] for c in calls] == ['mkdir', 'sync', 'run', 'collect']
    assert calls[2][2] == 2280 + 120
    verdict = json.loads((run / 'return_verdict.json').read_text())
    assert verdict['returned_hashes_match'] and verdict['remote_source_gate_passed']
    with pytest.raises(sw.Refused):
        sw.main(args_for(tmp_path, builds, '--execute', '--lead-authorized-execute'))


def test_execute_collects_after_a_remote_failure(tmp_path, builds, monkeypatch):
    sw.main(args_for(tmp_path, builds))
    run = tmp_path / 'runs' / RUN_ID
    calls = []

    def fake(label, command, log_path, timeout):
        calls.append(label)
        if label == 'run':
            raise RuntimeError('remote worker failed')
        if label == 'collect':
            fake_remote(run, command)

    monkeypatch.setattr(sw, 'run_command', fake)
    with pytest.raises(RuntimeError):
        sw.main(args_for(tmp_path, builds, '--execute', '--lead-authorized-execute'))
    assert calls == ['mkdir', 'sync', 'run', 'collect']
    verdict = json.loads((run / 'return_verdict.json').read_text())
    assert verdict['run_error'] == 'remote worker failed' and verdict['returned_hashes_match']


def test_tampered_package_is_refused_before_any_remote_step(tmp_path, builds, capsys, monkeypatch):
    sw.main(args_for(tmp_path, builds))
    run = tmp_path / 'runs' / RUN_ID
    with (run / 'inputs/fixtures/suite_cases.json').open('a') as stream:
        stream.write(' ')
    monkeypatch.setattr(sw, 'run_command', lambda *a, **k: pytest.fail('remote step attempted'))
    with pytest.raises(sw.Refused):
        sw.main(args_for(tmp_path, builds, '--execute', '--lead-authorized-execute'))
    (run / 'inputs/fixtures/suite_cases.json').write_bytes((HERE / 'fixtures/suite_cases.json').read_bytes())
    commands = json.loads((run / 'commands.json').read_text())
    commands['run'][-1] = 'rm -rf /'
    (run / 'commands.json').write_text(json.dumps(commands))
    with pytest.raises(sw.Refused):
        sw.main(args_for(tmp_path, builds, '--execute', '--lead-authorized-execute'))


class FakePodman:
    def __init__(self, root, fail_build=None):
        self.root = root
        self.fail_build = fail_build
        self.calls = []

    def __call__(self, cmd, **kwargs):
        import types
        self.calls.append(cmd)
        code = 0
        if cmd[:2] == ['podman', 'run']:
            name = cmd[cmd.index('--name') + 1]
            variant = 'original' if '-original-' in name else 'candidate'
            if '-build-' in name:
                if variant == self.fail_build:
                    code = 1
                else:
                    exe = self.root / ('work_' + variant) / 'install/scan_fix_native_suite/lib/scan_fix_native_suite/rebound_replan_suite'
                    exe.parent.mkdir(parents=True)
                    exe.write_bytes(variant.encode())
            else:
                (self.root / 'artifacts' / variant / 'cases_result.json').write_text('[]\n')
        elif cmd[:3] == ['podman', 'container', 'exists']:
            code = 1
        return types.SimpleNamespace(returncode=code, stderr='')


def prepared_remote(tmp_path, builds, monkeypatch, capsys):
    sw.main(args_for(tmp_path, builds))
    capsys.readouterr()
    run = tmp_path / 'runs' / RUN_ID
    request = json.loads((run / 'request.json').read_text())
    request.update(remote_original_build=str(builds[0]), remote_candidate_build=str(builds[1]))
    (run / 'request.json').write_text(json.dumps(request))
    manifest = json.loads((run / 'package_manifest.json').read_text())
    manifest['request.json'] = sha((run / 'request.json').read_bytes())
    (run / 'package_manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(sr, 'ROOT', run)
    return run


def test_remote_worker_builds_and_replays_both_variants(tmp_path, builds, capsys, monkeypatch):
    run = prepared_remote(tmp_path, builds, monkeypatch, capsys)
    fake = FakePodman(run)
    monkeypatch.setattr(sr.subprocess, 'run', fake)
    assert sr.main() == 0
    result = json.loads((run / 'artifacts/result.json').read_text())
    assert result['source_gate']['all_match'] and result['replay_completed'] and result['owned_containers_absent']
    assert all(result['after_run'].values())
    stages = [c[c.index('--name') + 1] for c in fake.calls if c[:2] == ['podman', 'run']]
    assert stages == ['vla-scan-fixq-%s-%s-native-suite-20260917t000000z' % (s, v)
                      for v in ('original', 'candidate') for s in ('build', 'replay')]
    assert result['variants']['original']['executable_sha256'] != result['variants']['candidate']['executable_sha256']
    assert (run / 'work_candidate/src/scan_fix_native_suite/src/rebound_replan_suite.cpp').is_file()
    hashes = json.loads((run / 'artifacts/artifact_hashes.json').read_text())
    assert set(hashes) == {'result.json', 'original/cases_result.json', 'candidate/cases_result.json',
                           'build_original.log', 'replay_original.log', 'build_candidate.log', 'replay_candidate.log'}


def test_remote_worker_stops_on_a_failed_gate_or_build(tmp_path, builds, capsys, monkeypatch):
    run = prepared_remote(tmp_path, builds, monkeypatch, capsys)
    fake = FakePodman(run, fail_build='original')
    monkeypatch.setattr(sr.subprocess, 'run', fake)
    assert sr.main() == 1
    result = json.loads((run / 'artifacts/result.json').read_text())
    assert 'build failed for original' in result['error'] and 'candidate' not in result['variants']
    assert len([c for c in fake.calls if c[:2] == ['podman', 'rm']]) == 4
    import shutil
    shutil.rmtree(run / 'artifacts')
    (builds[0] / 'install/plan_env/lib/libplan_env.a').write_bytes(b'other')
    fake = FakePodman(run)
    monkeypatch.setattr(sr.subprocess, 'run', fake)
    assert sr.main() == 1
    result = json.loads((run / 'artifacts/result.json').read_text())
    assert 'source gate failed' in result['error']
    assert result['source_gate']['original_scan_install']['mismatched'] == ['install/plan_env/lib/libplan_env.a']
    assert not [c for c in fake.calls if c[:2] == ['podman', 'run']]

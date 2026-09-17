#!/usr/bin/env python3
"""Prepare, and only on explicit authorization execute, the native SCAN A/B suite.

Default: hash-check the local sources and write an immutable run package under runs/<run-id>;
nothing is sent anywhere. --dry-run writes nothing and prints every command and the case count.
--execute --lead-authorized-execute syncs the whitelisted package to a new remote directory, runs
suite_remote.py (source gate, two builds, replay, cleanup), collects the artifacts and verifies
their hashes locally. --fixtures and --run-id let later Isaac stop poses be replayed the same way.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
REPO = EXPERIMENT.parents[2]
sys.path.insert(0, str(HERE))
import analyze_suite  # noqa: E402
import suite_remote  # noqa: E402

BUILDS = EXPERIMENT / 'p2b_execution/builds'
FIXTURES = HERE / 'fixtures/suite_cases.json'
PLANNER_YAML = EXPERIMENT / 'scan_replan_diagnosis/inputs/planner.yaml'
PLANNER_YAML_SHA256 = '851a6eb51b3175365fd5b7e58eeb8beb170259178dcbf1407da422075226d47b'
PACKAGE_DIR = HERE / 'native_suite'
IMAGE = 'e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8'
HOST = 'gpu5070ti'
REMOTE_P2B = '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b'
REMOTE_RUNS = REMOTE_P2B + '/scan_fix_qualification'
MANAGER_REL = 'src/plan_manage/src/planner_manager.cpp'
BASE_SHA256 = '0c51df6396f32d2563d50be0a16f3346c82a5c4d5659acb18b898da1df463981'
LINE_NUMBER = 171
BEFORE_LINE = '        start_end_derivatives.push_back(gl_traj.evaluateAcc(t));'
AFTER_LINE = '        start_end_derivatives.push_back(gl_traj.evaluateAcc(time));'
BUILD_CEILING_S = 180
CASE_CEILING_S = 20
DEFAULT_REPLAY_CEILING_S = 900
RUN_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_]{2,80}$')
LABEL = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_]{0,180}$')
BUILD_NAME = re.compile(r'^scan_[0-9]{2}$')
SCOPE = 'Native SCAN planner-only A/B replay; no Isaac, controller, sensor publisher, physical driver or GPU workload'
CLAIM = ('Prepared native planner evidence only. A pass supports the fix at the SCANPlannerManager boundary '
         'for these fixtures; it is not an Isaac, controller or physical-robot result.')


class Refused(RuntimeError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def rel(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def load_json(path):
    return json.loads(Path(path).read_text())


def one_line_diff(original, candidate):
    """Check that candidate differs from original only by the recorded line-171 token change."""
    a = original.splitlines(keepends=True)
    b = candidate.splitlines(keepends=True)
    changed = [i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y]
    result = {'ok': False, 'changed_lines': changed[:10], 'line_count': [len(a), len(b)]}
    if len(a) != len(b):
        result['reason'] = 'line count differs'
        return result
    if changed != [LINE_NUMBER]:
        result['reason'] = 'changed lines are not exactly [%d]' % LINE_NUMBER
        return result
    before, after = a[LINE_NUMBER - 1], b[LINE_NUMBER - 1]
    ending = before[len(before.rstrip(b'\r\n')):]
    if after[len(after.rstrip(b'\r\n')):] != ending:
        result['reason'] = 'line terminator changed'
        return result
    if before.rstrip(b'\r\n').decode() != BEFORE_LINE or after.rstrip(b'\r\n').decode() != AFTER_LINE:
        result['reason'] = 'line text is not the recorded change'
        return result
    result.update(ok=True, before_line=BEFORE_LINE, after_line=AFTER_LINE)
    return result


def check(name, passed, **details):
    return dict(name=name, passed=bool(passed), **details)


def preflight(original_dir, candidate_dir, fixtures_path, thresholds_path, plan_path):
    """Local gate; every check is reported, none raises."""
    original_dir, candidate_dir = Path(original_dir), Path(candidate_dir)
    checks = []
    original_cpp = original_dir / MANAGER_REL
    candidate_cpp = candidate_dir / MANAGER_REL
    original_sha = sha256_file(original_cpp) if original_cpp.is_file() else None
    candidate_sha = sha256_file(candidate_cpp) if candidate_cpp.is_file() else None
    original_ids = load_json(original_dir / 'source_sha256.json') if (original_dir / 'source_sha256.json').is_file() else None
    candidate_ids = load_json(candidate_dir / 'source_sha256.json') if (candidate_dir / 'source_sha256.json').is_file() else None
    checks.append(check('original_manager_is_recorded_base', original_sha == BASE_SHA256, sha256=original_sha))
    checks.append(check('original_manager_in_source_manifest',
                        original_ids is not None and original_ids.get(MANAGER_REL) == original_sha))
    install = original_dir / 'install_identity.json'
    install_files = load_json(install).get('installed_files', {}) if install.is_file() else {}
    checks.append(check('original_install_identity_present', len(install_files) > 0, files=len(install_files)))
    build = original_dir / 'build_result.json'
    checks.append(check('original_build_passed', build.is_file() and load_json(build).get('passed') is True))
    checks.append(check('candidate_manager_present', candidate_sha is not None, sha256=candidate_sha))
    checks.append(check('candidate_manager_in_source_manifest',
                        candidate_ids is not None and candidate_sha is not None
                        and candidate_ids.get(MANAGER_REL) == candidate_sha))
    fix = candidate_dir / 'terminal_accel_fix_manifest.json'
    fix_doc = load_json(fix) if fix.is_file() else {}
    checks.append(check('candidate_fix_manifest_matches', fix_doc.get('after_sha256') == candidate_sha is not None
                        and fix_doc.get('before_sha256') == BASE_SHA256, manifest=rel(fix)))
    build = candidate_dir / 'build_result.json'
    checks.append(check('candidate_build_passed', build.is_file() and load_json(build).get('passed') is True))
    diff = one_line_diff(original_cpp.read_bytes(), candidate_cpp.read_bytes()) \
        if original_sha and candidate_sha else {'ok': False, 'reason': 'manager source missing'}
    checks.append(check('manager_one_line_diff', diff['ok'], diff=diff))
    same_rest = (original_ids is not None and candidate_ids is not None
                 and set(original_ids) == set(candidate_ids)
                 and [k for k in original_ids if original_ids[k] != candidate_ids[k]] == [MANAGER_REL])
    checks.append(check('source_manifests_differ_only_in_manager', same_rest))
    checks.append(check('planner_yaml_hash', sha256_file(PLANNER_YAML) == PLANNER_YAML_SHA256))
    try:
        analyze_suite.load_thresholds(thresholds_path, plan_path)
        frozen = True
    except (analyze_suite.AnalysisRefused, OSError) as error:
        frozen = False
        checks.append(check('thresholds_error', False, error=str(error)))
    checks.append(check('thresholds_frozen', frozen, sha256=sha256_file(thresholds_path) if Path(thresholds_path).is_file() else None))
    fixture_ok, fixture_info = fixture_summary(fixtures_path)
    checks.append(check('fixtures_valid', fixture_ok, **fixture_info))
    return {'passed': all(c['passed'] for c in checks), 'checks': checks, 'diff': diff,
            'original_sha256': original_sha, 'candidate_sha256': candidate_sha}


def fixture_summary(fixtures_path):
    fixtures_path = Path(fixtures_path)
    if not fixtures_path.is_file():
        return False, {'error': 'missing fixtures file ' + str(fixtures_path)}
    doc = load_json(fixtures_path)
    runs = doc.get('runs', [])
    problems = []
    if doc.get('schema') != 'scan_fix_suite_cases_v1' or not runs:
        problems.append('unexpected schema or no runs')
    labels = [r.get('label') for r in runs]
    if len(set(labels)) != len(labels) or not all(isinstance(x, str) and LABEL.match(x) for x in labels):
        problems.append('run labels are not unique safe names')
    boxes = sorted({r['occupied_boxes'] for r in runs if r.get('occupied_boxes')})
    for box in boxes:
        path = fixtures_path.parent / box
        recorded = doc.get('boxes', {}).get(box, {}).get('sha256')
        if not path.is_file() or sha256_file(path) != recorded:
            problems.append('box file missing or hash mismatch: ' + box)
    if doc.get('planner_params', {}).get('sha256') != PLANNER_YAML_SHA256:
        problems.append('fixtures were generated from another planner.yaml')
    calls = sum(1 + len(r.get('follow_up_offsets_s') or []) for r in runs)
    info = {'path': rel(fixtures_path), 'sha256': sha256_file(fixtures_path), 'runs_per_build': len(runs),
            'process_runs_total': 2 * len(runs), 'planned_steps_per_build': calls, 'box_files': boxes,
            'problems': problems}
    return not problems, info


def remote_paths(run_id, host, original_name, candidate_name):
    # build_scan.py syncs builds/<name>/src to REMOTE_P2B/builds/<name>; the same names are used here.
    for name in (original_name, candidate_name):
        if not BUILD_NAME.match(name):
            raise Refused('unexpected SCAN build directory name: ' + name)
    return {'host': host, 'remote_run': REMOTE_RUNS + '/' + run_id,
            'remote_original_build': REMOTE_P2B + '/builds/' + original_name,
            'remote_candidate_build': REMOTE_P2B + '/builds/' + candidate_name}


def plan_commands(run_id, local_run, host, replay_ceiling_s, original_name, candidate_name):
    paths = remote_paths(run_id, host, original_name, candidate_name)
    remote_run = paths['remote_run']
    total = 2 * BUILD_CEILING_S + 2 * replay_ceiling_s + 120
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', host]
    commands = {
        'remote_run': remote_run,
        'remote_original_build': paths['remote_original_build'],
        'remote_candidate_build': paths['remote_candidate_build'],
        'remote_total_ceiling_s': total,
        'local_run_timeout_s': total + 120,
        'mkdir': ssh + ["python3 - <<'PY'\nfrom pathlib import Path\np=Path(%r)\nassert not p.exists(), p\n"
                        "p.mkdir(parents=True)\nPY" % remote_run],
        'sync': ['rsync', '-a', '--files-from=' + str(Path(local_run) / 'sync_files.txt'),
                 str(local_run) + '/', '%s:%s/' % (host, remote_run)],
        'run': ssh + [shlex.join(['timeout', '--kill-after=30', str(total), 'python3', remote_run + '/suite_remote.py'])],
        'collect': ['rsync', '-a', '%s:%s/artifacts/' % (host, remote_run), str(Path(local_run) / 'returned_artifacts') + '/'],
        'remote_container_commands': {
            variant: {stage: suite_remote.podman_command(run_id, remote_run, paths['remote_original_build'],
                                                         IMAGE, variant, stage)
                      for stage in ('build', 'replay')}
            for variant in suite_remote.VARIANTS},
    }
    return commands


def package_files(local_run):
    files = {}
    for path in sorted(Path(local_run).rglob('*')):
        relative = path.relative_to(local_run).as_posix()
        if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        if relative in ('package_manifest.json', 'sync_files.txt', 'commands.json', 'preflight.json'):
            continue
        files[relative] = sha256_file(path)
    return files


def prepare(args, gate, commands, fixtures_info):
    local_run = Path(args.local_runs_root) / args.run_id
    if local_run.exists():
        raise FileExistsError(str(local_run))
    local_run.mkdir(parents=True)
    shutil.copy2(HERE / 'suite_remote.py', local_run / 'suite_remote.py')
    shutil.copy2(HERE / 'container_suite.py', local_run / 'container_suite.py')
    shutil.copytree(PACKAGE_DIR, local_run / 'native_suite',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    inputs = local_run / 'inputs'
    (inputs / 'fixtures').mkdir(parents=True)
    shutil.copy2(PLANNER_YAML, inputs / 'planner.yaml')
    fixtures_path = Path(args.fixtures)
    shutil.copy2(fixtures_path, inputs / 'fixtures/suite_cases.json')
    for box in fixtures_info['box_files']:
        target = inputs / 'fixtures' / box
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fixtures_path.parent / box, target)
    original_dir, candidate_dir = Path(args.original_build_dir), Path(args.candidate_build_dir)
    shutil.copy2(original_dir / 'source_sha256.json', inputs / 'scan_source_identity.json')
    shutil.copy2(original_dir / 'install_identity.json', inputs / 'scan_install_identity.json')
    shutil.copy2(candidate_dir / 'source_sha256.json', inputs / 'candidate_source_identity.json')
    managers = local_run / 'managers'
    for variant, source in (('original', original_dir), ('candidate', candidate_dir)):
        (managers / variant).mkdir(parents=True)
        shutil.copy2(source / MANAGER_REL, managers / variant / 'planner_manager.cpp')
    write_json(managers / 'manager_identity.json', {
        'original': {'source': rel(original_dir / MANAGER_REL), 'sha256': gate['original_sha256'],
                     'build': original_dir.name},
        'candidate': {'source': rel(candidate_dir / MANAGER_REL), 'sha256': gate['candidate_sha256'],
                      'build': candidate_dir.name,
                      'fix_manifest': rel(candidate_dir / 'terminal_accel_fix_manifest.json'),
                      'fix_manifest_sha256': sha256_file(candidate_dir / 'terminal_accel_fix_manifest.json')},
        'one_line_diff': gate['diff'],
        'linking': 'both variants compile against scan_03 headers and scan_03 installed static libraries',
    })
    write_json(local_run / 'request.json', {
        'schema': 'scan_fix_native_suite_request_v1',
        'run_id': args.run_id,
        'prepared_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'scope': SCOPE,
        'image_id': IMAGE,
        'host': args.host,
        'remote_run': commands['remote_run'],
        'remote_original_build': commands['remote_original_build'],
        'remote_candidate_build': commands['remote_candidate_build'],
        'local_original_build': rel(original_dir),
        'local_candidate_build': rel(candidate_dir),
        'build_ceiling_s': BUILD_CEILING_S,
        'replay_ceiling_s': args.replay_ceiling_s,
        'case_ceiling_s': CASE_CEILING_S,
        'remote_total_ceiling_s': commands['remote_total_ceiling_s'],
        'fixtures': {k: fixtures_info[k] for k in ('path', 'sha256', 'runs_per_build', 'process_runs_total',
                                                     'planned_steps_per_build')},
        'thresholds': {'path': rel(args.thresholds), 'sha256': sha256_file(args.thresholds)},
        'source_of_truth': str(HERE),
        'default_execute': False,
        'execute_requires': ['--execute', '--lead-authorized-execute'],
        'claim_boundary': CLAIM,
    })
    files = package_files(local_run)
    write_json(local_run / 'package_manifest.json', files)
    (local_run / 'sync_files.txt').write_text('\n'.join(sorted(files) + ['package_manifest.json']) + '\n')
    write_json(local_run / 'commands.json', commands)
    write_json(local_run / 'preflight.json', gate)
    return local_run


def load_prepared(local_run):
    """Reload an unexecuted package after checking files and regenerated commands."""
    local_run = Path(local_run)
    if (local_run / 'return_verdict.json').exists():
        raise Refused('run package already executed: %s' % local_run)
    manifest = load_json(local_run / 'package_manifest.json')
    current = {p: h for p, h in package_files(local_run).items() if not p.startswith('host_logs/')}
    if current != manifest:
        differing = sorted(set(current) ^ set(manifest)) + sorted(
            p for p in set(current) & set(manifest) if current[p] != manifest[p])
        raise Refused('prepared package differs from its manifest: %s' % differing[:5])
    request = load_json(local_run / 'request.json')
    stored = load_json(local_run / 'commands.json')
    regenerated = plan_commands(request['run_id'], local_run, request['host'], request['replay_ceiling_s'],
                                Path(request['local_original_build']).name, Path(request['local_candidate_build']).name)
    if json.loads(json.dumps(regenerated)) != stored:
        raise Refused('stored commands.json differs from the commands regenerated from request.json')
    return stored


def run_command(label, command, log_path, timeout):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    log_path.write_text(result.stdout)
    if result.returncode:
        raise RuntimeError('%s failed with exit %d: %s' % (label, result.returncode, result.stdout[-2000:]))


def verify_returned(local_run):
    returned = Path(local_run) / 'returned_artifacts'
    expected = load_json(returned / 'artifact_hashes.json')
    actual = {p.relative_to(returned).as_posix(): sha256_file(p) for p in sorted(returned.rglob('*'))
              if p.is_file() and p.name != 'artifact_hashes.json'}
    result = load_json(returned / 'result.json') if (returned / 'result.json').is_file() else {}
    return {'returned_hashes_match': expected == actual, 'expected_count': len(expected), 'actual_count': len(actual),
            'remote_source_gate_passed': bool(result.get('source_gate', {}).get('all_match')),
            'remote_replay_completed': bool(result.get('replay_completed')),
            'owned_containers_absent': bool(result.get('owned_containers_absent')),
            'remote_error': result.get('error')}


def execute(args, local_run, commands):
    if not (args.execute and args.lead_authorized_execute):
        raise Refused('execution requires --execute --lead-authorized-execute')
    logs = Path(local_run) / 'host_logs'
    verdict = {'remote_worker_started': False}
    error = None
    try:
        run_command('mkdir', commands['mkdir'], logs / '00_mkdir.log', 60)
        run_command('sync', commands['sync'], logs / '01_sync.log', 600)
        verdict['remote_worker_started'] = True
        run_command('run', commands['run'], logs / '02_remote_worker.log', commands['local_run_timeout_s'])
    except Exception as exc:  # noqa: BLE001 - keep the failure, still collect what exists
        error = exc
        verdict['run_error'] = str(exc)
    finally:
        if verdict['remote_worker_started']:
            try:
                run_command('collect', commands['collect'], logs / '03_collect.log', 600)
                verdict.update(verify_returned(local_run))
            except Exception as exc:  # noqa: BLE001
                verdict['collect_error'] = str(exc)
                error = error or exc
        write_json(Path(local_run) / 'return_verdict.json', verdict)
    if error is not None:
        raise error
    if not verdict.get('returned_hashes_match'):
        raise Refused('returned artifact hashes do not match')
    return verdict


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--run-id', required=True, help='new run id, e.g. native_suite_20260917T010203Z')
    parser.add_argument('--fixtures', type=Path, default=FIXTURES)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--lead-authorized-execute', action='store_true')
    parser.add_argument('--host', default=HOST)
    parser.add_argument('--replay-ceiling-s', type=int, default=DEFAULT_REPLAY_CEILING_S)
    parser.add_argument('--original-build-dir', type=Path, default=BUILDS / 'scan_03')
    parser.add_argument('--candidate-build-dir', type=Path, default=BUILDS / 'scan_04')
    parser.add_argument('--thresholds', type=Path, default=analyze_suite.THRESHOLDS)
    parser.add_argument('--plan', type=Path, default=analyze_suite.PLAN)
    parser.add_argument('--local-runs-root', type=Path, default=HERE / 'runs')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not RUN_ID.match(args.run_id):
        raise Refused('invalid run id: ' + args.run_id)
    if args.dry_run and args.execute:
        raise Refused('--dry-run and --execute are exclusive')
    if not 60 <= args.replay_ceiling_s <= 3600:
        raise Refused('--replay-ceiling-s must be within 60..3600')
    local_run = Path(args.local_runs_root) / args.run_id
    gate = preflight(args.original_build_dir, args.candidate_build_dir, args.fixtures, args.thresholds, args.plan)
    fixtures_info = next(c for c in gate['checks'] if c['name'] == 'fixtures_valid')
    commands = plan_commands(args.run_id, local_run, args.host, args.replay_ceiling_s,
                             Path(args.original_build_dir).name, Path(args.candidate_build_dir).name)
    summary = {
        'run_id': args.run_id, 'local_run': str(local_run), 'remote_run': commands['remote_run'],
        'fixtures': fixtures_info.get('path'), 'fixtures_sha256': fixtures_info.get('sha256'),
        'runs_per_build': fixtures_info.get('runs_per_build'),
        'process_runs_total': fixtures_info.get('process_runs_total'),
        'planned_steps_per_build': fixtures_info.get('planned_steps_per_build'),
        'preflight_passed': gate['passed'],
        'failed_checks': [c['name'] for c in gate['checks'] if not c['passed']],
        'ceilings_s': {'build_each': BUILD_CEILING_S, 'replay_each': args.replay_ceiling_s,
                       'case_each': CASE_CEILING_S, 'remote_total': commands['remote_total_ceiling_s']},
        'execute': bool(args.execute),
    }
    if args.dry_run:
        print(json.dumps(dict(summary, mode='dry_run', commands=commands), indent=2))
        return 0
    if args.execute and not args.lead_authorized_execute:
        raise Refused('execution requires --execute --lead-authorized-execute')
    if local_run.exists():
        if not args.execute:
            raise Refused('run package already exists: %s' % local_run)
        commands = load_prepared(local_run)
    else:
        if not gate['passed']:
            raise Refused('preflight failed: %s' % summary['failed_checks'])
        local_run = prepare(args, gate, commands, fixtures_info)
    if args.execute:
        summary['verdict'] = execute(args, local_run, commands)
    print(json.dumps(dict(summary, mode='execute' if args.execute else 'prepared'), indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Refused as error:
        print('suite_worker: refused: ' + str(error), file=sys.stderr)
        raise SystemExit(2)

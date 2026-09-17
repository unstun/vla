#!/usr/bin/env python3
"""Capture a remote SCAN build's installed-file identity over SSH.

Writes builds/<name>/install_identity.json in the same form as scan_03's
(installed_files, source_file_count, source_matches, remote_workspace,
image_id), plus install_identity_capture.log and .json. The remote hashing code
is the Isaac launcher's scan_tree_hashes/compare_hash_maps source, embedded
verbatim, so capture and launch gate apply one rule. --dry-run prints the
remote command and contacts nothing. --compare-existing re-hashes a build that
already has an identity and prints the comparison without writing to it.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
LAUNCHER = HERE.parent / 'isaac_runner/run_two_goal_pilot.py'
HOST = 'gpu5070ti'
# Same remote layout and SSH options as build_scan.py.
REMOTE_BUILDS = '/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', HOST]
RECORDED_BUILDS = {'scan_01', 'scan_02', 'scan_03'}
OUTPUT_NAMES = ('install_identity.json', 'install_identity_capture.log', 'install_identity_capture.json')


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_launcher():
    spec = importlib.util.spec_from_file_location('run_two_goal_pilot_for_identity', str(LAUNCHER))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def remote_script(launcher, remote_workspace, expected_source):
    return (
        'import hashlib\nimport json\nfrom pathlib import Path\n\n\n'
        + launcher.scan_gate_source()
        + '\n\n\nroot = Path(%r)\n' % remote_workspace
        + 'expected_source = json.loads(%r)\n' % json.dumps(expected_source, sort_keys=True)
        + 'source, source_excluded = scan_tree_hashes(root, "src")\n'
        + 'installed, install_excluded = scan_tree_hashes(root, "install")\n'
        + 'print(json.dumps({"workspace": str(root), "install_dir_exists": (root / "install").is_dir(), '
        + '"source_comparison": compare_hash_maps(expected_source, source), "source_excluded": source_excluded, '
        + '"installed_files": installed, "install_excluded": install_excluded}, sort_keys=True))\n'
    )


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


def plan(build_name, compare_existing=False):
    if not build_name.replace('_', '').isalnum():
        raise ValueError('Invalid build name')
    base = HERE / 'builds' / build_name
    remote = REMOTE_BUILDS + build_name
    build_result = read_json(base / 'build_result.json') or {}
    expected_source = read_json(base / 'source_sha256.json') or {}
    preconditions = {
        'build_passed': build_result.get('passed') is True,
        'build_remote_workspace_matches': build_result.get('remote_workspace') == remote,
        'source_manifest_present': bool(expected_source),
    }
    if compare_existing:
        preconditions['install_identity_present'] = (base / 'install_identity.json').is_file()
    else:
        preconditions['not_a_recorded_build'] = build_name not in RECORDED_BUILDS
        preconditions['outputs_absent'] = not any((base / name).exists() for name in OUTPUT_NAMES)
    launcher = load_launcher()
    script = remote_script(launcher, remote, expected_source)
    return {
        'build_name': build_name,
        'base': base,
        'remote_workspace': remote,
        'build_result': build_result,
        'expected_source': expected_source,
        'preconditions': preconditions,
        'command': SSH + ['python3 -'],
        'script': script,
        'launcher_sha256': sha256_bytes(LAUNCHER.read_bytes()),
    }


def run_remote(job, runner):
    started = datetime.now(timezone.utc).isoformat()
    proc = runner(job['command'], input=job['script'], capture_output=True, text=True, timeout=300)
    payload = None
    if proc.returncode == 0 and proc.stdout.strip():
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    return proc, payload, started


def capture(job, runner=subprocess.run):
    if not all(job['preconditions'].values()):
        raise RuntimeError('capture preconditions failed: ' + json.dumps(job['preconditions'], sort_keys=True))
    base = job['base']
    proc, payload, started = run_remote(job, runner)
    (base / 'install_identity_capture.log').write_text(proc.stdout + proc.stderr, encoding='utf-8')
    installed = (payload or {}).get('installed_files') or {}
    source_matches = bool(payload) and payload['source_comparison']['match'] is True
    ok = proc.returncode == 0 and source_matches and bool(installed)
    record = {
        'schema_version': 1,
        'build_name': job['build_name'],
        'remote_workspace': job['remote_workspace'],
        'command': job['command'],
        'remote_script_sha256': sha256_bytes(job['script'].encode('utf-8')),
        'capture_script_sha256': sha256_bytes(Path(__file__).resolve().read_bytes()),
        'launcher_sha256': job['launcher_sha256'],
        'started_utc': started,
        'finished_utc': datetime.now(timezone.utc).isoformat(),
        'exit_code': proc.returncode,
        'source_comparison': (payload or {}).get('source_comparison'),
        'source_excluded': (payload or {}).get('source_excluded'),
        'install_excluded': (payload or {}).get('install_excluded'),
        'installed_file_count': len(installed),
        'wrote_install_identity': False,
    }
    if ok:
        identity = {
            'installed_files': dict(sorted(installed.items())),
            'source_file_count': len(job['expected_source']),
            'source_matches': True,
            'remote_workspace': job['remote_workspace'],
            'image_id': job['build_result'].get('image_id'),
        }
        text = json.dumps(identity, indent=2) + '\n'
        (base / 'install_identity.json').write_text(text, encoding='utf-8')
        record.update(wrote_install_identity=True, install_identity_sha256=sha256_bytes(text.encode('utf-8')))
    (base / 'install_identity_capture.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    if not ok:
        raise RuntimeError('install identity not written; see install_identity_capture.json')
    return record


def compare_existing(job, runner=subprocess.run):
    if not all(job['preconditions'].values()):
        raise RuntimeError('compare preconditions failed: ' + json.dumps(job['preconditions'], sort_keys=True))
    launcher = load_launcher()
    existing = read_json(job['base'] / 'install_identity.json')
    proc, payload, started = run_remote(job, runner)
    result = {'build_name': job['build_name'], 'started_utc': started, 'exit_code': proc.returncode,
              'stderr_tail': proc.stderr[-2000:], 'passed': False}
    if payload is not None:
        result.update(
            source_comparison=payload['source_comparison'],
            source_excluded=payload['source_excluded'],
            install_comparison=launcher.compare_hash_maps(existing['installed_files'], payload['installed_files']),
            install_excluded=payload['install_excluded'],
        )
        result['passed'] = result['source_comparison']['match'] and result['install_comparison']['match']
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_name')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='Print the remote command; contact nothing.')
    mode.add_argument('--compare-existing', action='store_true',
                      help='Re-hash a build with an existing identity; print the comparison, write nothing.')
    args = parser.parse_args(argv)
    job = plan(args.build_name, compare_existing=args.compare_existing)
    if args.dry_run:
        print(json.dumps({
            'build_name': job['build_name'],
            'remote_workspace': job['remote_workspace'],
            'command': job['command'],
            'stdin_script': job['script'],
            'preconditions': job['preconditions'],
            'would_write': [str(job['base'] / name) for name in OUTPUT_NAMES],
        }, indent=2))
        return 0
    if args.compare_existing:
        result = compare_existing(job)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result['passed'] else 1
    record = capture(job)
    print(json.dumps({k: record[k] for k in ('build_name', 'installed_file_count', 'install_identity_sha256')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

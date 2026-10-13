"""Run one authorized, bounded v58 Building trial; retain bulk remotely."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
PYTHON = '/home/sun/vla_exec/envs/newton_worker/bin/python'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    assert str(ROOT) == '/home/sun/vla_exec/vla'
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', type=int, default=1)
    args = parser.parse_args()
    run = f'v58_realtime_trial{args.attempt:02d}'
    output = HERE / f'trials/attempt{args.attempt:02d}'
    output.mkdir(parents=True)
    os.environ['PATH'] = '/home/sun/vla_exec/bin:' + os.environ['PATH']
    checks = {
        'containers': ['docker', 'ps', '--format', '{{.Names}}'],
        'ports': ['ss', '-ltnH', '( sport >= :46200 and sport <= :46203 )'],
        'gpu_processes': ['nvidia-smi', '--query-compute-apps=pid,process_name', '--format=csv,noheader']}
    preflight = {}
    for label, command in checks.items():
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        preflight[label] = dict(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
    (output / 'preflight.json').write_text(json.dumps(preflight, indent=2) + '\n')
    assert all(row['exit_code'] == 0 and not row['stdout'].strip() for row in preflight.values())
    command = [PYTHON, str(BASE / 'scripts/run_managed.py'), '--run-id', run, '--deadline', '360', '--',
        PYTHON, str(HERE / 'run_local_episode.py'), '--backend-executor', 'single',
        '--applied-transport', 'zmq', '--geometry-obstacles', '--scene', 'building_full',
        '--building-route', 'historical_full', '--goal-wall-budget', '180',
        '--startup-mode', 'factory_pd', '--stance-hold', '--integration-version', 'v58',
        '--real-time-factor', '1', '--recording-sim-seconds', '90']
    request = dict(command=command, supervisor_deadline_s=360,
        local_source_of_truth='/Users/sun/tongbu/study/phdproject/vla',
        source_sha256=sha(Path(__file__)), integration_manifest_sha256=sha(HERE / 'manifest.json'),
        remote_artifact_root=str(BASE / 'runs' / run),
        local_return='Compact trial/analysis results, provenance, plots, and an optional review MP4; no raw capture or build trees',
        expected_local_return_bytes='Under 5 MiB for compact evidence; one review video under 128 MiB',
        claim_boundary='Same configuration, independent physical trajectory; no 30 Hz or continuity claim until measured')
    (output / 'request.json').write_text(json.dumps(request, indent=2) + '\n')
    started = time.monotonic()
    code, error = 127, None
    try:
        with (output / 'execution.log').open('w') as log:
            code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=390).returncode
    except (OSError, subprocess.TimeoutExpired) as exception:
        error = repr(exception)
    name = 'vla-newton-' + run.replace('_', '-')
    subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=20)
    listed = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True, timeout=20)
    evidence = dict(exit_code=code, error=error, wall_s=time.monotonic() - started,
                    owned_container_not_running=listed.returncode == 0 and name not in listed.stdout.splitlines())
    (output / 'result.json').write_text(json.dumps(evidence, indent=2) + '\n')
    paths = [p for directory in (output, BASE / 'runs' / run)
             for p in directory.rglob('*') if p.is_file()]
    records = {str(p.relative_to(ROOT)): dict(sha256=sha(p), bytes=p.stat().st_size) for p in paths}
    (output / 'remote_artifact_manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(evidence, indent=2), flush=True)
    raise SystemExit(code)


if __name__ == '__main__':
    main()

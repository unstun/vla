"""Bounded, task-owned native offline phases. No physical episode entry exists."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'AGENTS.md').is_file())
VERSIONS = HERE.parent
BINDING = json.loads((HERE / 'binding.json').read_text())
PREFIX = Path(BINDING['remote_root'])
WORK = PREFIX / BINDING['native_workspace']


def command(name, output, shell, cpu_limit=4, domain=219):
    image = BINDING['native_image']
    assert image and image.startswith('sha256:'), 'Bind the actual rebuilt image first'
    detail = json.loads(subprocess.check_output(['/usr/bin/docker', 'image', 'inspect', image]))[0]
    assert detail['Architecture'] == 'amd64'
    for folder in ('ros_logs', 'ros_home'):
        (output / folder).mkdir()
    args = ['/usr/bin/docker', 'run', '--rm', '--pull=never', '--name', name,
        '--platform=linux/amd64', '--user', f'{os.getuid()}:{os.getgid()}',
        '--memory=6g', f'--cpus={cpu_limit}', '--cpu-shares=128', '--network=host',
        '--add-host', 'host.docker.internal:127.0.0.1',
        '-e', f'ROS_DOMAIN_ID={domain}', '-e', 'ROS_LOCALHOST_ONLY=1',
        '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'OPENBLAS_NUM_THREADS=1', '-e', 'OMP_NUM_THREADS=1',
        '-e', f'ROS_LOG_DIR={output}/ros_logs', '-e', f'ROS_HOME={output}/ros_home',
        '-v', f'{PREFIX}:/task:ro', '-v', f'{ROOT}:{ROOT}:ro', '-v', f'{ROOT}:/repo:ro',
        '-v', f'{PREFIX}:{PREFIX}:ro', '-v', f'{output}:{output}:rw',
        '-v', f'{WORK}:/work:rw', '-v', f'{WORK}/src:/work/src:ro',
        '-v', f'{VERSIONS}/v232:/source:ro', '-v', f'{HERE}:/migration:ro',
        '-v', f'{VERSIONS}/v224:/task/source_v224:ro',
        '--entrypoint', '/bin/bash', image, '-c', 'set -eo pipefail; ' + shell]
    return args


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'global_terrain', 'tests', 'atlas', 'probes', 'receipt', 'profiles'])
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    assert args.attempt.isdecimal()
    from source_gate import verify_source
    checked = verify_source(WORK)
    output = PREFIX / 'evidence' / (args.phase + args.attempt)
    output.mkdir(exist_ok=False)
    setup = 'source /opt/ros/foxy/setup.bash; '
    installed = setup + 'source /work/install/setup.bash; '
    if args.phase == 'build':
        shell = 'exec nice -n 10 bash /migration/native_build.sh'
    elif args.phase == 'global_terrain':
        shell = setup + ('exec nice -n 10 python3 ' + shlex.quote(str(HERE / 'rebuild_fixtures.py')) +
                         ' global_terrain --prefix /task --work /work')
        # Fixture producers need writable task-owned generated output directories.
        (PREFIX / 'global_coverage_v135_foxy').mkdir(exist_ok=False)
        # Producer refuses an existing output. Mount its writable parent /task below.
        (PREFIX / 'global_coverage_v135_foxy').rmdir()
    elif args.phase == 'tests':
        (WORK / 'v234_private_test_copy').write_text('Private v234 reconstruction; frozen source is read-only.\n')
        shell = 'exec nice -n 10 bash /migration/native_tests.sh v234_attempt' + args.attempt.zfill(2)
    elif args.phase == 'atlas':
        shell = installed + 'nice -n 10 bash /migration/rebuild_atlas.sh; python3 /migration/prepare_profiles.py'
    elif args.phase == 'receipt':
        shell = installed + 'exec python3 ' + shlex.quote(str(HERE / 'collect_native.py'))
    elif args.phase == 'profiles':
        shell = installed + 'exec python3 /migration/prepare_profiles.py --component-only'
    else:
        shell = installed + ('export REPLAY_INPUT=/work/fixtures/building; '
            'export ENVIRONMENT_INPUT=/work/fixtures/building/environment225.env ENVIRONMENT_FNV=10040917858432847476; '
            'export PCT_INPUT=/work/fixtures/building/route.pct ROUTE_ENDPOINTS=/work/fixtures/route_endpoints.txt '
            'BENCH_POSES=/work/fixtures/bench_poses.txt; '
            'cmake -S /source/tools -B /work/probe_build -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions -DCMAKE_BUILD_TYPE=Release; '
            'cmake --build /work/probe_build --target field_probe admission_probe -j2; '
            f'export PROBE_OUTPUT={shlex.quote(str(output))}/field; '
            '/work/probe_build/field_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level error; '
            f'export PROBE_OUTPUT={shlex.quote(str(output))}/admission; '
            '/work/probe_build/admission_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level error')
    argv = command('v234-' + args.phase + '-' + args.attempt, output, shell,
                   cpu_limit=2 if args.phase in ('tests', 'probes') else 4,
                   domain=218 if args.phase == 'tests' else 219)
    if args.phase == 'global_terrain':
        index = argv.index(f'{PREFIX}:/task:ro')
        argv[index] = f'{PREFIX}:/task:rw'
    started = time.time_ns()
    request = dict(command=argv, started_ns=started, phase=args.phase, image=BINDING['native_image'], source_gate=checked,
                   source='exact v232 317-file tree', physics_steps=0)
    (output / 'request.json').write_text(json.dumps(request, indent=2) + '\n')
    with (output / 'execution.log').open('w') as log:
        result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    report = dict(returncode=result.returncode, finished_ns=time.time_ns(), started_ns=started, physics_steps=0)
    (output / 'execution.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    result.check_returncode()


if __name__ == '__main__':
    main()

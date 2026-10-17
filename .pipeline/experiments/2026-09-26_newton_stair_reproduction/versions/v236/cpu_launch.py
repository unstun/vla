"""Own4-CPU cgroup quota with flexible affinity and the unchanged host libraries."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
PREFIX = Path('/home/ubuntu/sun/vla_v234_20261017')
PYTHON = PREFIX / 'env/newton_worker/bin/python'
IMAGE = 'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('probe', 'preflight', 'route'))
    parser.add_argument('--attempt', default='04')
    args = parser.parse_args()
    assert args.attempt.isdecimal()
    suffix = args.phase + args.attempt
    name = 'v236-host-' + suffix
    output = PREFIX / 'evidence' / ('v236_host_' + suffix)
    spec = importlib.util.spec_from_file_location('v236_host_inventory', HERE.parent / 'v234/host_inventory.py')
    inventory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inventory)
    before = inventory.snapshot(PREFIX)
    socket_group = Path('/var/run/docker.sock').stat().st_gid
    command = ['/usr/bin/docker', 'run', '--rm', '--pull=never', '--name', name,
        '--cpus=4', '--cpu-shares=128', '--memory=6g', '--network=host',
        '--user', f'{os.getuid()}:{os.getgid()}', '--group-add', str(socket_group),
        '-v', f'{PREFIX}:{PREFIX}:rw', '-v', '/var/run/docker.sock:/var/run/docker.sock',
        '-v', '/usr/bin/docker:/usr/bin/docker:ro']
    # Reuse host CPU libraries at the same paths, instead of changing the
    # physics/policy wheel or libc environment when adding the cgroup wrapper.
    library_dirs = ('/lib', '/usr/lib', '/lib64', '/usr/lib64')
    for path in library_dirs:
        command.extend(['-v', path + ':' + path + ':ro'])
    loader = '/lib64/ld-linux-x86-64.so.2'
    for key, value in dict(PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1',
        OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='',
        V236_PRIVATE_CPU_WRAPPER='1',
        WARP_CACHE_PATH=str(PREFIX / 'trials/v235_linux_full_attempt01/runtime/warp-cache'),
        PATH=str(HERE.parent / 'v234/bin') + ':' + str(HERE.parent / 'v233/bin') + ':' + os.environ['PATH']).items():
        command.extend(['-e', key + '=' + value])
    command += ['--entrypoint', '/usr/bin/nice', IMAGE, '-n', '19', str(PYTHON)]
    if args.phase == 'probe':
        command += [str(HERE / 'probe_scans.py'), '--output',
            str(PREFIX / 'evidence' / ('v236_scan_probe' + args.attempt + '.json')),
            '--scans', '150', '--fixed', '--flexible']
    else:
        command += [str(HERE / 'launch.py')]
        if args.phase == 'preflight':
            command.append('--preflight-only')
    host_files = [Path('/usr/bin/docker'), Path(loader)]
    host_files += [Path('/lib/x86_64-linux-gnu') / n for n in ('libc.so.6', 'libm.so.6', 'libstdc++.so.6')]
    request = dict(command=command, before=before, cpu_quota=4, affinity_flexible=True,
        host_cpu_libraries_unchanged=True, host_files_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in host_files})
    with output.with_suffix('.request.json').open('x') as stream:
        json.dump(request, stream, indent=2)
    started = time.monotonic()
    result = None
    try:
        result = subprocess.run(command, timeout=1800)
    finally:
        subprocess.run(['/usr/bin/docker', 'rm', '-f', name], capture_output=True, timeout=30)
        report = dict(returncode=result.returncode if result else None, wall_s=time.monotonic()-started,
            after=inventory.snapshot(PREFIX), peer_mutations=[])
        output.with_suffix('.execution.json').write_text(json.dumps(report, indent=2)+'\n')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()

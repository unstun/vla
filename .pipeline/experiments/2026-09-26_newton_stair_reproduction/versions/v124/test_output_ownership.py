"""Exercise the real Docker tmpfs mount before starting any physics."""
from pathlib import Path
import json
import os
import subprocess
import time

TASK = Path('/data/sun/vla_mppi_20261009')
root = TASK/'checks'/f'ownership_{time.time_ns()}'
run = root/'runs'/'ownership'
external = run/'artifacts/external_episode'
external.mkdir(parents=True)
container = f'vla-mppi-ownership-{os.getpid()}'
image = json.loads((TASK/'results/baseline_receipt.json').read_text())['image_id']
created = False
try:
    subprocess.run(['docker', 'run', '-d', '--rm', '--name', container, '--network', 'none',
                    '-v', f'{root}:{root}:rw', '--tmpfs', f'{external}:rw,size=8m',
                    '--entrypoint', '/bin/sh', image, '-c', 'exec sleep infinity'],
                   check=True, capture_output=True, timeout=30)
    created = True
    assert run.stat().st_uid == os.getuid()
    (run/'request.json').write_text('{"host_writer":true}\n')
    subprocess.run(['docker', 'exec', container, '/bin/sh', '-c',
                    'printf native > "$1/current_command.json"', 'sh', str(external)], check=True)
    data = subprocess.check_output(['docker', 'exec', container, 'cat', str(external/'current_command.json')])
    assert data == b'native'
    (run/'retention_result.json').write_text('{"host_writer":true}\n')
    result = {'passed': True, 'host_uid': os.getuid(), 'run_owner': run.stat().st_uid,
              'host_request_and_retention_writable': True, 'container_state_writable': True,
              'root': str(root), 'image_id': image, 'physics_advanced': False}
    (TASK/'results/output_ownership_test.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
finally:
    if created:
        subprocess.run(['docker', 'rm', '-f', container], capture_output=True, timeout=30)

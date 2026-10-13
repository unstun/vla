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
(root/'ros_logs').mkdir()
container = f'vla-mppi-ownership-{os.getpid()}'
image = json.loads((TASK/'results/baseline_receipt.json').read_text())['image_id']
created = False
try:
    subprocess.run(['docker', 'run', '-d', '--rm', '--name', container, '--network', 'none',
                    '--user', f'{os.getuid()}:{os.getgid()}', '-e', 'ROS_LOG_DIR='+str(root/'ros_logs'),
                    '-v', f'{root}:{root}:rw', '--tmpfs', f'{external}:rw,size=8m,uid={os.getuid()},gid={os.getgid()},mode=0700',
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
    here = Path(__file__).resolve().parent
    with (run/'active_writer.log').open('w') as writer:
        check = subprocess.run([str(here/'lsof'), '-nP', '-F', 'fan', '--', str(run/'active_writer.log')], capture_output=True, text=True)
        assert check.returncode == 0 and not check.stderr and 'aw' in check.stdout, (check.stdout, check.stderr)
    check = subprocess.run([str(here/'lsof'), '-nP', '-F', 'fan', '--', str(run/'active_writer.log')], capture_output=True, text=True)
    assert check.returncode == 1 and not check.stdout and not check.stderr, (check.stdout, check.stderr)
    native_script = root/'active_writer_test.py'
    native_path = run/'native_writer.log'
    native_script.write_text('import time\nwith open('+repr(str(native_path))+', "w") as f:\n print("READY", flush=True)\n time.sleep(3)\n')
    native = subprocess.Popen(['docker', 'exec', container, 'python3', str(native_script)], stdout=subprocess.PIPE, text=True)
    assert native.stdout.readline().strip() == 'READY'
    check = subprocess.run([str(here/'lsof'), '-nP', '-F', 'fan', '--', str(native_path)], capture_output=True, text=True)
    assert check.returncode == 0 and not check.stderr and 'aw' in check.stdout, (check.stdout, check.stderr)
    assert native.wait(timeout=5) == 0
    result = {'active_writer_detected': True, 'native_writer_detected': True, 'closed_writer_check_passed': True, 'passed': True, 'host_uid': os.getuid(), 'run_owner': run.stat().st_uid,
              'host_request_and_retention_writable': True, 'container_state_writable': True,
              'root': str(root), 'image_id': image, 'physics_advanced': False}
    (TASK/'results/recovery_v134/output_ownership_test.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
finally:
    if created:
        subprocess.run(['docker', 'rm', '-f', container], capture_output=True, timeout=30)

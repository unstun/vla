"""Verify closed bind-mounted state without an applied-state ACK or copyback."""
import hashlib
import json
from pathlib import Path
import subprocess

FILES = ('current_command.json', 'finish_request.json')


def validate_identity(values, request, run_id):
    current, finish = (values[name] for name in FILES)
    if current['run_id'] != run_id or finish['run_id'] != run_id:
        raise ValueError('Foreign shared-state run')
    if (current['run_epoch_ns'] != request['run_epoch_ns'] or
            finish['observed_run_epoch_ns'] != request['run_epoch_ns']):
        raise ValueError('Foreign shared-state epoch')
    if request['applied_transport'] != 'shared':
        raise ValueError('Expected shared applied-state transport')
    if finish['backend_terminal_status'] not in ('FINISHED', 'FAILED'):
        raise ValueError('Missing terminal status')


def verify_shared_state(container, out):
    """Compare host and container bytes after the producer and graph stop."""
    out = Path(out)
    external = out / 'artifacts/external_episode'
    report = {'verified': False, 'method': 'shared_bind_mount_after_graph_stop',
              'copyback_required': False, 'per_step_ack_required': False}
    try:
        values, files = {}, {}
        for name in FILES:
            data = (external / name).read_bytes()
            values[name] = json.loads(data)
            files[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        validate_identity(values, json.loads((out / 'episode_request.json').read_text()), out.name)
        code = '''import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1])
files={}
for name in sys.argv[2:]:
 data=(root/name).read_bytes()
 files[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
print(json.dumps(files))
'''
        remote = json.loads(subprocess.check_output(
            ['docker', 'exec', container, 'python3', '-c', code, str(external), *FILES],
            text=True, timeout=15))
        report.update(host_files=files, container_files=remote,
                      terminal_status=values['finish_request.json']['backend_terminal_status'])
        if files != remote:
            raise ValueError('Host/container shared-state bytes differ')
        report['verified'] = True
    except Exception as error:
        report['error'] = repr(error)
    (out / 'shared_state.json').write_text(json.dumps(report, indent=2) + '\n')
    return report['verified']


def verify_capture(capture):
    """Bind the closed-state witness to the actual retained capture bytes."""
    report = capture.json('shared_state.json')
    assert report['verified'] and report['method'] == 'shared_bind_mount_after_graph_stop'
    assert report['copyback_required'] is False and report['per_step_ack_required'] is False
    assert report['host_files'] == report['container_files']
    values = {}
    for name in FILES:
        data = capture.read('artifacts/external_episode/' + name).encode()
        assert report['host_files'][name] == {
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        values[name] = json.loads(data)
    validate_identity(values, capture.json('episode_request.json'), capture.root.name)
    return True

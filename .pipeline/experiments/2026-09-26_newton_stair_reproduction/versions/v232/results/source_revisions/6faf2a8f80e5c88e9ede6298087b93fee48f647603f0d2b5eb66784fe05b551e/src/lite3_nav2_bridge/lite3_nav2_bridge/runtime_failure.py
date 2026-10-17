"""Run-bound critical-process evidence and first-terminal finish publication."""
import json
import os
from pathlib import Path
import tempfile
import time


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def matches(record, run_id, epoch):
    return (isinstance(record, dict) and record.get('run_id') == run_id
            and record.get('run_epoch_ns') == epoch)


def valid_failure(record, run_id, epoch):
    return (matches(record, run_id, epoch)
            and isinstance(record.get('component'), str) and bool(record['component'])
            and record.get('cause') in ('native_process_exit', 'native_node_unresponsive')
            and (type(record.get('exit_code')) is int
                 or (record['cause'] == 'native_node_unresponsive' and record.get('exit_code') is None)))


def write_once(path, payload):
    """Publish complete bytes atomically; retain the first terminal/failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(payload, stream, allow_nan=False)
        stream.write('\n')
    try:
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
    finally:
        temporary.unlink()
    return read_json(path)


def process_failure(path, run_id, epoch, component, exit_code,
                    cause='native_process_exit'):
    payload = dict(run_id=run_id, run_epoch_ns=epoch, component=component,
                   exit_code=exit_code, cause=cause, monotonic_ns=time.monotonic_ns())
    if not valid_failure(payload, run_id, epoch):
        raise ValueError('Invalid native failure identity')
    return write_once(path, payload)


def critical_exit_handler(path, run_id, epoch, component):
    def exited(event, context):
        if not context.is_shutdown:
            process_failure(path, run_id, epoch, component, event.returncode)
        return []
    return exited


def finish_failed(root, request, failure, state=None):
    root = Path(root)
    run_id, epoch = root.name, request['run_epoch_ns']
    if not valid_failure(failure, run_id, epoch):
        return None
    if not matches(state, run_id, epoch):
        state = read_json(root / 'backend_latest.json')
    owner = state.get('service', {}).get('current_owner') if matches(state, run_id, epoch) else None
    if owner:
        request_id = owner['request_id']
    elif matches(state, run_id, epoch) and state.get('terminal_results'):
        request_id = state['terminal_results'][-1]['request_id']
    else:
        request_id = run_id + '-native-failure'
    note = '%s:%s:exit_code=%s' % (failure['cause'], failure['component'], failure['exit_code'])
    payload = dict(schema_version=1, run_id=run_id, request_id=request_id,
                   observed_run_epoch_ns=epoch, requested_at_monotonic_ns=time.monotonic_ns(),
                   backend_terminal_status='FAILED', note=note, native_failure=failure)
    return write_once(root / 'artifacts/external_episode/finish_request.json', payload)

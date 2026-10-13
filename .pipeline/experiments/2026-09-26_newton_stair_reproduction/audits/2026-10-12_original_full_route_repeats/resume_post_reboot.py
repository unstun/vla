"""Continue only the four unstarted members of the fixed post-reboot cohort."""
from pathlib import Path
import argparse
import json
import os
import threading
import time

import run_post_reboot as post
import run_repeats as original

HERE = Path(__file__).resolve().parent
PARENT = post.OUTPUT
OUTPUT = original.TASK / 'results/full_route_repeats_post_reboot_resume01_20261012'
CONTROL = OUTPUT.with_name(OUTPUT.name + '_control')
ATTEMPTS = tuple(range(10, 14))


def verify_parent():
    request = json.loads((PARENT / 'request.json').read_text())
    progress = json.loads((PARENT / 'progress.json').read_text())
    before = json.loads((PARENT / 'identities_before.json').read_text())
    assert request['tags'] == [f'v147_full_candidate_attempt{n:02d}' for n in range(8, 14)]
    assert progress['state'] == 'interrupted' and progress['active'] is None
    assert progress['error'] == "AssertionError('Other GPU compute tasks active; retain results and inspect')"
    assert [r['tag'] for r in progress['completed']] == request['tags'][:2]
    command = Path(f"/proc/{request['pid']}/cmdline")
    assert not command.exists() or b'run_post_reboot.py' not in command.read_bytes()
    assert post.identities() == before, 'Boot/source/native identity changed since parent cohort'
    for row in progress['completed']:
        path = original.TASK / 'results/recording_v147' / row['tag'] / 'outcome.json'
        assert original.sha(path) == row['outcome_sha256']
    for attempt in ATTEMPTS:
        tag = f'v147_full_candidate_attempt{attempt:02d}'
        assert not (original.TASK / 'trials' / tag).exists(), tag
        assert not (original.TASK / 'results/recording_v147' / tag).exists(), tag
    return {name: original.sha(PARENT / name)
            for name in ('request.json', 'progress.json', 'identities_before.json')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wait-seconds', type=float, default=600)
    args = parser.parse_args()
    assert 0 <= args.wait_seconds <= 600
    assert not OUTPUT.exists() and not CONTROL.exists()
    parent_hashes = verify_parent()
    CONTROL.mkdir()
    original.save(CONTROL / 'request.json', {
        'pid': os.getpid(), 'started_unix_s': time.time(), 'parent': str(PARENT),
        'parent_hashes': parent_hashes, 'attempts': ATTEMPTS,
        'wait_budget_s': args.wait_seconds, 'source_sha256': original.sha(Path(__file__)),
        'plan_sha256': original.sha(HERE / 'RESUME_PLAN.md')})
    wait_remaining = args.wait_seconds

    def identities():
        assert {name: original.sha(PARENT / name) for name in parent_hashes} == parent_hashes
        return {**post.identities(), 'resume_runner_sha256': original.sha(Path(__file__)),
                'resume_plan_sha256': original.sha(HERE / 'RESUME_PLAN.md'),
                'parent_hashes': parent_hashes}

    def resources():
        nonlocal wait_remaining
        while True:
            error = None
            try:
                row = post.resources()
            except AssertionError as exc:
                error = str(exc)
                assert error in ('Post-reboot memory admission below20GiB',
                                 'Other GPU compute tasks active; retain results and inspect'), error
                row = None
            with (CONTROL / 'admission.jsonl').open('a') as stream:
                stream.write(json.dumps({'unix_s': time.time(), 'admitted': row is not None,
                                         'reason': error, 'wait_remaining_s': wait_remaining}) + '\n')
            if row is not None:
                return row
            if wait_remaining <= 0:
                raise RuntimeError('Resource admission wait exhausted; no new launch')
            start = time.monotonic()
            time.sleep(min(20, wait_remaining))
            wait_remaining = max(0, wait_remaining - (time.monotonic() - start))

    stop = threading.Event()
    observer = None
    state = 'waiting_for_resources'
    original.save(CONTROL / 'state.json', {'state': state, 'unix_s': time.time()})
    try:
        resources()  # Do not consume an attempt or create its batch root while waiting.
        assert verify_parent() == parent_hashes
        original.OUTPUT = OUTPUT
        original.ATTEMPTS = ATTEMPTS
        original.identities = identities
        original.resources = resources
        post.OUTPUT = OUTPUT
        observer = threading.Thread(target=post.observe, args=(stop,), daemon=True)
        observer.start()
        state = 'running'
        original.save(CONTROL / 'state.json', {'state': state, 'unix_s': time.time()})
        original.main()
        state = 'completed'
    except BaseException as exc:
        state = 'interrupted'
        original.save(CONTROL / 'error.json', {'error': repr(exc), 'unix_s': time.time()})
        raise
    finally:
        stop.set()
        if observer:
            observer.join(timeout=5)
            assert not observer.is_alive(), 'Resource observer still writing'
        original.save(CONTROL / 'state.json', {'state': state, 'unix_s': time.time()})


if __name__ == '__main__':
    main()

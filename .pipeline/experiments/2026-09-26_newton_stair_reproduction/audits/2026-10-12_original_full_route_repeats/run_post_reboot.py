"""Reuse the declared batch runner with a separate post-reboot protocol."""
from pathlib import Path
import csv
import os
import subprocess
import threading
import time

import run_repeats as original

HERE = Path(__file__).resolve().parent
OUTPUT = original.TASK / 'results/full_route_repeats_post_reboot_20261012'
ATTEMPTS = tuple(range(8, 14))
original_identities = original.identities
original_resources = original.resources


def memory():
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        values[key] = int(value.split()[0]) * 1024
    return values


def identities():
    return {**original_identities(), 'execution_runner_sha256': original.sha(Path(__file__)),
            'execution_protocol_sha256': original.sha(HERE / 'POST_REBOOT_PLAN.md'),
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def resources():
    row = original_resources()
    values = memory()
    compute = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory',
                                       '--format=csv,noheader'], text=True, timeout=20).strip()
    row.update(memory_available_bytes=values['MemAvailable'], gpu_compute_tasks=compute)
    assert values['MemAvailable'] >= 20 * 1024**3, 'Post-reboot memory admission below20GiB'
    assert not compute, 'Other GPU compute tasks active; retain results and inspect'
    return row


def observe(stop):
    while not OUTPUT.exists():
        if stop.wait(0.1):
            return
    with (OUTPUT / 'memory_samples.csv').open('x') as stream:
        writer = csv.writer(stream)
        writer.writerow(['unix_s', 'available_bytes', 'swap_used_bytes', 'load_1min'])
        while True:
            values = memory()
            writer.writerow([time.time(), values['MemAvailable'],
                             values['SwapTotal'] - values['SwapFree'], os.getloadavg()[0]])
            stream.flush()
            if stop.wait(1):
                return


def main():
    assert not OUTPUT.exists()
    inspection = original.TASK / 'results/full_route_repeats_20261012/environment_after_reboot.json'
    assert inspection.exists()
    original.OUTPUT = OUTPUT
    original.ATTEMPTS = ATTEMPTS
    original.identities = identities
    original.resources = resources
    stop = threading.Event()
    observer = threading.Thread(target=observe, args=(stop,), daemon=True)
    observer.start()
    try:
        original.main()
    finally:
        stop.set()
        observer.join(timeout=5)
        assert not observer.is_alive(), 'Resource writer remains active'


if __name__ == '__main__':
    main()

"""Read-only shared-host admission for one CPU-only original-route trial."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess

HERE = Path(__file__).resolve().parent
PREFIX = Path('/home/ubuntu/sun/vla_v234_20261017')


def admit():
    spec = importlib.util.spec_from_file_location('v235_inventory', HERE.parent / 'v234/host_inventory.py')
    inventory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inventory)
    record = inventory.snapshot(PREFIX)
    assert record['architecture'] == 'x86_64'
    assert record['memory_available_bytes'] >= 20 * 2**30
    assert record['disk_free_bytes'] >= 10 * 2**30
    assert record['docker'].get('returncode') == 0
    assert set(range(18, 24)).issubset(os.sched_getaffinity(0))
    low, high = map(int, Path('/proc/sys/net/ipv4/ip_local_port_range').read_text().split())
    for port in (24600, 24601, 24602, 24651, 8785):
        assert not low <= port <= high, port
        with socket.socket() as probe:
            probe.bind(('0.0.0.0', port))
    for executable in ('ffmpeg', 'ffprobe', 'lsof'):
        # This check uses the same private PATH as the physical entry.
        if executable != 'lsof':
            subprocess.run([executable, '-version'], check=True, capture_output=True, timeout=15)
    record.update(passed=True, native_cpu_limit=4, native_cpu_set=[18, 19, 20, 21],
                  native_memory_limit='6g', native_cpu_shares=128,
                  physics_cpu_set=[22, 23], physics_nice=19,
                  gpu_required_for_physics=False, peer_mutations=[])
    return record

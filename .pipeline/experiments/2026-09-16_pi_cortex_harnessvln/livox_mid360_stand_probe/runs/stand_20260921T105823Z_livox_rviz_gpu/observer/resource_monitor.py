"""Read-only Linux host/owned-process sampling for a bounded display probe."""

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def cpu_times(path=Path('/proc/stat')):
    values = [int(x) for x in path.read_text().splitlines()[0].split()[1:]]
    # guest/guest_nice are already included in user/nice.
    return sum(values[:8]), values[3] + values[4]


def memory_bytes(path=Path('/proc/meminfo')):
    info = {}
    for line in path.read_text().splitlines():
        key, value = line.split(':', 1)
        info[key] = int(value.strip().split()[0]) * 1024
    return {k: info[k] for k in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree')}


def process_stats(pid):
    root = Path('/proc') / str(pid)
    text = (root / 'stat').read_text()
    end = text.rindex(')')
    fields = text[end + 2:].split()
    # Fields start at Linux stat field 3; utime/stime are 14/15, RSS is 24.
    return {
        'pid': pid,
        'cpu_ticks': int(fields[11]) + int(fields[12]),
        'rss_bytes': int(fields[21]) * os.sysconf('SC_PAGE_SIZE'),
        'start_ticks': int(fields[19]),
        'state': fields[0],
    }


def sample_gpu():
    command = ['nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used,memory.total,utilization.encoder,encoder.stats.sessionCount,encoder.stats.averageFps',
               '--format=csv,noheader,nounits']
    result = subprocess.run(command, capture_output=True, text=True, timeout=2)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    rows = []
    for line in result.stdout.splitlines():
        values = [x.strip() for x in line.split(',')]
        rows.append({'index': int(values[0]), 'utilization_percent': float(values[1]),
                     'memory_used_mib': float(values[2]), 'memory_total_mib': float(values[3]),
                     'encoder_utilization_percent': float(values[4]),
                     'encoder_session_count': int(values[5]),
                     'encoder_average_fps': float(values[6])})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pids', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--max-wall-seconds', type=float, default=1500)
    args = parser.parse_args()
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    previous_cpu = cpu_times()
    previous_processes = {}
    previous_time = time.monotonic()
    started = previous_time
    ticks_per_second = os.sysconf('SC_CLK_TCK')
    with args.output.open('w', buffering=1) as stream:
        while not stopping and time.monotonic() - started < args.max_wall_seconds:
            now = time.monotonic()
            row = {'monotonic_ns': time.monotonic_ns(), 'wall_time_ns': time.time_ns(),
                   'elapsed_s': now - started, 'host_cpu_count': os.cpu_count(), 'errors': []}
            current_cpu = cpu_times()
            delta = current_cpu[0] - previous_cpu[0]
            row['host_cpu_percent'] = None if not delta else 100 * (1 - (current_cpu[1] - previous_cpu[1]) / delta)
            previous_cpu = current_cpu
            row['host_memory_bytes'] = memory_bytes()
            try:
                row['gpus'] = sample_gpu()
            except Exception as error:
                row['errors'].append('gpu:' + str(error))
            try:
                registered = json.loads(args.pids.read_text())
            except Exception:
                registered = {}
            processes = {}
            for name, pid in registered.items():
                try:
                    record = process_stats(int(pid))
                    prev = previous_processes.get(name)
                    if prev and prev['start_ticks'] == record['start_ticks'] and now > previous_time:
                        record['cpu_percent_one_core'] = 100 * (record['cpu_ticks'] - prev['cpu_ticks']) / ticks_per_second / (now - previous_time)
                    processes[name] = record
                except (FileNotFoundError, ProcessLookupError):
                    processes[name] = {'pid': pid, 'exited': True}
            row['processes'] = processes
            previous_processes = {k: v for k, v in processes.items() if 'cpu_ticks' in v}
            previous_time = now
            try:
                snapshot = json.loads(args.snapshot.read_text())
                row['sim_snapshot'] = {k: snapshot.get(k) for k in ('run_id', 'run_epoch_ns', 'sim_step', 'sim_time_s', 'wall_monotonic_ns')}
            except Exception:
                row['sim_snapshot'] = None
            stream.write(json.dumps(row, sort_keys=True) + '\n')
            deadline = now + 1.0
            while not stopping and time.monotonic() < deadline:
                time.sleep(max(0.0, min(0.1, deadline - time.monotonic())))


if __name__ == '__main__':
    main()

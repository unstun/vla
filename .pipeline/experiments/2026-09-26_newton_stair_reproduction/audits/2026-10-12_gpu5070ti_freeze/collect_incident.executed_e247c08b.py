"""Read historical host evidence; write only this audit's remote output directory."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import time

TASK = Path('/data/sun/vla_mppi_20261009')
OUTPUT = TASK / 'results/freeze_20261012'
INCIDENT_BOOT = '156d3e01bce64a6db2e8ab54e3718fbc'
RUN = TASK / 'trials/v147_full_candidate_attempt05/runs/v147_full_candidate_attempt05'
POWER = '2026-10-12 08:54:29 UTC'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')


def probe(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        return {'command': command, 'exit': result.returncode,
                'stdout': result.stdout, 'stderr': result.stderr}
    except subprocess.TimeoutExpired:
        return {'command': command, 'exit': None, 'error': 'timeout after 30 s'}


def journal(start, end, pattern=None, units=()):
    command = ['journalctl', '--boot=' + INCIDENT_BOOT, '--since=' + start,
               '--until=' + end, '--no-pager', '-o', 'json']
    if pattern:
        command.append('--grep=' + pattern)
    for unit in units:
        command.extend(['-u', unit])
    response = probe(command)
    assert response.get('exit') == 0, response
    rows = [json.loads(line) for line in response['stdout'].splitlines() if line.startswith('{')]
    return rows, response


def event(row):
    return {'unix_us': int(row['__REALTIME_TIMESTAMP']),
            'monotonic_us': int(row['__MONOTONIC_TIMESTAMP']),
            'unit': row.get('_SYSTEMD_UNIT'), 'message': row.get('MESSAGE', '')}


def trace(path, field, scale, offset, nested=None):
    times, errors = [], 0
    with path.open() as stream:
        for line in stream:
            row = json.loads(line)
            if nested:
                row = row[nested]
            times.append(row[field] / scale)
            errors += bool(row.get('error'))
    assert len(times) > 1
    def utc(t):
        return datetime.fromtimestamp(t + offset, timezone.utc).isoformat()
    gaps = sorted(((b-a, a, b) for a, b in zip(times, times[1:])), reverse=True)
    return {'source': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size,
            'records': len(times), 'first_utc': utc(times[0]), 'last_utc': utc(times[-1]),
            'reported_errors': errors,
            'duplicate_timestamps': sum(b == a for a, b in zip(times, times[1:])),
            'backward_timestamps': sum(b < a for a, b in zip(times, times[1:])),
            'largest_gaps': [{'seconds': g, 'from_utc': utc(a), 'to_utc': utc(b)}
                             for g, a, b in gaps[:5]]}


def main():
    global OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=OUTPUT)
    OUTPUT = parser.parse_args().output
    assert OUTPUT.parent == TASK / 'results' and OUTPUT.name.startswith('freeze_20261012')
    assert Path(__file__).resolve().is_relative_to(TASK / 'repo')
    OUTPUT.mkdir(exist_ok=False)
    returned = OUTPUT / 'return'
    returned.mkdir()
    rows, response = journal('2026-10-12 08:52:00 UTC', '2026-10-12 08:55:40 UTC',
                             units=('ssh', 'systemd-logind'))
    save(OUTPUT / 'clock_and_login_journal.json', response)
    offsets = [(int(r['__REALTIME_TIMESTAMP']) - int(r['__MONOTONIC_TIMESTAMP'])) / 1e6
               for r in rows]
    assert len(offsets) >= 2 and max(offsets) - min(offsets) < 0.001
    offset = statistics.median(offsets)
    summary = {'incident_boot_id': INCIDENT_BOOT, 'capture_unix_s': time.time(),
               'current_boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
               'collector_sha256': sha(Path(__file__)),
               'clock_map': {'pairs': len(offsets), 'offset_s': offset,
                             'offset_range_s': max(offsets) - min(offsets)},
               'events': [event(r) for r in rows if any(s in r.get('MESSAGE', '')
                          for s in ('Accepted publickey', 'Power key', 'power off', 'powering'))],
               'traces': {
                   'clock': trace(RUN / 'clock_samples.jsonl', 'sent', 1e9, offset),
                   'backend': trace(RUN / 'backend_states.jsonl', 'monotonic_s', 1, offset, 'data')},
               'network_comparison': []}
    for start, end in [('07:00:00', '07:30:00'), ('08:00:00', '08:30:00'), ('08:30:00', '08:54:29')]:
        rows, raw = journal('2026-10-12 ' + start + ' UTC', '2026-10-12 ' + end + ' UTC',
                            'Failed to dial a quic|Accepted publickey|frpc.*restarted')
        counts = Counter('cloudflared_dial_errors' if 'quic' in r.get('MESSAGE', '')
                         else 'ssh_accepts' if 'Accepted' in r.get('MESSAGE', '')
                         else 'frpc_restart' for r in rows)
        name = 'network_' + start.replace(':', '') + '.json'
        save(OUTPUT / name, raw)
        summary['network_comparison'].append({'start_utc': start, 'end_utc': end,
                                               'counts': dict(counts), 'raw': str(OUTPUT / name)})
    for name, pattern in {
        'host_errors': 'Out of memory|oom-kill|Killed process|Xid|NVRM|soft lockup|hard LOCKUP|blocked for more than|I/O error|NETDEV WATCHDOG|thermal|throttl',
        'network_changes': 'login to server|frpc-watchdog.*(restarted|errors)|NETDEV|Link is|link down|link up|r816|e1000|carrier|NetworkManager.*(state change|connectivity)',
    }.items():
        rows, raw = journal('2026-10-12 08:30:00 UTC', POWER, pattern)
        save(OUTPUT / (name + '.json'), raw)
        summary[name] = {'window_start_utc': '2026-10-12 08:30:00 UTC',
                         'window_end_utc': POWER, 'matches': [event(r) for r in rows],
                         'query_exit': raw['exit'], 'stderr': raw['stderr']}
    snapshot = OUTPUT / 'sa12.snapshot'
    shutil.copyfile('/var/log/sysstat/sa12', snapshot)
    env_tz = os.environ.get('TZ')
    stats = {'snapshot': str(snapshot), 'sha256': sha(snapshot), 'bytes': snapshot.stat().st_size,
             'host_timezone': probe(['timedatectl', 'show', '-p', 'Timezone', '--value']),
             'environment_TZ': env_tz, 'window_is_host_local_time': True}
    for label, options in [('memory', ['-r', 'ALL']), ('swap', ['-S']), ('cpu', ['-u']),
                            ('load', ['-q']), ('swap_rate', ['-W']), ('disk', ['-d'])]:
        stats[label] = probe(['sar', '-f', str(snapshot), '-s', '04:30:00', '-e', '04:50:01', *options])
    save(returned / 'sysstat.json', stats)
    for name in ('result.json', 'realtime_pacing.json', 'navigation_clock_anchor.json'):
        shutil.copyfile(RUN / name, returned / ('attempt05_' + name))
    summary['partial_attempt05'] = {'raw_result_present': True,
        'copyback_present': (RUN / 'state_copyback.json').exists(),
        'retention_present': (RUN / 'retention_result.json').exists(),
        'qualified_completed_trial': False,
        'claim': 'Recorded physical arrival; shutdown interrupted closeout. No manufactured copyback.'}
    previous = TASK / 'results/full_route_repeats_20261012'
    for name in ['environment_after_reboot.json', 'pre_power_freeze_inspection.json',
                 'partial_attempt05_inventory.json', 'shutdown_context.json']:
        shutil.copyfile(previous / name, returned / name)
    summary['claim'] = ('Historical observations only. No reproduced host freeze or established root cause. '
                        'Continuous computation constrains the covered interval; it cannot rule out an earlier transient freeze.')
    save(returned / 'SUMMARY.json', summary)
    save(returned / 'raw_sources.json', {str(p): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                                       for p in sorted(OUTPUT.iterdir()) if p.is_file()})
    files = {str(p.relative_to(returned)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
             for p in sorted(returned.iterdir()) if p.is_file()}
    assert sum(f['bytes'] for f in files.values()) < 2 * 1024**2
    save(OUTPUT / 'return_manifest.json', {'root': str(returned), 'files': files,
                                          'bytes': sum(f['bytes'] for f in files.values())})
    print(json.dumps(summary))


if __name__ == '__main__':
    main()

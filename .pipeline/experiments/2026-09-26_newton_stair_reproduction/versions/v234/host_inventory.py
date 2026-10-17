"""Read-only host/peer inventory; never collect process command-line secrets."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import time


def capture(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        return {"returncode": result.returncode, "stdout": result.stdout,
                "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}


def processes():
    result = {}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            comm = (proc / 'comm').read_text().strip()
            if not any(word in comm.lower() for word in ('python', 'isaac', 'mps')):
                continue
            # comm can contain spaces/parentheses; fields after the final ')' start at 3.
            stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
            result[proc.name] = dict(comm=comm, start_ticks=int(stat[19]),
                                    uid=proc.stat().st_uid,
                                    executable=os.readlink(proc / 'exe'))
        except (OSError, ValueError, IndexError):
            continue
    return result


def snapshot(prefix):
    disk = shutil.disk_usage(prefix if prefix.exists() else prefix.parent)
    memory = {line.split(':')[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines()}
    return dict(time_ns=time.time_ns(), host=socket.gethostname(),
                system=platform.platform(), architecture=platform.machine(),
                uid=os.getuid(), cpu_count=os.cpu_count(), load=os.getloadavg(),
                disk_free_bytes=disk.free, memory_available_bytes=memory['MemAvailable'],
                peers=processes(),
                gpu=capture(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory',
                             '--format=csv,noheader']),
                docker=capture(['docker', 'info', '--format', '{{.ServerVersion}} {{.Architecture}}']),
                arm_binfmt=sorted(p.name for p in Path('/proc/sys/fs/binfmt_misc').iterdir()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--before', type=Path)
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve prior inventories'
    report = snapshot(args.prefix)
    if args.before:
        before = json.loads(args.before.read_text())
        report['prior_peer_continuity'] = {
            pid: ('same_process' if report['peers'].get(pid, {}).get('start_ticks') == row['start_ticks']
                  else 'exited_or_replaced') for pid, row in before['peers'].items()}
        # An exited peer is evidence to report, not proof this migration killed it.
    report['admitted_for_bounded_offline'] = (
        report['architecture'] == 'x86_64' and report['memory_available_bytes'] >= 20 * 2**30
        and report['disk_free_bytes'] >= 10 * 2**30 and report['docker'].get('returncode') == 0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('host', 'admitted_for_bounded_offline',
                                           'disk_free_bytes', 'memory_available_bytes')}))
    if not report['admitted_for_bounded_offline']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

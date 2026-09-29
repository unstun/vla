"""Linux counterpart of audits/2026-09-29_wall_clock_chain/host_sampler.py for trials on gpu5070ti (observation only;
runs as its own process). Revised after port review rounds 1 (B4), 2 (B6) and 3 (N23), before any use in a trial.

Once per second it writes one JSON line with:
- monotonic_ns and loadavg, as the macOS sampler;
- top: the ten processes that used the most CPU in the last interval, as {pid, pcpu, comm, cmd}. pcpu is the percent
  of one CPU over that interval, from utime + stime deltas in /proc/<pid>/stat. The macOS sampler takes ps's %CPU, a
  decaying average over up to a minute; Linux ps reports CPU time over the process's whole life, which hides a burst
  from a long-running process, so it is not used. comm is the kernel's 15-character name, where macOS ps gives the
  executable path. cmd adds the first 120 characters of the command line, only for processes of the invoking
  user and after redaction; other users' processes get null (round 2, B6: another user's command line carried a
  tunnel token). The ownership test is made on the opened /proc/<pid>/cmdline itself, so a reused pid cannot
  pass it. Redaction replaces the value, quoted or not, after any flag whose name contains token, passw, secret,
  key, credential or auth; the credentials in a scheme://user:password@ URL; and any run of 32 or more base64-like
  characters that mixes upper case, lower case and digits. For the invoking user's own processes it is best effort:
  a flag without such a keyword, or a shorter token, is not caught. Other users' processes are protected by the
  ownership test, not by redaction;
- cpu: the busy fraction of each CPU and of all CPUs over the interval, from /proc/stat (busy = all time except idle
  and iowait). The macOS sampler has no counterpart;
- psi: CPU, memory and I/O pressure from /proc/pressure/* (avg10 and the cumulative total in microseconds, for "some"
  and, where the kernel reports it, "full"). The macOS sampler has no counterpart;
- vm: paging counters from /proc/vmstat (pgpgin, pgpgout, pswpin, pswpout, pgmajfault) and free memory from
  /proc/meminfo in kB; macOS vm_stat has different counters;
- git: running git processes and their working directories. A process counts when the basename of its first argument
  is `git`; the macOS sampler requires a path ending in `/git`.
The first line follows a one-second baseline. Writes to the path given as argument 1 until SIGTERM.
With --processes instead of a path, it prints one redacted table of all processes (pid, user, elapsed seconds,
lifetime %CPU, RSS in kB, command) by the same rule, for the runner's pre-run snapshot, and exits.
"""
import json
import os
import pwd
import re
import signal
import sys
import time

CLK_TCK = os.sysconf("SC_CLK_TCK")
VMSTAT_KEYS = ("pgpgin", "pgpgout", "pswpin", "pswpout", "pgmajfault")
UID = os.getuid()
SECRET_FLAG = re.compile(
    r'(--?[A-Za-z_-]*(?:token|passw|secret|key|credential|auth)[A-Za-z_-]*(?:=|\s+))(?:"[^"]*"|\'[^\']*\'|[^\s"\']+)', re.I)
SECRET_URL = re.compile(r'([A-Za-z][A-Za-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@')
SECRET_RUN = re.compile(r'(?=[A-Za-z0-9+_=-]*[A-Z])(?=[A-Za-z0-9+_=-]*[a-z])(?=[A-Za-z0-9+_=-]*[0-9])[A-Za-z0-9+_=-]{32,}')


def redact(text):
    text = SECRET_FLAG.sub(r"\1<redacted>", text)
    text = SECRET_URL.sub(r"\1<redacted>@", text)
    return SECRET_RUN.sub("<redacted>", text)


def process_times():
    """{(pid, starttime): (ticks, comm)} for every readable process; starttime guards against pid reuse."""
    times = {}
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/stat") as f:
                stat = f.read()
        except OSError:
            continue
        comm = stat[stat.index("(") + 1:stat.rindex(")")]
        rest = stat[stat.rindex(")") + 2:].split()
        try:
            uid = os.stat(f"/proc/{name}").st_uid
        except OSError:
            uid = None
        times[(int(name), rest[19])] = (int(rest[11]) + int(rest[12]), comm, uid)
    return times


def cpu_times():
    """[(total, busy)] for all CPUs first, then each CPU, from /proc/stat."""
    out = []
    with open("/proc/stat") as f:
        for line in f:
            if not line.startswith("cpu"):
                break
            values = [int(v) for v in line.split()[1:]]
            total = sum(values[:8])  # user nice system idle iowait irq softirq steal; guest time is inside user
            out.append((total, total - values[3] - values[4]))
    return out


def pressure():
    out = {}
    for resource in ("cpu", "memory", "io"):
        try:
            with open(f"/proc/pressure/{resource}") as f:
                for line in f:
                    kind, *fields = line.split()
                    values = dict(field.split("=") for field in fields)
                    out[f"{resource}_{kind}"] = {"avg10": float(values["avg10"]), "total_us": int(values["total"])}
        except OSError:
            pass
    return out


def vm_counters():
    counters = {}
    with open("/proc/vmstat") as f:
        for line in f:
            key, value = line.split()
            if key in VMSTAT_KEYS:
                counters[key] = int(value)
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith(("MemFree:", "MemAvailable:")):
                key, value = line.split()[:2]
                counters[key.rstrip(":")] = int(value)
    return counters


def command_line(pid, uid, limit=120):
    """The redacted command line of the invoking user's process; None for any other user's."""
    if uid != UID:
        return None
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            if os.fstat(f.fileno()).st_uid != UID:  # the pid was reused by another user's process
                return None
            return redact(f.read().replace(b"\0", b" ").decode(errors="replace").strip())[:limit]
    except OSError:
        return None


def process_table():
    """All processes, lifetime %CPU as ps gives it, with the same redaction rule as the sampler's cmd."""
    ticks_per_s, uptime = CLK_TCK, float(open("/proc/uptime").read().split()[0])
    rows = []
    for (pid, start), (ticks, comm, uid) in process_times().items():
        elapsed = max(uptime - int(start) / ticks_per_s, 1e-9)
        try:
            user = pwd.getpwuid(uid).pw_name if uid is not None else "?"
            rss = next((line.split()[1] for line in open(f"/proc/{pid}/status") if line.startswith("VmRSS:")), "0")
        except (KeyError, OSError):
            user, rss = str(uid), "0"
        rows.append((100. * ticks / ticks_per_s / elapsed, pid, user, int(elapsed), rss,
                     command_line(pid, uid, 220) or f"[{comm}]"))
    rows.sort(reverse=True)
    return "\n".join(f"{pid:>7} {user:<12} {elapsed:>8}s {pcpu:5.1f}% {rss:>8}kB {cmd}"
                     for pcpu, pid, user, elapsed, rss, cmd in rows)


def git_processes():
    found = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/cmdline", "rb") as f:
                first = f.read().split(b"\0")[0].decode(errors="replace")
        except OSError:
            continue
        if os.path.basename(first) == "git":
            try:
                cwd = os.readlink(f"/proc/{name}/cwd")
            except OSError:
                cwd = None
            found.append({"pid": int(name), "cwd": cwd})
    return found


def main():
    running = [True]
    signal.signal(signal.SIGTERM, lambda *_: running.__setitem__(0, False))
    before, cpus_before, t_before = process_times(), cpu_times(), time.monotonic()
    time.sleep(1.)
    with open(sys.argv[1], "w") as f:
        while running[0]:
            now, cpus, t_now = process_times(), cpu_times(), time.monotonic()
            interval = t_now - t_before
            usage = []
            for key, (ticks, comm, uid) in now.items():
                previous = before.get(key)
                delta = ticks - previous[0] if previous else ticks  # a process new in this interval: all its CPU
                if delta > 0:
                    usage.append((100. * delta / CLK_TCK / interval, key[0], comm, uid))
            usage.sort(reverse=True)
            busy = [round((b1 - b0) / (a1 - a0), 3) if a1 > a0 else None
                    for (a0, b0), (a1, b1) in zip(cpus_before, cpus)]
            f.write(json.dumps({
                "monotonic_ns": time.monotonic_ns(), "interval_s": round(interval, 3), "loadavg": os.getloadavg(),
                "top": [{"pid": pid, "uid": uid, "pcpu": round(pcpu, 1), "comm": comm, "cmd": command_line(pid, uid)}
                        for pcpu, pid, comm, uid in usage[:10]],
                "cpu": {"all": busy[0], "per_cpu": busy[1:]}, "psi": pressure(), "vm": vm_counters(),
                "git": git_processes()}) + "\n")
            f.flush()
            before, cpus_before, t_before = now, cpus, t_now
            time.sleep(max(0., 1. - (time.monotonic() - t_now)))


if __name__ == "__main__":
    if sys.argv[1:] == ["--processes"]:
        print(process_table())
    else:
        main()

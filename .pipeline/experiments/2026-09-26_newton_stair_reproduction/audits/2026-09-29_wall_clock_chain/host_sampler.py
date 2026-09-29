"""Standalone host-load sampler for an uninstrumented trial (observation only; runs as its own process).

Once per second: load average, the ten busiest processes (ps), VM paging counters, and the working directories
of any running `git` processes (the Claude desktop app's session-diff refreshes run git diff in other
repositories). Writes JSON lines to the path given as argument 1 until SIGTERM.
"""
import json
import os
import re
import signal
import subprocess
import sys
import time


def main():
    running = [True]
    signal.signal(signal.SIGTERM, lambda *_: running.__setitem__(0, False))
    with open(sys.argv[1], "w") as f:
        while running[0]:
            top = subprocess.run(["ps", "-Ao", "pid,pcpu,pmem,comm", "-r"], capture_output=True, text=True).stdout.splitlines()[1:11]
            vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
            counters = {key.strip(): int(value) for key, value in re.findall(r'"?([A-Za-z ]+)"?:\s+(\d+)\.', vm)
                        if key.strip() in ("Pageins", "Pageouts", "Swapins", "Swapouts", "Pages free", "Decompressions")}
            gits = []
            for line in subprocess.run(["ps", "-Ao", "pid,pcpu,command"], capture_output=True, text=True).stdout.splitlines():
                fields = line.split(None, 2)
                if len(fields) == 3 and fields[2].split(" ")[0].endswith("/git"):
                    cwd = subprocess.run(["lsof", "-a", "-p", fields[0], "-d", "cwd", "-Fn"], capture_output=True,
                                         text=True).stdout
                    gits.append({"pid": int(fields[0]), "pcpu": float(fields[1]),
                                 "cwd": next((l[1:] for l in cwd.splitlines() if l.startswith("n")), None)})
            f.write(json.dumps({"monotonic_ns": time.monotonic_ns(), "loadavg": os.getloadavg(), "vm": counters,
                                "top": [l.strip() for l in top], "git": gits}) + "\n")
            f.flush()
            time.sleep(1.)


if __name__ == "__main__":
    main()

"""External wake-up lateness probe: a separate process, so only OS scheduling can delay it (no shared GIL).

Sleeps 20 ms in a loop and records how late each wake-up is, until it receives SIGTERM.
"""
import signal
import sys
import time

import numpy as np


def main():
    path = sys.argv[1]
    running = [True]
    signal.signal(signal.SIGTERM, lambda *_: running.__setitem__(0, False))
    samples = []
    while running[0]:
        start = time.monotonic_ns()
        time.sleep(.02)
        samples.append((start, time.monotonic_ns() - start - 20_000_000))
    np.save(path, np.asarray(samples, dtype=np.int64))


if __name__ == "__main__":
    main()

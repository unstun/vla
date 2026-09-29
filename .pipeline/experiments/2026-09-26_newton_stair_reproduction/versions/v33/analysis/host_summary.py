"""Summary of the Linux host sampler's record of a trial on gpu5070ti
(hosts/2026-09-29_gpu5070ti/host_sampler_linux.py).

Usage: host_summary.py <host.jsonl> <output JSON> <the invoking user's uid on the host>. Written before v33's
trial; it reads only the sampler's file and writes only the output file. Reported, over the whole record:
- the sampler's own intervals (a long one means the sampler itself did not run on time);
- the 1-minute load, the busy fraction of all CPUs and the busiest CPU in each interval;
- pressure: for "some" and "full" CPU, memory and I/O, the share of each interval with a stalled task (from the
  cumulative totals), and the largest avg10;
- paging: swap-in, swap-out and major faults over the record, and the lowest available memory;
- processes: for each process name and owner class (the invoking user or another user), its peak share of one CPU in
  an interval and its CPU time summed over the intervals where it was among the ten busiest (a lower bound);
- git processes: the intervals with any.
Process names only: command lines are not copied into the summary.
"""
import collections
import json
from pathlib import Path
import sys


def quantiles(values):
    if not values:
        return None
    v = sorted(values)
    pick = lambda q: v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]
    return {"n": len(v), "min": round(v[0], 4), "p50": round(pick(0.5), 4), "p99": round(pick(0.99), 4),
            "max": round(v[-1], 4)}


def main():
    rows = [json.loads(line) for line in open(sys.argv[1]) if line.strip()]
    me = int(sys.argv[3])
    intervals = [r["interval_s"] for r in rows]
    stalls = {}
    for kind in ("cpu_some", "cpu_full", "memory_some", "memory_full", "io_some", "io_full"):
        shares, avg10 = [], []
        for a, b in zip(rows, rows[1:]):
            pa, pb = a["psi"].get(kind), b["psi"].get(kind)
            if pa and pb and b["interval_s"]:
                shares.append((pb["total_us"] - pa["total_us"]) / 1e6 / b["interval_s"])
        avg10 = [r["psi"][kind]["avg10"] for r in rows if r["psi"].get(kind)]
        stalls[kind] = {"stalled_share_per_interval": quantiles(shares), "avg10_max": max(avg10, default=None)}
    vm0, vm1 = rows[0]["vm"], rows[-1]["vm"]
    processes = collections.defaultdict(lambda: {"peak_pcpu": 0.0, "cpu_s_lower_bound": 0.0, "intervals_in_top10": 0})
    for r in rows:
        for p in r["top"]:
            key = (p["comm"], "invoking user" if p["uid"] == me else "other user")
            entry = processes[key]
            entry["peak_pcpu"] = max(entry["peak_pcpu"], p["pcpu"])
            entry["cpu_s_lower_bound"] += p["pcpu"] / 100 * r["interval_s"]
            entry["intervals_in_top10"] += 1
    ranked = sorted(processes.items(), key=lambda kv: -kv[1]["cpu_s_lower_bound"])
    result = {
        "samples": len(rows),
        "span_s": round((rows[-1]["monotonic_ns"] - rows[0]["monotonic_ns"]) / 1e9, 1),
        "sampler_interval_s": dict(quantiles(intervals), over_1p5_s=sum(i > 1.5 for i in intervals)),
        "load1": quantiles([r["loadavg"][0] for r in rows]),
        "cpu_all_busy": quantiles([r["cpu"]["all"] for r in rows]),
        "busiest_cpu_busy": quantiles([max(r["cpu"]["per_cpu"]) for r in rows]),
        "cpus": len(rows[0]["cpu"]["per_cpu"]),
        "pressure": stalls,
        "paging": {"pswpin": vm1["pswpin"] - vm0["pswpin"], "pswpout": vm1["pswpout"] - vm0["pswpout"],
                   "pgmajfault": vm1["pgmajfault"] - vm0["pgmajfault"],
                   "mem_available_min_kb": min(r["vm"]["MemAvailable"] for r in rows)},
        "processes_by_cpu": [{"comm": k[0], "owner": k[1], **{kk: round(vv, 2) for kk, vv in v.items()}}
                             for k, v in ranked[:20]],
        "git_intervals": sum(1 for r in rows if r.get("git")),
    }
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("samples", "span_s", "sampler_interval_s", "load1", "cpu_all_busy",
                                             "busiest_cpu_busy", "git_intervals")}, indent=1))


if __name__ == "__main__":
    main()

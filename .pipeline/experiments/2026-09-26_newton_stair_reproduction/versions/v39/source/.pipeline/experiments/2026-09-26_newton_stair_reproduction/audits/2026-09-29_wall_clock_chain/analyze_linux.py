"""Linux-side attribution of body-pose gaps (container_site/sitecustomize.py records).

Inputs in runs/<run>/diagnostics/linux/: <pid>_cmdline.txt, <pid>_gc.i64 (start, duration, generation,
collected, thread), and in the bridge process <pid>_offer.i64 (sim_ns, receive_ns, accepted),
<pid>_take.i64 (sim_ns, deliver_ns), <pid>_publish.i64 (start_ns, duration_ns). All times are the
container's CLOCK_MONOTONIC, the same clock as backend_body_callbacks.jsonl.
For each backend body-pose gap over 0.15 s it reports, inside the gap:
- states the bridge received (offers) and delivered (takes);
- the bridge's publish callbacks: the longest one, and the longest pause between callback starts;
- the longest collection in the bridge and in the backend process.
Reading: no offers means nothing arrived from the Mac (upstream); offers without takes and a long pause
between callbacks means the bridge's timer did not run; a long callback means the timer ran but one call
took the time.
"""
import array
import json
from pathlib import Path
import sys

import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]


def load(path, width):
    data = array.array("q")
    data.frombytes(path.read_bytes())
    return np.asarray(data, dtype=np.int64).reshape(-1, width)


def main():
    name = sys.argv[1]
    run = E / "runs" / name
    linux = run / "diagnostics/linux"
    processes = {}
    for path in linux.glob("*_cmdline.txt"):
        pid = path.name.split("_")[0]
        processes[pid] = path.read_text().strip()
    role = {}
    for pid, command in processes.items():
        if "foxy_bridge_node" in command or "lite3_sim_bridge" in command:
            role[pid] = "bridge"
        elif "p2b_backend_ros" in command or "native_backend_entry" in command:
            role[pid] = "backend"
    gc_by_pid = {path.name.split("_")[0]: load(path, 5) for path in linux.glob("*_gc.i64")}
    summary = {"run": name, "processes": {pid: {"command": processes.get(pid, "?")[:160], "role": role.get(pid),
               "collections": int(len(events)), "max_ms": round(float(events[:, 1].max()) / 1e6, 1) if len(events) else 0,
               "generation2": [round(float(d) / 1e6, 1) for d in events[events[:, 2] == 2, 1]]}
               for pid, events in gc_by_pid.items()}}
    bridge = [pid for pid, r in role.items() if r == "bridge" and (linux / f"{pid}_offer.i64").exists()]
    if not bridge:
        (H / f"linux_attribution_{name}.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=1))
        return
    pid = bridge[0]
    offers, takes, publish = load(linux / f"{pid}_offer.i64", 3), load(linux / f"{pid}_take.i64", 2), load(linux / f"{pid}_publish.i64", 2)
    # Container files are appended in flush order; sort by time before differencing.
    offers, takes, publish = offers[np.argsort(offers[:, 1], kind="stable")], takes[np.argsort(takes[:, 1], kind="stable")], \
        publish[np.argsort(publish[:, 0], kind="stable")]
    delivered = {int(s): int(t) for s, t in takes}
    received = {int(s): int(t) for s, t, a in offers if a}
    latency = np.array([delivered[s] - received[s] for s in delivered if s in received]) / 1e6
    starts = publish[:, 0]
    summary["bridge"] = {
        "pid": pid, "received": len(received), "delivered": len(delivered),
        "superseded": len(set(received) - set(delivered)),
        "receive_to_deliver_ms": {"median": float(np.median(latency)), "p99": float(np.quantile(latency, .99)),
                                  "max": float(latency.max())},
        "publish_callback_ms": {"median": float(np.median(publish[:, 1]) / 1e6), "p99": float(np.quantile(publish[:, 1], .99) / 1e6),
                                "max": float(publish[:, 1].max() / 1e6)},
        "pause_between_callback_starts_ms": {"median": float(np.median(np.diff(starts)) / 1e6),
                                             "max": float(np.diff(starts).max() / 1e6)},
    }
    backend_pid = next((p for p, r in role.items() if r == "backend"), None)
    callbacks = [json.loads(line) for line in open(run / "backend_body_callbacks.jsonl")]
    gaps = []
    for a, b in zip(callbacks, callbacks[1:]):
        lo, hi = a["entered_ns"], b["entered_ns"]
        if hi - lo <= 150_000_000:
            continue
        inside_offers = offers[(offers[:, 1] > lo) & (offers[:, 1] < hi)]
        inside_takes = takes[(takes[:, 1] > lo) & (takes[:, 1] < hi)]
        window = publish[(publish[:, 0] + publish[:, 1] > lo) & (publish[:, 0] < hi)]
        pause = np.diff(np.concatenate(([lo], window[:, 0], [hi]))).max() / 1e6

        def longest_gc(p):
            events = gc_by_pid.get(p)
            if events is None or not len(events):
                return None
            mask = (events[:, 0] < hi) & (events[:, 0] + events[:, 1] > lo)
            return round(float(events[mask, 1].max()) / 1e6, 1) if mask.any() else 0.0
        gaps.append({"backend_gap_ms": round((hi - lo) / 1e6, 1), "stamps_s": [a["stamp_ns"] / 1e9, b["stamp_ns"] / 1e9],
                     "bridge_received": int(len(inside_offers)), "bridge_delivered": int(len(inside_takes)),
                     "longest_publish_callback_ms": round(float(window[:, 1].max()) / 1e6, 1) if len(window) else None,
                     "longest_pause_between_callbacks_ms": round(float(pause), 1),
                     "longest_bridge_collection_ms": longest_gc(pid), "longest_backend_collection_ms": longest_gc(backend_pid)})
    summary["backend_gaps_over_150ms"] = gaps
    (H / f"linux_attribution_{name}.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=1)[:6000])


if __name__ == "__main__":
    main()

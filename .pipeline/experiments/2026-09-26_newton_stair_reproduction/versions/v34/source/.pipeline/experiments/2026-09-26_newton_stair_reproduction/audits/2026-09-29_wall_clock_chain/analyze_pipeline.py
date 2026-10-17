"""End-to-end body-state delivery in an instrumented run (diag_worker + container_site records).

Per body state (BODY_STATE_V2, keyed by its stamp, which is the same integer in the frame header, the
bridge's CompleteStateStream and the backend callback): Mac enqueue, Mac send start/end (worker sender
thread), bridge receive (offer), bridge delivery (take), backend callback entry. Container times are mapped
to the Mac clock through the clock filter's offset (Mac - Linux) nearest in time.
Segments (pre-registered in versions/v32/PLAN.md): worker queue = send start - enqueue; worker send = the
send call; transit and bridge receipt = bridge receive - send end (the host-to-VM path plus the bridge's
telemetry thread, which receives and decodes before stamping); bridge hold = delivery - receive; ROS delivery
= backend callback - delivery. For each backend gap over 150 ms it reports every pose from the one before
the gap to the one after it, where each one's time went, the bridge's publish-callback activity and the
collections in the bridge and backend processes during the gap. Each pose that reached the bridge but was
superseded there is blamed on one segment by a fixed rule against the next pose p', with a 15 ms threshold (the
10 ms timer period plus a margin for its jitter): received >= 15 ms before p' -> "bridge_timer" (the timer did not
deliver it in time); otherwise sent < 15 ms before p' -> "worker_sender" (they left the worker bunched);
otherwise "transit_or_receipt" (sent apart, received bunched). The receive spacing of every superseded pose is
reported too. Only offers the bridge accepted count as received; the bridge is matched as foxy_bridge_node and
the backend as native_backend_entry.py.
All record arrays are sorted by time first (container files are appended in flush order).
Writes pipeline_<run>.json.
"""
import array
import bisect
import json
from pathlib import Path
import sys

import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]


def load_i64(path, width):
    data = array.array("q")
    data.frombytes(path.read_bytes())
    return np.asarray(data, dtype=np.int64).reshape(-1, width)


def main():
    name = sys.argv[1]
    run = E / "runs" / name
    diag, linux = run / "diagnostics", run / "diagnostics/linux"
    enq = np.load(diag / "telemetry_frames_enqueued.npy")
    sent = np.load(diag / "telemetry_frames_sent.npy")
    body_enq = {int(s): int(t) for m, s, t, _, _ in enq if m == 8}
    body_sent = {int(s): (int(a), int(b), int(ok)) for m, s, a, b, ok in sent if m == 8}
    roles = {p.name.split("_")[0]: p.read_text() for p in linux.glob("*_cmdline.txt")}
    bridge = next(pid for pid, cmd in roles.items() if "foxy_bridge_node" in cmd and (linux / f"{pid}_offer.i64").exists())
    backend = next((pid for pid, cmd in roles.items() if "native_backend_entry.py" in cmd), None)
    offers = load_i64(linux / f"{bridge}_offer.i64", 3)
    takes = load_i64(linux / f"{bridge}_take.i64", 2)
    publish = load_i64(linux / f"{bridge}_publish.i64", 2)
    offers, takes, publish = offers[np.argsort(offers[:, 1], kind="stable")], takes[np.argsort(takes[:, 1], kind="stable")], \
        publish[np.argsort(publish[:, 0], kind="stable")]
    received = {int(s): int(t) for s, t, a in offers if a == 1}
    delivered = {int(s): int(t) for s, t in takes}
    clock = [json.loads(line) for line in open(run / "clock_samples.jsonl") if '"seq"' in line]
    accepted = [c for c in clock if c["accepted"]]
    received_mac = [c["received"] for c in accepted]

    def to_mac(linux_ns, near_mac):
        index = min(max(bisect.bisect_right(received_mac, near_mac) - 1, 0), len(accepted) - 1)
        return linux_ns + accepted[index]["filtered_offset_ns"]

    callbacks = [json.loads(line) for line in open(run / "backend_body_callbacks.jsonl")]
    backend_at = {int(c["stamp_ns"]): int(c["entered_ns"]) for c in callbacks}

    def stages(stamp):
        if stamp not in body_enq:
            return None
        e = body_enq[stamp]
        s0, s1, ok = body_sent.get(stamp, (None, None, 0))
        r = received.get(stamp)
        d = delivered.get(stamp)
        b = backend_at.get(stamp)
        rm = to_mac(r, e) if r is not None else None
        dm = to_mac(d, e) if d is not None else None
        bm = to_mac(b, e) if b is not None else None
        ms = lambda x, y: None if x is None or y is None else round((y - x) / 1e6, 1)
        return {"stamp": stamp, "queue_ms": ms(e, s0), "send_ms": ms(s0, s1), "transit_and_receipt_ms": ms(s1, rm),
                "bridge_ms": ms(rm, dm), "ros_ms": ms(dm, bm), "delivered": d is not None, "sent_ok": bool(ok)}

    all_stages = [stages(s) for s in sorted(body_enq)]
    all_stages = [x for x in all_stages if x is not None]

    def dist(key, only_delivered=False):
        values = np.array([x[key] for x in all_stages if x[key] is not None and (x["delivered"] or not only_delivered)])
        return {"n": int(len(values)), "median": float(np.median(values)), "p99": float(np.quantile(values, .99)),
                "max": float(values.max())} if len(values) else None

    gc = {}
    for pid in (bridge, backend):
        if pid and (linux / f"{pid}_gc.i64").exists():
            gc[pid] = load_i64(linux / f"{pid}_gc.i64", 5)
    gaps = []
    stamps_sorted = sorted(body_enq)
    for a, b in zip(callbacks, callbacks[1:]):
        if b["entered_ns"] - a["entered_ns"] <= 150_000_000:
            continue
        sa, sb = int(a["stamp_ns"]), int(b["stamp_ns"])
        inside = [s for s in stamps_sorted[bisect.bisect_left(stamps_sorted, sa):bisect.bisect_right(stamps_sorted, sb)]]
        lo, hi = a["entered_ns"], b["entered_ns"]
        window = publish[(publish[:, 0] < hi) & (publish[:, 0] + publish[:, 1] > lo)]
        pause = float(np.diff(np.concatenate(([lo], window[:, 0], [hi]))).max()) / 1e6
        blame, receive_spacing_ms = [], []
        for this, following in zip(inside, inside[1:]):
            if this in received and this not in delivered and following in received:
                spacing = received[following] - received[this]
                receive_spacing_ms.append(round(spacing / 1e6, 2))
                if spacing >= 15_000_000:
                    blame.append("bridge_timer")
                elif this in body_sent and following in body_sent and body_sent[following][0] - body_sent[this][0] < 15_000_000:
                    blame.append("worker_sender")
                else:
                    blame.append("transit_or_receipt")
        record = {"backend_gap_ms": round((hi - lo) / 1e6, 1), "poses": [stages(s) for s in inside],
                  "superseded_blame": {k: blame.count(k) for k in ("bridge_timer", "worker_sender", "transit_or_receipt")},
                  "superseded_receive_spacing_ms": receive_spacing_ms,
                  "bridge_longest_publish_callback_ms": round(float(window[:, 1].max()) / 1e6, 1) if len(window) else None,
                  "bridge_longest_pause_between_callbacks_ms": round(pause, 1)}
        for pid, events in gc.items():
            mask = (events[:, 0] < hi) & (events[:, 0] + events[:, 1] > lo)
            record[f"longest_collection_ms_{'bridge' if pid == bridge else 'backend'}"] = \
                round(float(events[mask, 1].max()) / 1e6, 1) if mask.any() else 0.0
        gaps.append(record)
    summary = {"run": name, "body_states": len(all_stages),
               "delivered": sum(x["delivered"] for x in all_stages),
               "stages_ms": {k: dist(k) for k in ("queue_ms", "send_ms", "transit_and_receipt_ms", "bridge_ms", "ros_ms")},
               "bridge_publish_callback_ms": {"median": float(np.median(publish[:, 1]) / 1e6),
                                              "max": float(publish[:, 1].max() / 1e6)},
               "collections": {("bridge" if pid == bridge else "backend"): {
                   "count": int(len(ev)), "max_ms": float(ev[:, 1].max() / 1e6) if len(ev) else 0.0,
                   "generation2_ms": [round(float(d) / 1e6, 1) for d in ev[ev[:, 2] == 2, 1]]} for pid, ev in gc.items()},
               "backend_gaps_over_150ms": gaps}
    (H / f"pipeline_{name}.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "backend_gaps_over_150ms"}, indent=1))
    for g in gaps:
        print({k: v for k, v in g.items() if k != "poses"}, [(p and (p["queue_ms"], p["transit_and_receipt_ms"], p["bridge_ms"], p["delivered"])) for p in g["poses"]])


if __name__ == "__main__":
    main()

"""Offline lead, not an implementation: how would one candidate rule change
SCAN's walkway support labels near the landing?

1. A Python copy of reactive_stair::precomputeEthStyleStepScores must first
   reproduce every native label in all_cells.csv (the header-built map).
2. Candidate: when a present navigation neighbour has no layer within the
   critical height, look at the same cell in the pinned surface evidence
   (raw_ground.f32, same 0.1 m lattice). If the evidence has a surface within
   the critical height there, skip that neighbour as ETH does for an absent
   measurement; otherwise it still makes the layer Unknown (possible drop).
"""
from pathlib import Path
import csv, json, math
import numpy as np

here = Path(__file__).resolve().parent
experiment = here.parents[2]
CRIT, STAIR, RES = 0.26, 0.04, 0.1
OFFS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]  # circleOffsets(0.15, 0.1)


def decode(path):
    g = np.fromfile(path, dtype="<f4").reshape(-1, 4)
    ok = np.isfinite(g).all(1) & (g[:, 3] <= 20.0)
    ox, oy = float(g[ok, 0].min()) - RES / 2, float(g[ok, 1].min()) - RES / 2
    cells = {}
    for x, y, z, _ in g[ok].astype(np.float64):
        cells.setdefault((math.floor((x - ox) / RES), math.floor((y - oy) / RES)), []).append(z - 0.03)
    return cells, ox, oy


def nearest(surfaces, target):
    best, selected, ambiguous = math.inf, -1, False
    for i, e in enumerate(surfaces):
        d = abs(e - target)
        if d + 1e-9 < best:
            best, selected, ambiguous = d, i, False
        elif abs(d - best) <= 1e-9:
            ambiguous = True
    return -1 if ambiguous or best > CRIT else selected


def score(cells, present_at_level):
    first = {}
    for c, layers in cells.items():
        out = []
        for e in layers:
            lo, hi, complete = math.inf, -math.inf, True
            for dx, dy in OFFS:
                n = cells.get((c[0] + dx, c[1] + dy))
                if n is None:
                    continue
                k = nearest(n, e)
                if k < 0:
                    if present_at_level((c[0] + dx, c[1] + dy), e):
                        continue
                    complete = False
                    break
                lo, hi = min(lo, n[k]), max(hi, n[k])
            out.append(hi - lo if complete else math.nan)
        first[c] = out
    labels = {}
    for c, layers in cells.items():
        out = []
        for li, e in enumerate(layers):
            if not math.isfinite(first[c][li]):
                out.append(0)
                continue
            complete, maximum, critical = True, 0.0, 0
            for dx, dy in OFFS:
                nc = (c[0] + dx, c[1] + dy)
                n = cells.get(nc)
                if n is None:
                    continue
                k = nearest(n, e)
                if k < 0:
                    if present_at_level(nc, e):
                        continue
                    complete = False
                    break
                f = first[nc][k]
                if not math.isfinite(f):
                    continue
                maximum = max(maximum, f)
                critical += f > CRIT
            if not complete:
                out.append(0)
                continue
            step = min(maximum, critical / 4 * maximum)
            s = 1.0 - step / CRIT if step < CRIT else 0.0
            f = first[c][li]
            out.append(3 if f >= CRIT or s <= 0.0 else (2 if f >= STAIR else 1))
        labels[c] = out
    return labels


nav, nox, noy = decode(experiment / "audits/2026-09-27_pct_precision/ground_precise.f32")
evidence, eox, eoy = decode(experiment / "audits/2026-09-27_dense_static_sampling/raw_ground.f32")
shift = (round((nox - eox) / RES), round((noy - eoy) / RES))
assert abs(nox - eox - shift[0] * RES) < 1e-6 and abs(noy - eoy - shift[1] * RES) < 1e-6
native = {}
for r in csv.DictReader((here / "all_cells.csv").open()):
    native.setdefault((int(r["ix"]), int(r["iy"])), {})[int(r["layer"])] = int(r["support"])
baseline = score(nav, lambda c, e: False)
mismatch = sum(1 for c, layers in baseline.items() for i, s in enumerate(layers) if native[c][i] != s)
total = sum(len(v) for v in baseline.values())


def evidence_level(c, e):
    s = evidence.get((c[0] + shift[0], c[1] + shift[1]))
    return s is not None and nearest(s, e) >= 0


candidate = score(nav, evidence_level)
changed = [(c, i, baseline[c][i], candidate[c][i]) for c in nav for i in range(len(nav[c])) if baseline[c][i] != candidate[c][i]]
box = lambda c: -5.3 <= nox + c[0] * RES <= -3.5 and -4.5 <= noy + c[1] * RES <= -2.3
walk = lambda c, i: 1.35 <= nav[c][i] <= 1.65
in_box = [x for x in changed if box(x[0]) and walk(x[0], x[1])]
remaining_unknown_box = sum(1 for c in nav if box(c) for i in range(len(nav[c])) if walk(c, i) and candidate[c][i] == 0)
report = {
    "replica_layers": total, "replica_mismatches_vs_native": mismatch,
    "candidate_changed_layers_whole_map": len(changed),
    "candidate_change_kinds_whole_map": {f"{a}->{b}": sum(1 for x in changed if (x[2], x[3]) == (a, b)) for a, b in sorted({(x[2], x[3]) for x in changed})},
    "landing_box_walkway_changed": len(in_box),
    "landing_box_walkway_unknown_after": remaining_unknown_box,
    "labels": {"0": "Unknown", "1": "Flat", "2": "Stair", "3": "Unsupported"},
    "status": "offline lead only; not a native build, replay or safety evaluation",
}
(here / "evidence_fallback_estimate.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))

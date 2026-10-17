"""Independent Python implementation of v34's rule (PLAN.md, "The rule"), for the fill contract's checker.

Written from PLAN.md's text, not from the C++ header:
- decode: as GridMap::decodeReactiveGround with the planner defaults (0.1 m cells, z - 0.03 m, finite records with
  cost <= 20; origin = minimum kept x and y - 0.05 m; layers in file order).
- a snapshot is usable evidence when it is valid (source, frame, finite stamp, positive resolution, finite origin,
  non-empty cells, every cell non-empty, every elevation finite), in the navigation's frame and at its resolution.
- for every evidence cell in (x, y) order and each of its layers in order: the target is the navigation cell that
  contains the evidence cell's centre. Skip when the target (with layers added earlier) has a layer within 0.12 m.
  Otherwise reject when any evidence cell whose square comes within 0.35 m of the candidate's square is a drop: it is
  absent, or it has no layer within 0.26 m of the level and some layer below level - 0.26 m. Else add.
"""
import math
from pathlib import Path

import numpy as np

TOLERANCE, STEP, GUARD = 0.12, 0.26, 0.35


class Snapshot:
    def __init__(self, cells, origin=(0.0, 0.0), resolution=0.1, frame="world"):
        self.cells = {k: list(v) for k, v in cells.items()}
        self.origin = origin
        self.resolution = resolution
        self.frame = frame

    def valid(self):
        return (math.isfinite(self.resolution) and self.resolution > 0 and all(map(math.isfinite, self.origin))
                and bool(self.cells) and all(v and all(math.isfinite(z) for z in v) for v in self.cells.values()))


def decode_f32(path):
    a = np.fromfile(Path(path), dtype="<f4").reshape(-1, 4)
    keep = np.isfinite(a).all(1) & (a[:, 3] <= 20.0)
    kept = a[keep]
    origin = (float(kept[:, 0].min()) - 0.05, float(kept[:, 1].min()) - 0.05)
    cells = {}
    for x, y, z, _ in kept:
        cells.setdefault((math.floor((float(x) - origin[0]) / 0.1), math.floor((float(y) - origin[1]) / 0.1)),
                         []).append(float(z) - 0.03)
    return Snapshot(cells, origin)


def guard_offsets(resolution):
    reach = math.ceil(GUARD / resolution) + 1
    out = []
    for dx in range(-reach, reach + 1):
        for dy in range(-reach, reach + 1):
            gx, gy = max(0, abs(dx) - 1) * resolution, max(0, abs(dy) - 1) * resolution
            if gx * gx + gy * gy <= GUARD * GUARD + 1e-12:
                out.append((dx, dy))
    return out


def fill(navigation, evidence):
    """Return (augmented cells, added list [(cell, z)], rejected count, evidence_used)."""
    out = {k: list(v) for k, v in navigation.cells.items()}
    usable = (evidence is not None and navigation.valid() and evidence.valid() and evidence.frame == navigation.frame
              and abs(evidence.resolution - navigation.resolution) <= 1e-9)
    if not usable:
        return out, [], 0, False
    res = navigation.resolution
    offsets = guard_offsets(res)

    def drop(cell, level):
        layers = evidence.cells.get(cell)
        if layers is None:
            return True
        if any(abs(z - level) <= STEP for z in layers):
            return False
        return any(z < level - STEP for z in layers)

    added, rejected = [], 0
    for (ex, ey) in sorted(evidence.cells):
        cx = evidence.origin[0] + (ex + 0.5) * res
        cy = evidence.origin[1] + (ey + 0.5) * res
        target = (math.floor((cx - navigation.origin[0]) / res), math.floor((cy - navigation.origin[1]) / res))
        for level in evidence.cells[(ex, ey)]:
            if any(abs(z - level) <= TOLERANCE for z in out.get(target, [])):
                continue
            if any(drop((ex + dx, ey + dy), level) for dx, dy in offsets):
                rejected += 1
                continue
            out.setdefault(target, []).append(level)
            added.append((target, level))
    return out, added, rejected, True

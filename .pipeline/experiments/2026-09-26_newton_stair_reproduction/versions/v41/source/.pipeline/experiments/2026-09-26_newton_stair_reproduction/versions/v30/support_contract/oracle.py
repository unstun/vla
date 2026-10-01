"""Independent Python statement of the step-score support rule, v29 and v30.

v29: a present neighbour with no unambiguous layer within the step capability
makes the layer Unknown. v30: that neighbour counts as measured ground when the
evidence cell under its centre has an unambiguous surface within the step
capability. The evidence height enters pass 1, and the neighbour is skipped in
pass 2. Evidence that is absent, empty, non-finite, in another frame or at
another resolution is ignored.

Labels: 0 Unknown, 1 Flat, 2 Stair, 3 Unsupported.
"""
import math

CRIT, STAIR_LABEL, RESOLUTION, CRITICAL_CELLS = 0.26, 0.04, 0.1, 4
OFFSETS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]  # circleOffsets(0.15, 0.1)


class Snapshot:
    def __init__(self, cells, origin=(0.0, 0.0), resolution=RESOLUTION, frame="world"):
        self.cells, self.origin, self.resolution, self.frame = cells, origin, resolution, frame

    def usable_as_evidence_for(self, nav):
        return (bool(self.cells) and self.frame == nav.frame and abs(self.resolution - nav.resolution) <= 1e-9
                and all(math.isfinite(e) for layers in self.cells.values() for e in layers)
                and all(math.isfinite(v) for v in self.origin))


def nearest(surfaces, target):
    best, selected, ambiguous = math.inf, -1, False
    for index, elevation in enumerate(surfaces):
        distance = abs(elevation - target)
        if distance + 1e-9 < best:
            best, selected, ambiguous = distance, index, False
        elif abs(distance - best) <= 1e-9:
            ambiguous = True
    return -1 if ambiguous or best > CRIT else selected


def evidence_height(evidence, nav, cell, elevation):
    if evidence is None:
        return None
    x = nav.origin[0] + (cell[0] + 0.5) * nav.resolution
    y = nav.origin[1] + (cell[1] + 0.5) * nav.resolution
    key = (math.floor((x - evidence.origin[0]) / evidence.resolution), math.floor((y - evidence.origin[1]) / evidence.resolution))
    surfaces = evidence.cells.get(key)
    if surfaces is None:
        return None
    k = nearest(surfaces, elevation)
    return None if k < 0 else surfaces[k]


def score(nav, evidence=None):
    """Return {cell: [(label, first_pass_height), ...]} for every navigation layer."""
    if evidence is not None and not evidence.usable_as_evidence_for(nav):
        evidence = None
    first = {}
    for cell, layers in nav.cells.items():
        values = []
        for elevation in layers:
            low, high, complete = math.inf, -math.inf, True
            for dx, dy in OFFSETS:
                neighbour = (cell[0] + dx, cell[1] + dy)
                surfaces = nav.cells.get(neighbour)
                if surfaces is None:
                    continue
                k = nearest(surfaces, elevation)
                height = surfaces[k] if k >= 0 else evidence_height(evidence, nav, neighbour, elevation)
                if height is None:
                    complete = False
                    break
                low, high = min(low, height), max(high, height)
            values.append(high - low if complete else math.nan)
        first[cell] = values
    labels = {}
    for cell, layers in nav.cells.items():
        out = []
        for index, elevation in enumerate(layers):
            f = first[cell][index]
            if not math.isfinite(f):
                out.append((0, f))
                continue
            complete, maximum, critical = True, 0.0, 0
            for dx, dy in OFFSETS:
                neighbour = (cell[0] + dx, cell[1] + dy)
                surfaces = nav.cells.get(neighbour)
                if surfaces is None:
                    continue
                k = nearest(surfaces, elevation)
                if k < 0:
                    if evidence_height(evidence, nav, neighbour, elevation) is not None:
                        continue
                    complete = False
                    break
                g = first[neighbour][k]
                if not math.isfinite(g):
                    continue
                maximum = max(maximum, g)
                critical += g > CRIT
            if not complete:
                out.append((0, f))
                continue
            step = min(maximum, critical / CRITICAL_CELLS * maximum)
            s = 1.0 - step / CRIT if step < CRIT else 0.0
            out.append((3 if f >= CRIT or s <= 0.0 else (2 if f >= STAIR_LABEL else 1), f))
        labels[cell] = out
    return labels


def decode_f32(path, z_offset=0.03, cost_limit=20.0, exclude=None):
    """Repeat GridMap::decodeReactiveGround for a pinned 16-byte x,y,z,cost file.

    `exclude(g)` may return a boolean mask of points to drop before decoding.
    """
    import numpy as np
    g = np.fromfile(path, dtype="<f4").reshape(-1, 4)
    if exclude is not None:
        g = g[~exclude(g)]
    ok = np.isfinite(g).all(1) & (g[:, 3] <= cost_limit)
    origin = (float(g[ok, 0].min()) - RESOLUTION / 2, float(g[ok, 1].min()) - RESOLUTION / 2)
    cells = {}
    for x, y, z, _ in g[ok].astype(np.float64):
        cells.setdefault((math.floor((x - origin[0]) / RESOLUTION), math.floor((y - origin[1]) / RESOLUTION)), []).append(z - z_offset)
    return Snapshot(cells, origin)

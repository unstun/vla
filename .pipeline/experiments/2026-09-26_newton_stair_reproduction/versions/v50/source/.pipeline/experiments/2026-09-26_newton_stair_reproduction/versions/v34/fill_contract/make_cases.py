"""Write cases.txt: synthetic cases for the v34 fill contract (PLAN.md, K2).

Every case is on the 0.1 m grid in frame "world". The floor is at 1.56 m. Unless a case says otherwise, the evidence
floor covers x 0..20, y 0..12, and a ring of solid cells (only a surface above, 3.12 m) surrounds it out to x -5..25,
y -5..17, so that no candidate meets the map's own edge. The navigation ground keeps the floor only in the band
x 0..5 ("trimmed" beyond it). Parameters: tolerance 0.12 m, step 0.26 m, guard radius 0.35 m.
The checker compares every output layer with oracle.py and asserts each case's designed expectation.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOOR, CEILING, LOWER = 1.56, 3.12, 0.06


def floor_cells(x0=0, x1=20, y0=0, y1=12, z=FLOOR):
    return [(x, y, z) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def solid_ring(x0=-5, x1=25, y0=-5, y1=17, inner=(0, 20, 0, 12)):
    return [(x, y, CEILING) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)
            if not (inner[0] <= x <= inner[1] and inner[2] <= y <= inner[3])]


BAND = floor_cells(0, 5)
EVIDENCE = floor_cells() + solid_ring()


def replace(cells, where, new):
    """Evidence with the cells in `where` replaced by the layers in `new` (a list of z, possibly empty)."""
    kept = [c for c in cells if (c[0], c[1]) not in where]
    return kept + [(x, y, z) for (x, y) in where for z in new]


HOLE = {(15, 6)}
CASES = {
    # Discriminating: the trimmed floor is added up to the solid ring.
    "wall_trim": ("normal", (0.0, 0.0), BAND, EVIDENCE),
    # An isolated wrong-height cell inside the band: the floor is added beside the kept wrong layer.
    "isolated_wrong_height": ("normal", (0.0, 0.0),
                              [c for c in floor_cells(0, 20) if (c[0], c[1]) != (6, 6)] + [(6, 6, 1.42)], EVIDENCE),
    # A drop (only a lower surface) at (15, 6): candidates within 0.35 m square to square are rejected.
    "drop_lower_level": ("normal", (0.0, 0.0), BAND, replace(EVIDENCE, HOLE, [LOWER])),
    # No surface at all at (15, 6): the same rejections.
    "drop_no_surface": ("normal", (0.0, 0.0), BAND, replace(EVIDENCE, HOLE, [])),
    # A cell with only a higher surface at (15, 6) is solid: nothing is rejected for it.
    "solid_inside": ("normal", (0.0, 0.0), BAND, replace(EVIDENCE, HOLE, [CEILING])),
    # A surface within the step (0.20 m below) at (15, 6) is floor for the guard.
    "step_within_capability": ("normal", (0.0, 0.0), BAND, replace(EVIDENCE, HOLE, [FLOOR - 0.20])),
    # A surface just beyond the step (0.27 m below) and nothing else: a drop.
    "step_beyond_capability": ("normal", (0.0, 0.0), BAND, replace(EVIDENCE, HOLE, [FLOOR - 0.27])),
    # Navigation layer 0.10 m from the evidence floor in the trimmed region: not added.
    "navigation_within_tolerance": ("normal", (0.0, 0.0), BAND + floor_cells(6, 20, z=FLOOR - 0.10), EVIDENCE),
    # Navigation layer 0.13 m away: added beside it.
    "navigation_beyond_tolerance": ("normal", (0.0, 0.0), BAND + floor_cells(6, 20, z=FLOOR - 0.13), EVIDENCE),
    # Two evidence layers 0.04 m apart in each trimmed cell: added once.
    "duplicate_candidates": ("normal", (0.0, 0.0), BAND, EVIDENCE + floor_cells(6, 20, z=FLOOR + 0.04)),
    # Evidence origin 0.07 m lower in x and y: each layer goes to the navigation cell containing its centre.
    "sub_cell_origin_offset": ("normal", (-0.07, -0.07), BAND, EVIDENCE),
    # Must leave the input unchanged (unusable evidence), in both builds.
    "no_evidence": ("none", (0.0, 0.0), BAND, []),
    "evidence_other_frame": ("frame_map", (0.0, 0.0), BAND, EVIDENCE),
    "evidence_other_resolution": ("resolution_0.2", (0.0, 0.0), BAND, EVIDENCE),
    "evidence_empty": ("empty", (0.0, 0.0), BAND, []),
    "evidence_non_finite": ("nan", (0.0, 0.0), BAND, EVIDENCE),
}
EXPECTATION = {
    "wall_trim": "adds",
    "isolated_wrong_height": "adds_at_6_6_keeps_wrong",
    "drop_lower_level": "rejects_near_hole",
    "drop_no_surface": "rejects_near_hole",
    "solid_inside": "adds_all_trimmed",
    "step_within_capability": "adds_all_trimmed",
    "step_beyond_capability": "rejects_near_hole",
    "navigation_within_tolerance": "adds_none_at_floor",
    "navigation_beyond_tolerance": "adds_beside",
    "duplicate_candidates": "adds_once",
    "sub_cell_origin_offset": "adds_shifted",
    "no_evidence": "unchanged",
    "evidence_other_frame": "unchanged",
    "evidence_other_resolution": "unchanged",
    "evidence_empty": "unchanged",
    "evidence_non_finite": "unchanged",
}

if __name__ == "__main__":
    lines = []
    for name, (mode, origin, nav, evidence) in CASES.items():
        lines += [f"case {name}", f"evidence_mode {mode}", f"evidence_origin {origin[0]!r} {origin[1]!r}"]
        lines += [f"N {x} {y} {z!r}" for x, y, z in nav]
        lines += [f"E {x} {y} {z!r}" for x, y, z in evidence]
        lines.append("end")
    (HERE / "cases.txt").write_text("\n".join(lines) + "\n")
    print(len(CASES), "cases")

"""Write cases.txt: synthetic step-score cases for the v30 support contract.

A 7 x 3 walkway band at 1.42 m (cells x 0..6, y 0..2) has one present column
beyond its +x edge (x = 7, y -1..3). In the navigation ground that column holds
only other floors (0.058 m, 3.118 m). The evidence differs per case. Every case
is scored in full, and the checker compares every label with oracle.py.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
BAND = [(x, y, 1.42) for x in range(7) for y in range(3)]
OTHER_FLOORS = [(7, y, z) for y in range(-1, 4) for z in (0.058, 3.118)]


def column(*levels):
    return [(7, y, z) for y in range(-1, 4) for z in (0.058, *levels, 3.118)]


CASES = {
    # Discriminating: v29 leaves the edge ring Unknown; v30 decides from evidence.
    "artifact_edge": ("normal", (0.0, 0.0), BAND + OTHER_FLOORS, BAND + column(1.42)),
    "evidence_step_up": ("normal", (0.0, 0.0), BAND + OTHER_FLOORS, BAND + column(1.62)),
    "evidence_step_mixed": ("normal", (0.0, 0.0), [c for c in BAND if c[:2] != (5, 1)] + [(5, 1, 1.32)] + OTHER_FLOORS,
                            BAND + column(1.62)),
    "sub_cell_origin_offset": ("normal", (-0.03, -0.03), BAND + OTHER_FLOORS, BAND + column(1.42)),
    # Must stay a possible drop in both.
    "real_drop": ("normal", (0.0, 0.0), BAND + OTHER_FLOORS, BAND + column()),
    "evidence_absent_there": ("normal", (0.0, 0.0), BAND + OTHER_FLOORS, BAND),
    "ambiguous_evidence": ("normal", (0.0, 0.0), BAND + OTHER_FLOORS, BAND + column(1.32, 1.52)),
    "evidence_beyond_capability": ("normal", (0.0, 0.0), BAND + OTHER_FLOORS, BAND + column(1.70)),
    # Must be identical in both.
    "absent_neighbours": ("normal", (0.0, 0.0), BAND, BAND + column(1.42)),
    "navigation_has_level": ("normal", (0.0, 0.0), BAND + column(1.42), BAND + column(1.62)),
    "no_evidence": ("none", (0.0, 0.0), BAND + OTHER_FLOORS, []),
    "evidence_other_frame": ("frame_map", (0.0, 0.0), BAND + OTHER_FLOORS, BAND + column(1.42)),
    "evidence_other_resolution": ("resolution_0.2", (0.0, 0.0), BAND + OTHER_FLOORS, BAND + column(1.42)),
    "evidence_empty": ("empty", (0.0, 0.0), BAND + OTHER_FLOORS, []),
    "evidence_non_finite": ("nan", (0.0, 0.0), BAND + OTHER_FLOORS, BAND + column(1.42)),
}
DISCRIMINATING = ["artifact_edge", "evidence_step_up", "evidence_step_mixed", "sub_cell_origin_offset"]

lines = []
for name, (mode, origin, nav, evidence) in CASES.items():
    lines += [f"case {name}", f"evidence_mode {mode}", f"evidence_origin {origin[0]!r} {origin[1]!r}"]
    lines += [f"N {x} {y} {z!r}" for x, y, z in nav]
    lines += [f"E {x} {y} {z!r}" for x, y, z in evidence]
    lines.append("end")
(HERE / "cases.txt").write_text("\n".join(lines) + "\n")
print(len(CASES), "cases")

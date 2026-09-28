"""Check the header-built support map against every [SUPPORT] line the native
probes printed (cell, layer elevation, status, known, first-pass height)."""
from pathlib import Path
import csv, json, re

here = Path(__file__).resolve().parent
audit = here.parent
table = {}
for r in csv.DictReader((here / "all_cells.csv").open()):
    table.setdefault((int(r["ix"]), int(r["iy"])), []).append(r)
checked, mismatches = 0, []
logs = ["landing/baseline.log", "landing/probe.log", "onset/baseline.log", "onset/probe.log"]
for log in logs:
    cell = None
    for line in (audit / log).open(errors="replace"):
        m = re.match(r"\[DETAIL\] (\S+) .* cell=(-?\d+),(-?\d+) ", line)
        if m:
            cell = (int(m.group(2)), int(m.group(3)))
            continue
        m = re.match(r"\[SUPPORT\] (\S+) z=(\S+) status=(\d+) known=(\d+) first_height=(\S+) score=(\S+)", line)
        if not (m and cell):
            continue
        z, status, known, first = float(m.group(2)), int(m.group(3)), int(m.group(4)), m.group(5)
        match = [r for r in table.get(cell, []) if abs(float(r["elevation"]) - z) < 1e-9]
        ok = len(match) == 1 and int(match[0]["support"]) == status and int(match[0]["known"]) == known
        if ok and first != "nan":
            ok = abs(float(match[0]["first_pass_height"]) - float(first)) < 1e-9
        checked += 1
        if not ok:
            mismatches.append({"log": log, "cell": cell, "z": z, "status": status, "known": known})
cells = len(table)
report = {"native_support_lines_checked": checked, "mismatches": mismatches, "map_cells": cells,
          "live_terrain_cells": 27278, "logs": logs}
(here / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "logs"}))

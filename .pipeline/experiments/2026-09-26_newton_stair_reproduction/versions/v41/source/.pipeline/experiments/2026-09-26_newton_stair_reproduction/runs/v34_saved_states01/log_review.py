"""Normalised log comparison against v31: python3 log_review.py <v31_run_dir> <v34_run_dir> <output.json>.

Adapted from runs/v31_native_regression03/log_review.py (v30's normalisation plus v31's rule for input_refresh lines):
- timestamps, timings, stamps and clock values are masked, and [DEBUG lines are dropped;
- in both runs, an input_refresh line that applied nothing (sensor_poses, clouds and body_poses all 0, and fsm_odom 0
  or -1) and whose four ages are all non-negative is dropped (v31's rule; both runs now carry these lines);
- v34 adds one rule for its own instrumentation: its evidence_floor_fill lines (one per ground or evidence message,
  with the added and rejected counts) are dropped from v34's logs and recorded per log in
  <output stem>_evidence_floor_fill.json. They change no planner state; the counts are checked by the fill contract.
For every log in both runs whose normalised text differs, it records the difference counts by message kind and the
first differing lines of each kind.
"""
from pathlib import Path
import collections, difflib, json, re, sys

REFRESH = re.compile(r"input_refresh site=(\w+) sensor_poses=(\d+) clouds=(\d+) body_poses=(\d+) fsm_odom=(-?\d+) "
                     r"cloud_age=([-0-9.]+)->([-0-9.]+) body_age=([-0-9.]+)->([-0-9.]+)")
FILL = re.compile(r"evidence_floor_fill evidence_used=(\d) navigation_layers=(\d+) added=(\d+) drop_rejected=(\d+)")


def norm(path, dropped, fills):
    out = []
    for line in path.read_text(errors="replace").splitlines():
        m = REFRESH.search(line)
        if m and all(int(x) == 0 for x in m.groups()[1:4]) and int(m.group(5)) <= 0 and \
                all(float(x) >= 0.0 for x in m.groups()[5:9]):
            dropped[m.group(1)] += 1
            continue
        f = FILL.search(line)
        if f:
            fills.append([int(v) for v in f.groups()])
            continue
        line = re.sub(r"\[\d+\.\d+\]", "[T]", line)
        line = re.sub(r"time\(ms\)=[0-9.e+-]+", "time", line)
        line = re.sub(r"total_t\(ms\)=[0-9.e+-]+", "total", line)
        line = re.sub(r"wall_ms=[0-9.]+", "wall", line)
        line = re.sub(r"total time:.*$", "total time", line)
        line = re.sub(r"stamp=[0-9.]+", "stamp", line)
        line = re.sub(r"now=[0-9.]+", "now", line)
        if line.startswith("[DEBUG"):
            continue
        out.append(line)
    return out


old_dir, new_dir, output = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
summary, fill_lines = {}, {}
for new in sorted(new_dir.rglob("*.log")):
    relative = new.relative_to(new_dir)
    if "build" in relative.parts[0]:
        continue
    old = old_dir / relative
    if not old.exists():
        continue
    fills_old, fills_new = [], []
    x = norm(old, collections.Counter(), fills_old)
    y = norm(new, collections.Counter(), fills_new)
    assert not fills_old, (str(relative), "v31 has no evidence_floor_fill lines")
    if fills_new:
        fill_lines[str(relative)] = fills_new
    if x == y:
        continue
    kinds, samples = collections.Counter(), collections.defaultdict(list)
    for line in difflib.unified_diff(x, y, lineterm="", n=0):
        if line.startswith(("---", "+++", "@@")):
            continue
        match = re.search(r"\]: (\w+)", line) or re.search(r"^[+-](\S+)", line)
        key = f"{line[0]}{match.group(1) if match else line[:40]}"
        kinds[key] += 1
        if len(samples[key]) < 3:
            samples[key].append(line[:300])
    summary[str(relative)] = {"counts": dict(kinds), "samples": dict(samples)}
output.write_text(json.dumps(summary, indent=2) + "\n")
output.with_name(output.stem + "_evidence_floor_fill.json").write_text(json.dumps(fill_lines, indent=2) + "\n")
print(json.dumps({name: item["counts"] for name, item in summary.items()}, indent=1))

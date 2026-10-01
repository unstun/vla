"""Normalised log comparison against v30: python3 log_review.py <v30_run_dir> <v31_run_dir> <output.json>.

Uses v30's normalisation (the same as v29's log_differences_vs_v28.json):
- timestamps, timings, stamps and clock values are masked;
- [DEBUG lines are dropped.
v31 adds one rule for its own instrumentation: an input_refresh line that applied nothing
(sensor_poses, clouds and body_poses all 0, and fsm_odom 0 or -1) and whose four ages are all
non-negative is dropped. v31 logs every call at its four inner sites, and these lines change no planner
state. A line that applied anything, or that carries a negative age (an input stamped ahead of the
clock, which a freshness test reads as stale), is kept, so it shows as a difference that needs an
explanation (round-2 review NB4). The dropped lines are counted per log in
<output stem>_input_refresh.json.
For every log in both runs whose normalised text differs, it records the difference counts by message
kind and the first differing lines of each kind.
"""
from pathlib import Path
import collections, difflib, json, re, sys

REFRESH = re.compile(r"input_refresh site=(\w+) sensor_poses=(\d+) clouds=(\d+) body_poses=(\d+) fsm_odom=(-?\d+) "
                     r"cloud_age=([-0-9.]+)->([-0-9.]+) body_age=([-0-9.]+)->([-0-9.]+)")


def norm(path, dropped):
    out = []
    for line in path.read_text(errors="replace").splitlines():
        m = REFRESH.search(line)
        if m and all(int(x) == 0 for x in m.groups()[1:4]) and int(m.group(5)) <= 0 and \
                all(float(x) >= 0.0 for x in m.groups()[5:9]):
            dropped[m.group(1)] += 1
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
summary, refresh_lines = {}, {}
for new in sorted(new_dir.rglob("*.log")):
    relative = new.relative_to(new_dir)
    if "build" in relative.parts[0]:
        continue
    old = old_dir / relative
    if not old.exists():
        continue
    dropped_old, dropped_new = collections.Counter(), collections.Counter()
    x, y = norm(old, dropped_old), norm(new, dropped_new)
    assert not dropped_old, (str(relative), "v30 has no input_refresh lines")
    kept = sum(1 for line in new.read_text(errors="replace").splitlines() if REFRESH.search(line)) - sum(dropped_new.values())
    if dropped_new or kept:
        refresh_lines[str(relative)] = {"dropped_applied_nothing": dict(dropped_new), "kept_applied_something": kept}
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
output.with_name(output.stem + "_input_refresh.json").write_text(json.dumps(refresh_lines, indent=2) + "\n")
print(json.dumps({name: item["counts"] for name, item in summary.items()}, indent=1))

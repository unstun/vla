"""Normalised log comparison against v29: python3 log_review.py <v29_run_dir> <v30_run_dir> <output.json>.

Uses the same normalisation as v29's log_differences_vs_v28.json:
- timestamps, timings, stamps and clock values are masked;
- [DEBUG lines are dropped.
For every log in both runs whose normalised text differs, it records the
difference counts by message kind and the first differing lines of each kind.
"""
from pathlib import Path
import collections, difflib, json, re, sys


def norm(path):
    out = []
    for line in path.read_text(errors="replace").splitlines():
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
summary = {}
for new in sorted(new_dir.rglob("*.log")):
    relative = new.relative_to(new_dir)
    if "build" in relative.parts[0]:
        continue
    old = old_dir / relative
    if not old.exists():
        continue
    x, y = norm(old), norm(new)
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
print(json.dumps({name: item["counts"] for name, item in summary.items()}, indent=1))

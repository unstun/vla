"""Diagnostic counterfactuals: the stopped state with only the final body z changed.

Scans, paired sensor poses, route, spline and every other input byte are copied
unchanged from ../stopped/inputs; the recorded body z is 0.35168790817260742.
"""
from pathlib import Path
import hashlib, json, shutil

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "stopped/inputs"
Z_VALUES = [0.35168790817260742, 0.353, 0.354, 0.3545, 0.3549, 0.3551, 0.3555, 0.356]
records = {}
for z in Z_VALUES:
    name = f"z_{z:.5f}".replace(".", "p")
    out = HERE / name / "inputs"
    shutil.copytree(SOURCE, out)
    fields = (SOURCE / "final_body.txt").read_text().split()
    fields[2] = format(z, ".17g")
    (out / "final_body.txt").write_text(" ".join(fields) + "\n")
    changed = [p.name for p in sorted(out.iterdir()) if p.is_file() and
               hashlib.sha256(p.read_bytes()).hexdigest() != hashlib.sha256((SOURCE / p.name).read_bytes()).hexdigest()]
    assert changed == ([] if z == Z_VALUES[0] else ["final_body.txt"]), changed
    records[name] = {"final_body_z": z, "changed_files": changed}
(HERE / "variants.json").write_text(json.dumps(records, indent=2) + "\n")
print(json.dumps(records))

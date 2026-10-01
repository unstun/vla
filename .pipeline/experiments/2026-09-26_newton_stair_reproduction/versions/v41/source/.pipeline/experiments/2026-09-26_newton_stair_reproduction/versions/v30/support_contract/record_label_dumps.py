"""Record the local-only full-map label dumps: python3 record_label_dumps.py -> label_dump_sha256.json.

freeze.py leaves every map_labels.csv out of the snapshot (about 4 MB each).
This tracked record keeps their SHA-256, size, rows and label counts, so the
7,873-layer evidence stays checkable, and says how to regenerate them.
"""
from collections import Counter
from pathlib import Path
import csv, hashlib, json

HERE = Path(__file__).resolve().parent
NAMES = {"0": "Unknown", "1": "Flat", "2": "Stair", "3": "Unsupported"}
records = {}
for path in sorted(HERE.rglob("map_labels.csv")):
    data = path.read_bytes()
    rows = list(csv.DictReader(path.open()))
    records[str(path.relative_to(HERE))] = {
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "layers": len(rows),
        "labels": {NAMES[k]: v for k, v in sorted(Counter(r["support"] for r in rows).items())}}
(HERE / "label_dump_sha256.json").write_text(json.dumps({
    "files": records,
    "storage": "Local only, at these paths under versions/v30/support_contract/ (git-ignored by path).",
    "regeneration": "From versions/v30/support_contract: python3 run.py <label> <native tree> in the pinned image "
                    "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb (red_v29: "
                    "runtime/scan61_sensor_column_v29, green_v30: runtime/scan62_support_evidence_v30). "
                    "step_contract writes map_labels.csv from the pinned grounds; check.py compares it with oracle.py.",
    "superseded": "attempt01/ holds the first passing run, kept unchanged; the strengthened contract replaced it."},
    indent=2) + "\n")
print(json.dumps({name: {k: v[k] for k in ("sha256", "layers", "labels")} for name, v in records.items()}, indent=1))

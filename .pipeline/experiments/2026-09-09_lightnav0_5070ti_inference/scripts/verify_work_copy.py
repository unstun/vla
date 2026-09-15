"""Compare an execution work copy against the pristine upstream file manifest.

Usage: verify_work_copy.py <upstream_file_manifest.json> <work_dir> <report.json>
Reports mismatched, missing and extra files. Paths under ignored prefixes (.git, virtual
environments, caches, docs/assets which are deliberately not shipped) are listed separately.
"""
import hashlib
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text())
work = Path(sys.argv[2]).resolve()
report_path = Path(sys.argv[3])
IGNORED_PREFIXES = (".git/", ".venv/", "mujoco_demo/.venv/", "__pycache__", "docs/assets/",
                    "src/lightnav.egg-info/", ".pytest_cache/", ".ruff_cache/", "uv.lock", "mujoco_demo/uv.lock")


def ignored(rel: str) -> bool:
    return any(rel.startswith(p) or f"/{p}" in rel for p in IGNORED_PREFIXES)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


expected = {f["path"]: f for f in manifest["files"]}
present = {}
for p in work.rglob("*"):
    if p.is_file():
        rel = p.relative_to(work).as_posix()
        present[rel] = p
matched, mismatched, missing, extra, skipped_expected, skipped_present = [], [], [], [], [], []
for rel, entry in expected.items():
    if ignored(rel):
        skipped_expected.append(rel)
        continue
    p = present.get(rel)
    if p is None:
        missing.append(rel)
        continue
    if p.stat().st_size != entry["bytes"] or sha256_of(p) != entry["sha256"]:
        mismatched.append(rel)
    else:
        matched.append(rel)
for rel in present:
    if rel not in expected:
        (skipped_present if ignored(rel) else extra).append(rel)
report = {"commit": manifest.get("commit"), "work_dir": str(work), "matched": len(matched),
          "mismatched": sorted(mismatched), "missing": sorted(missing), "extra": sorted(extra),
          "ignored_expected_count": len(skipped_expected), "ignored_present_count": len(skipped_present),
          "pass": not mismatched and not missing and not extra}
report_path.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ("matched", "pass")}, ), "mismatched", len(mismatched),
      "missing", len(missing), "extra", len(extra))
sys.exit(0 if report["pass"] else 1)

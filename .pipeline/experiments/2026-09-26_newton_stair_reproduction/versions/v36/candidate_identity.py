"""Identify the exact implementation and contract presented for local review."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
EXCLUDED = {"source", "tests", "history", "parent_source", "reviews", "__pycache__"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_identity():
    selected = {}
    for path in HERE.rglob("*"):
        relative = path.relative_to(HERE)
        if (not path.is_file() or path.is_symlink() or
            any(part in EXCLUDED or part.startswith("build_evidence") for part in relative.parts) or
            path.name in {"RESULTS.md", "manifest.json", "quality.json", "review_identity.json", "LOCAL_ONLY_BYTES.json"}):
            continue
        selected[str(path.relative_to(ROOT))] = sha(path)
    return {
        "native_source_sha256": json.loads((HERE / "native_source_sha256.json").read_text()),
        "contract_sha256": sha(HERE / "navigation_contract.json"),
        "changes_sha256": sha(HERE / "changes.patch"),
        "source_sha256": dict(sorted(selected.items())),
    }


if __name__ == "__main__":
    (HERE / "review_identity.json").write_text(json.dumps(candidate_identity(), indent=2) + "\n")
    print("Recorded exact candidate identity for two independent review axes.")

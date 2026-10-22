"""Read-only verification of the locally retained v242-v290 evidence."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify():
    errors = []
    retained = 0
    for line in (HERE / "local-files.jsonl").read_text().splitlines():
        row = json.loads(line)
        path = ROOT / row["path"]
        if not path.is_file():
            errors.append({"path": row["path"], "error": "missing retained file"})
        elif path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            errors.append({"path": row["path"], "error": "retained bytes differ"})
        retained += 1

    receipt = json.loads((HERE / "source-verification.json").read_text())
    sources = 0
    for row in receipt["checks"]:
        path = ROOT / row["manifest"]
        if not path.is_file() or sha256(path) != row["manifest_sha256"]:
            errors.append({"path": row["manifest"], "error": "frozen manifest differs"})
            continue
        manifest = json.loads(path.read_text())
        for relative, expected in manifest.get("source_files", {}).items():
            candidates = [path.parent / relative, path.parent / "source" / relative]
            location = manifest.get("snapshot_locations", {}).get(relative)
            if isinstance(location, str):
                candidates.insert(0, path.parent / location)
            if not any(p.is_file() and sha256(p) == expected for p in candidates):
                errors.append({"manifest": row["manifest"], "source": relative,
                               "error": "no matching source or snapshot"})
            sources += 1
    result = {"passed": not errors, "retained_files_checked": retained,
              "source_manifests_checked": len(receipt["checks"]),
              "source_entries_checked": sources, "errors": errors,
              "remote_checked": False, "physics_steps": 0}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(verify())

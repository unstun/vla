"""Verify returned v50 evidence and immutable v48/v49/v50 identities."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
VERSION = HERE.parent
BASE = VERSION.parents[1]
ROOT = BASE.parents[2]


def sha(path):
    with path.open("rb") as f:
        digest = hashlib.sha256()
        for block in iter(lambda: f.read(8*1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(entries, prefix=ROOT):
    failures = []
    byte_count = 0
    for name, value in entries.items():
        expected = value if isinstance(value, str) else value["sha256"]
        path = prefix / name
        if not path.is_file():
            failures.append({"path": str(path), "reason": "missing"})
        elif sha(path) != expected:
            failures.append({"path": str(path), "reason": "sha256 mismatch"})
        else:
            byte_count += path.stat().st_size
    return dict(files=len(entries), verified_bytes=byte_count, failures=failures, passed=not failures)


def main():
    manifest = json.loads((VERSION / "manifest.json").read_text())
    parent = json.loads((BASE / "versions/v48/manifest.json").read_text())
    assert manifest["parent"] == manifest["native_source_parent"] == "v48"
    assert sha(BASE / "versions/v48/manifest.json") == manifest["parent_manifest_sha256"]
    results = {
        "v50_current_sources": check(manifest["source_files"]),
        "v50_frozen_snapshot": check(manifest["source_files"], VERSION / "source"),
        "v48_current_sources": check(parent["source_files"]),
    }
    preserved = json.loads((VERSION / "v49_preservation.json").read_text())
    # Preservation keys are paths relative to the v49 version directory.
    results["v49_unchanged"] = check(preserved["version_directory_files"], BASE / "versions/v49")
    for relative in ["build_evidence", "tests/attempt01", "tests/attempt02", "profiles/attempt01", "profiles/attempt02", "trials/attempt01", "trials/attempt02"]:
        path = VERSION / relative / "return_manifest.json"
        if path.exists():
            results[relative] = check(json.loads(path.read_text()))
    path = BASE / "versions/v48/trials/attempt02/return_manifest.json"
    results["v48_control_trial02"] = check(json.loads(path.read_text()))
    result = dict(passed=all(r["passed"] for r in results.values()), checks=results,
                  claim="File identity and complete local return only; does not promote failed physical acceptance.")
    (HERE / "evidence_verification.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__": main()

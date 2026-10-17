#!/usr/bin/env python3
"""Compare fresh Drive object metadata with the original archive receipts."""

import collections
import hashlib
import json
from pathlib import Path
import time


base = Path("/Users/sun/tongbu/study/phdproject/machine-dog/artifacts/2026-09-12_dqn_google_drive_offload")
out = Path(__file__).parent / "data_audit"
prefix = "gdrive-phd:phdproject-archive/2026-09-12/dqn/"
current = json.loads((out / "cloud_listing.json").read_text())
by_path = collections.defaultdict(list)
for item in current:
    by_path[item["Path"]].append(item)
expected = {}


def add(folder, item, source, extra_hashes=None):
    assert folder.startswith(prefix), folder
    name = item.get("name", item.get("Name"))
    size = item.get("size", item.get("bytes", item.get("Size")))
    hashes = dict(item.get("hashes", item.get("Hashes", {})))
    if item.get("md5"):
        hashes["md5"] = item["md5"]
    hashes.update(extra_hashes or {})
    key = folder.removeprefix(prefix).strip("/") + "/" + name
    row = {"path": key, "size": size, "hashes": hashes,
           "id": item.get("id", item.get("ID")), "receipt": str(source)}
    if key in expected:
        assert expected[key]["size"] == size and expected[key]["hashes"] == hashes
    expected[key] = row


for receipt in (base / "full_tree").glob("*/verified-receipt.json"):
    data = json.loads(receipt.read_text())
    manifest = json.loads(receipt.with_name("manifest.json").read_text())
    shards = {s["name"]: s for s in manifest["shards"]}
    for item in data["objects"]:
        extra = {}
        if item["name"] in shards:
            extra["sha256"] = shards[item["name"]]["sha256"]
        else:
            local = receipt.parent / item["name"]
            if local.is_file():
                extra["sha256"] = hashlib.sha256(local.read_bytes()).hexdigest()
        add(data["remote"], item, receipt, extra)

for receipt in (base / "dqn9_first_batch").rglob("remote-verification.json"):
    data = json.loads(receipt.read_text())
    source = json.loads(receipt.with_name("source-manifest.json").read_text())
    folder = source["remote"].rsplit("/", 1)[0]
    for item in data["files"]:
        add(folder, item, receipt)

for receipt in (base / "dqn9_first_batch").rglob("remote-shards-receipt.json"):
    data = json.loads(receipt.read_text())
    for item in data["remote_files"]:
        add(data["remote_directory"], item, receipt)

results = []
groups = collections.defaultdict(lambda: {"expected": 0, "passed": 0, "bytes": 0})
for path, old in sorted(expected.items()):
    candidates = by_path.get(path, [])
    same_id = [x for x in candidates if x.get("ID") == old["id"]]
    candidates = same_id or candidates
    status = "missing" if not candidates else "ambiguous" if len(candidates) != 1 else "passed"
    mismatch = []
    if len(candidates) == 1:
        now = candidates[0]
        if now["Size"] != old["size"]:
            mismatch.append("size")
        if not old["hashes"]:
            mismatch.append("no_historical_hash")
        for name, value in old["hashes"].items():
            if now.get("Hashes", {}).get(name) != value:
                mismatch.append(name)
        if mismatch:
            status = "mismatch"
    group = "/".join(path.split("/")[:2])
    groups[group]["expected"] += 1
    if status == "passed":
        groups[group]["passed"] += 1
        groups[group]["bytes"] += old["size"]
    results.append({**old, "status": status, "mismatches": mismatch})

report = {
    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "remote_root": prefix.rstrip("/"), "current_object_count": len(current),
    "current_bytes": sum(x["Size"] for x in current), "receipt_object_count": len(expected),
    "passed": sum(x["status"] == "passed" for x in results),
    "failures": [x for x in results if x["status"] != "passed"],
    "objects_without_local_receipt": sorted(set(by_path) - set(expected)),
    "duplicate_paths": [name for name, objects in by_path.items() if len(objects) > 1],
    "groups": groups,
    "claim_boundary": "Current provider-reported object sizes and all recorded hashes matched where marked passed. This is a complete receipt comparison, not a full archive download/decompression test, nor proof that the old filesystem's DQN8 files are covered.",
}
(out / "CLOUD_REVALIDATED.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
(out / "cloud_object_checks.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False, indent=2))

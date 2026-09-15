"""Download official pinned NaVILA weights and verify upstream LFS hashes."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from huggingface_hub import snapshot_download

REPO = "a8cheng/navila-llama3-8b-8f"
REVISION = "b2294e96581454468d6b94f38201f4f965ef48b7"
root = Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=True)
evidence = root / "setup"
evidence.mkdir(exist_ok=True)
url = f"https://huggingface.co/api/models/{REPO}/tree/{REVISION}?recursive=true"
with urllib.request.urlopen(url, timeout=60) as response:
    tree = json.load(response)
(evidence / "upstream_model_tree.json").write_text(json.dumps(tree, indent=2))
target = root / "models" / "navila-llama3-8b-8f"
snapshot_download(REPO, revision=REVISION, local_dir=target, max_workers=4)
manifest = []
for item in tree:
    if item["type"] != "file":
        continue
    path = target / item["path"]
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    sha = digest.hexdigest()
    expected = item.get("lfs", {}).get("oid")
    if expected and sha != expected:
        raise RuntimeError(f"LFS SHA-256 mismatch: {path}")
    if path.stat().st_size != item["size"]:
        raise RuntimeError(f"Size mismatch: {path}")
    manifest.append({"path": item["path"], "size": path.stat().st_size,
                     "sha256": sha, "upstream_lfs_sha256": expected})
    print(f"verified {item['path']} {sha}", flush=True)
(evidence / "original_weight_manifest.json").write_text(json.dumps(
    {"repo": REPO, "revision": REVISION, "files": manifest}, indent=2))
print("DOWNLOAD_AND_HASH_VERIFICATION_COMPLETE", flush=True)

"""Acquire a pinned CPU ASR model with upstream LFS/Git blob verification."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "scripts"))
from download_assets import download_in_ranges, sha256


def main():
    upstream = json.loads((ROOT / "manifests/asr_upstream.json").read_text())
    records = []
    for file in upstream["files"]:
        name = file["rfilename"]
        url = f"https://huggingface.co/{upstream['repo_id']}/resolve/{upstream['revision']}/{name}"
        target = ROOT / "models" / name
        if not target.exists():
            if "lfs" in file:
                partial = target.with_suffix(target.suffix + ".partial")
                download_in_ranges({"url": url, "bytes": file["size"], "destination": name}, partial, workers=4)
                if sha256(partial) != file["lfs"]["sha256"]:
                    raise RuntimeError("ASR LFS hash mismatch")
                partial.rename(target)
            else:
                target.write_bytes(urllib.request.urlopen(url, timeout=45).read())
        data = target.read_bytes()
        if len(data) != file["size"]:
            raise RuntimeError(f"ASR asset size mismatch: {name}")
        if "lfs" in file:
            assert sha256(target) == file["lfs"]["sha256"]
        elif hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != file["blobId"]:
            raise RuntimeError(f"ASR Git blob mismatch: {name}")
        records.append({"path": name, "bytes": len(data), "sha256": sha256(target), "url": url})
        print("ASR_ASSET_VERIFIED", name, len(data), flush=True)
    (ROOT / "manifests/asr_assets.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()

"""Capture an exact official PyPI wheel compatible with the pinned Foxy image."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
OUT = HERE / "dependencies/scipy_1_8_1_cp38"
NAME = "scipy-1.8.1-cp38-cp38-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
METADATA_URL = "https://pypi.org/pypi/scipy/1.8.1/json"


def main():
    if (OUT / "manifest.json").exists():
        raise FileExistsError("Dependency already captured")
    OUT.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(METADATA_URL, timeout=30) as response:
        metadata = json.load(response)
    wheel = next(row for row in metadata["urls"] if row["filename"] == NAME)
    with urllib.request.urlopen(wheel["url"], timeout=90) as response:
        payload = response.read()
    if len(payload) != wheel["size"] or hashlib.sha256(payload).hexdigest() != wheel["digests"]["sha256"]:
        raise ValueError("Official wheel identity mismatch")
    path = OUT / NAME
    path.write_bytes(payload)
    # Capture license/requirements without importing Linux binaries on macOS.
    with zipfile.ZipFile(path) as archive:
        package_metadata = archive.read("scipy-1.8.1.dist-info/METADATA").decode()
        (OUT / "METADATA.txt").write_text(package_metadata)
        for name in archive.namelist():
            if name.startswith("scipy-1.8.1.dist-info/") and "LICENSE" in name:
                (OUT / Path(name).name).write_bytes(archive.read(name))
        file_hashes = {name: hashlib.sha256(archive.read(name)).hexdigest()
                       for name in archive.namelist() if not name.endswith("/")}
    manifest = {"source": METADATA_URL, "project": "scipy", "version": "1.8.1",
                "filename": NAME, "url": wheel["url"], "bytes": len(payload),
                "sha256": wheel["digests"]["sha256"], "requires_python": metadata["info"]["requires_python"],
                "requires_dist": metadata["info"]["requires_dist"], "wheel_members_sha256": file_hashes,
                "target": "Pinned Foxy CPython 3.8.10 x86_64, existing NumPy 1.17.4; no NumPy replacement",
                "runtime_verified": False}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "wheel_members_sha256"}, indent=2))


if __name__ == "__main__":
    main()

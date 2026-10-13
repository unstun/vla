"""Same SciPy1.8.1 as the archive, with the official CPython3.10 Linux wheel."""
import hashlib
import importlib.util
import json
from pathlib import Path
import urllib.request
import zipfile

BASE = Path(__file__).resolve().parents[1]
OLD = BASE.parents[2] / ".pipeline/experiments/2026-09-23_scan_reactive_stair/runtime_integration/runs/walk_scan28_height030_right_v1"
filename = "scipy-1.8.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
metadata_url = "https://pypi.org/pypi/scipy/1.8.1/json"
metadata = json.load(urllib.request.urlopen(metadata_url, timeout=20))
file = next(f for f in metadata["urls"] if f["filename"] == filename)
folder = BASE / "runtime/foreground_wheels"
folder.mkdir(parents=True, exist_ok=True)
wheel = folder / filename
if wheel.exists():
    raise FileExistsError(wheel)
data = urllib.request.urlopen(file["url"], timeout=90).read()
if hashlib.sha256(data).hexdigest() != file["digests"]["sha256"] or len(data) != file["size"]:
    raise ValueError("Official wheel integrity mismatch")
wheel.write_bytes(data)
with zipfile.ZipFile(wheel) as archive:
    hashes = {p: hashlib.sha256(archive.read(p)).hexdigest() for p in archive.namelist() if not p.endswith("/")}
manifest = {"source": metadata_url, "repository": "https://github.com/scipy/scipy/tree/v1.8.1",
    "version": "1.8.1", "filename": filename, "url": file["url"], "bytes": len(data),
    "sha256": file["digests"]["sha256"], "requires_python": metadata["info"]["requires_python"],
    "requires_dist": metadata["info"]["requires_dist"], "wheel_members_sha256": hashes,
    "change": "Only CPython ABI wheel changes from archived cp38 to cp310; same SciPy version, existing NumPy retained"}
manifest_path = BASE / "setup/foreground_dependency.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
source = OLD / "inputs/static_background/unpack_foreground_dependency.py"
spec = importlib.util.spec_from_file_location("original_dependency_unpack", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
receipt = module.unpack(wheel, manifest_path, BASE / "runtime/foreground_py310")
receipt.update(unpacker_source=str(source), unpacker_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(BASE / "setup/foreground_unpack.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))

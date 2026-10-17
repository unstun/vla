"""Pin official PyZMQ wheels for the local Mac and the existing Linux runtime."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

BASE = Path(__file__).resolve().parents[1]
url = "https://pypi.org/pypi/pyzmq/26.4.0/json"
metadata = json.load(urllib.request.urlopen(url, timeout=20))
filenames = {
    "macos": "pyzmq-26.4.0-cp312-cp312-macosx_10_15_universal2.whl",
    "linux": "pyzmq-26.4.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
}
records = []
folder = BASE / "runtime/zmq_wheels"
folder.mkdir(parents=True, exist_ok=True)
for platform, filename in filenames.items():
    item = next(f for f in metadata["urls"] if f["filename"] == filename)
    destination = BASE / "runtime" / ("zmq_" + platform)
    destination.mkdir(exist_ok=False)
    data = urllib.request.urlopen(item["url"], timeout=60).read()
    if len(data) != item["size"] or hashlib.sha256(data).hexdigest() != item["digests"]["sha256"]:
        raise ValueError("Official PyZMQ wheel identity mismatch")
    wheel = folder / filename
    wheel.write_bytes(data)
    members = {}
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Invalid wheel path")
            payload = archive.read(name)
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            members[name] = hashlib.sha256(payload).hexdigest()
    records.append({"platform": platform, "filename": filename, "url": item["url"],
                    "sha256": item["digests"]["sha256"], "bytes": len(data), "members_sha256": members})
record = {"repository": "https://github.com/zeromq/pyzmq", "commit": "b273c0915abd45003dc6378a3c6e8750d39a34c0",
          "version": "26.4.0", "pypi_metadata": url, "wheels": records,
          "contract": "Standard ZeroMQ REQ/REP complete-message transport; JSON bytes and original applied-snapshot schema",
          "scope": "No global package installation; wheels unpacked only under this experiment runtime"}
(BASE / "setup/zmq_dependency.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"platforms": list(filenames), "total_bytes": sum(r["bytes"] for r in records)}))

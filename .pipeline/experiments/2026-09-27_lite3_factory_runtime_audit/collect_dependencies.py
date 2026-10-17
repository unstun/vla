"""Read and pin selected runtime dependencies; never execute robot software."""

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
HOST = "ysc@192.168.2.1"
FILES = [
    "/home/ysc/jy_exe/lib/libtorch/arm/lib/libtorch_cpu.so",
    "/home/ysc/jy_exe/lib/libtorch/arm/lib/libc10.so",
    "/home/ysc/jy_exe/lib/log_lib/lib/liblog4cplus.so.2",
    "/home/ysc/rl_deploy/lib/onnxruntime/lib/libonnxruntime.so.1",
    "/lib/aarch64-linux-gnu/libgomp.so.1",
]
OPTIONS = [
    "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
    "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=5",
    "-o", "ServerAliveCountMax=2",
]

remote = """import hashlib,json,pathlib,datetime
paths = %s
for value in paths:
    path=pathlib.Path(value)
    digest=hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            digest.update(block)
    print(json.dumps({'remote_path':value,'resolved_remote_path':str(path.resolve()),
          'bytes':path.stat().st_size,'sha256':digest.hexdigest(),
          'acquired_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}),flush=True)
""" % repr(FILES)
identity = subprocess.run(
    ["ssh", *OPTIONS, HOST, "nice -n 15 python3 -"], input=remote,
    text=True, capture_output=True, check=True, timeout=30,
)
records = [json.loads(line) for line in identity.stdout.splitlines()]
destination = ROOT / "private_snapshot" / "deps"
destination.mkdir(parents=True, exist_ok=True)
for record in records:
    target = destination / Path(record["remote_path"]).name
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != record["sha256"]:
            raise RuntimeError("Refusing to replace different dependency bytes")
    else:
        subprocess.run(
            ["scp", "-q", *OPTIONS, HOST + ":" + record["remote_path"], str(target)],
            check=True, timeout=120,
        )
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != record["sha256"]:
        raise RuntimeError("Transferred dependency hash mismatch: " + target.name)
    target.chmod(0o600)
    record["local_path"] = str(target.relative_to(ROOT))
    print("Verified", target.name, record["bytes"], flush=True)
(ROOT / "dependency_manifest.json").write_text(
    json.dumps({"source_host": HOST, "files": records}, indent=2) + "\n"
)

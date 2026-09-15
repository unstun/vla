"""Resume one verified artifact over bounded SSH reads on an unstable link."""

import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(sys.argv[1]).resolve()
    run_id = sys.argv[2]
    name = sys.argv[3]
    run = root / "runs" / run_id
    record = next(r for r in json.loads((run / "artifact_sha256.json").read_text()) if r["path"] == name)
    target = run / name
    partial = target.with_name(target.name + ".partial")
    if target.exists() and target.stat().st_size == record["bytes"]:
        if hashlib.sha256(target.read_bytes()).hexdigest() == record["sha256"]:
            print("ARTIFACT_ALREADY_VERIFIED", name)
            return
        raise RuntimeError("Existing full-size artifact failed its checksum")
    if target.exists() and not partial.exists():
        os.replace(target, partial)
    position = partial.stat().st_size if partial.exists() else 0
    remote = "/home/sun/vla_exec/2026-09-08_tic_vla_dynanav_5070ti/runs/" + run_id + "/" + name
    while position < record["bytes"]:
        size = min(8 * 1024 * 1024, record["bytes"] - position)
        code = f"import sys; f=open({remote!r},'rb'); f.seek({position}); sys.stdout.buffer.write(f.read({size}))"
        command = ["ssh", "-S", "/tmp/vla5070ti-01a080e1.sock", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "gpu5070ti", shlex.join(["python3", "-c", code])]
        for attempt in range(3):
            result = subprocess.run(command, capture_output=True, timeout=60)
            if result.returncode == 0 and len(result.stdout) == size:
                break
            print("SSH_RANGE_RETRY", position, result.returncode, len(result.stdout), flush=True)
        else:
            raise RuntimeError("SSH range could not be received completely")
        with partial.open("ab") as output:
            output.write(result.stdout)
        position += size
        print("SSH_ARTIFACT_PROGRESS", name, position, "/", record["bytes"], flush=True)
    if hashlib.sha256(partial.read_bytes()).hexdigest() != record["sha256"]:
        raise RuntimeError("Final artifact checksum mismatch")
    os.replace(partial, target)
    print("ARTIFACT_VERIFIED", name, record["sha256"], flush=True)


if __name__ == "__main__":
    main()

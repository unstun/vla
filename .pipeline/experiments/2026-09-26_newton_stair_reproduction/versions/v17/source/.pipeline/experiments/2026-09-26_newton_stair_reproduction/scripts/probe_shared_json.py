"""Minimize the observed cross-OS JSON read failure; no robot or planner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[2]
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"


def reader(out):
    failures, reads = [], 0
    until = time.monotonic() + 15
    while time.monotonic() < until:
        if (out / "done.json").exists():
            break
        try:
            raw = (out / "sample.json").read_text()
            value = json.loads(raw)
            if hashlib.sha256(value["payload"].encode()).hexdigest() != value["sha256"]:
                raise ValueError("valid JSON but payload checksum mismatch")
            reads += 1
        except FileNotFoundError:
            pass
        except Exception as error:
            item = {"type": type(error).__name__, "message": str(error), "errno": getattr(error, "errno", None)}
            if hasattr(error, "doc"):
                item["doc"] = error.doc
            if len(failures) < 10:
                failures.append(item)
        time.sleep(.001)
    (out / "read_result.json").write_text(json.dumps({"valid_reads": reads, "failures": failures}, indent=2) + "\n")


def writer(out, overlap):
    name = "vla-newton-json-" + out.name.replace("_", "-")
    command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--network=none",
        "--name", name, "--memory=256m", "--cpus=1"]
    if overlap:
        command += ["-v", str(PROJECT) + ":" + str(PROJECT) + ":ro"]
    else:
        command += ["-v", str(BASE / "scripts") + ":" + str(BASE / "scripts") + ":ro"]
    command += ["-v", str(out) + ":" + str(out) + ":rw", "--entrypoint", "/usr/bin/python3", IMAGE,
                str(Path(__file__).resolve()), "--reader", str(out)]
    (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (out / "container.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            for sequence in range(500):
                payload = "abcd" * (20 + sequence % 200)
                value = {"sequence": sequence, "payload": payload, "sha256": hashlib.sha256(payload.encode()).hexdigest()}
                tmp = out / "sample.tmp"
                tmp.write_text(json.dumps(value) + "\n")
                tmp.replace(out / "sample.json")
                time.sleep(.01)
            (out / "done.json").write_text("{}\n")
            process.wait(timeout=10)
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)
    result = json.loads((out / "read_result.json").read_text())
    print(json.dumps({"overlapping_mount": overlap, "valid_reads": result["valid_reads"],
                      "failures": [{k:v for k,v in x.items() if k != "doc"} for x in result["failures"]]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reader", type=Path)
    parser.add_argument("--overlap", action="store_true")
    args = parser.parse_args()
    if args.reader:
        reader(args.reader)
    else:
        writer(Path(os.environ["NEWTON_RUN_DIR"]), args.overlap)

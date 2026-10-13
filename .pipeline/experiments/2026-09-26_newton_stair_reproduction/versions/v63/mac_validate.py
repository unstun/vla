"""Build/check the v63 source using the cached local Docker engine only.

Every attempt is append-only. Temporary build products remain in the owned
container, removed on completion/failure; only compact evidence returns.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
NATIVE = BASE / "runtime/scan82_optimizer_failure_v63"
PARENT = BASE / "runtime/scan81_retry_epoch_v62"
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"
DOCKER = "/Users/sun/.local/bin/docker"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root):
    expected = json.loads((root / "source_sha256.json").read_text())
    assert all(sha(root / name) == digest for name, digest in expected.items())
    return expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    assert str(BASE.parents[2]) == "/Users/sun/tongbu/study/phdproject/vla"
    assert shutil.disk_usage(HERE).free > 12 * 1024**3
    parent_manifest = verify(PARENT)
    candidate_manifest = verify(NATIVE)
    out = HERE / "mac_tests" / f"attempt{args.attempt:02d}"
    out.mkdir(parents=True, exist_ok=False)
    owned_name = f"vla-v63-mac-validation-{args.attempt:02d}"
    prefix = [DOCKER, "--context", "desktop-linux"]
    context = subprocess.run(prefix + ["context", "inspect", "desktop-linux"],
        capture_output=True, text=True, timeout=20, check=True)
    context_data = json.loads(context.stdout)
    assert context_data[0]["Endpoints"]["docker"]["Host"] == "unix:///Users/sun/.docker/run/docker.sock"
    subprocess.run(prefix + ["image", "inspect", IMAGE], capture_output=True,
        text=True, timeout=20, check=True)
    # Save the executed script and fixture bytes before starting the container.
    input_files = [HERE / "mac_inside.sh", HERE / "mac_validate.py",
                   HERE / "building_planner.yaml", HERE / "controller.yaml"]
    input_files += sorted(p for p in (HERE / "contract").iterdir() if p.is_file())
    snapshot = out / "executed_source"
    snapshot.mkdir()
    for path in input_files:
        destination = snapshot / path.relative_to(HERE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    native_delta = out / "executed_native_delta"
    native_delta.mkdir()
    for name, digest in candidate_manifest.items():
        if digest != parent_manifest[name]:
            destination = native_delta / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(NATIVE / name, destination)
    shutil.copyfile(NATIVE / "source_sha256.json", native_delta / "source_sha256.json")
    request = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "host": "Mac local desktop-linux Docker engine", "gpu5070ti_used": False,
        "image": IMAGE, "cpu_limit": 3, "memory_limit": "6g", "deadline_s": 2400,
        "parent_manifest_sha256": sha(PARENT / "source_sha256.json"),
        "candidate_manifest_sha256": sha(NATIVE / "source_sha256.json"),
        "recorded_fixture_manifest_sha256": sha(BASE / "versions/v36/recorded_input_manifest.json"),
        "input_sha256": {str(p.relative_to(HERE)): sha(p) for p in input_files},
        "claim_boundary": "Native build and component contracts; no full simulation or 30 Hz claim",
        "recorded_gates_pending_inputs": ["startup_refresh", "freshness", "physical_native"],
    }
    command = prefix + ["run", "--rm", "--pull=never", "--platform=linux/amd64",
        "--network=none", "--name", owned_name, "--memory=6g", "--cpus=3",
        "-e", "CMAKE_BUILD_PARALLEL_LEVEL=2", "-e", "MAKEFLAGS=-j2",
        "-e", "ROS_LOCALHOST_ONLY=1", "-e", "RCUTILS_COLORIZED_OUTPUT=0",
        "-v", str(PARENT) + ":/parent:ro", "-v", str(NATIVE) + ":/candidate:ro",
        "-v", str(BASE) + ":/archive:ro", "-v", str(HERE) + ":/version:ro",
        "-v", str(out) + ":/attempt:rw", "--entrypoint", "/bin/bash", IMAGE,
        "/attempt/executed_source/mac_inside.sh"]
    request["command"] = command
    (out / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    result = {"passed": False}
    begin = time.monotonic()
    try:
        with (out / "driver.log").open("w") as log:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                     timeout=request["deadline_s"])
        result["exit_code"] = process.returncode
        result["parent_unchanged"] = verify(PARENT) == parent_manifest
        result["candidate_unchanged"] = verify(NATIVE) == candidate_manifest
        result["test_inputs_unchanged"] = all(sha(HERE / p) == h
            for p, h in request["input_sha256"].items())
        result["passed"] = (process.returncode == 0 and result["parent_unchanged"]
            and result["candidate_unchanged"] and result["test_inputs_unchanged"])
    except subprocess.TimeoutExpired:
        result["timed_out"] = True
    finally:
        cleanup = subprocess.run(prefix + ["rm", "-f", owned_name],
            capture_output=True, text=True, timeout=20)
        result["cleanup"] = {"exit_code": cleanup.returncode,
            "stdout": cleanup.stdout.strip(), "stderr": cleanup.stderr.strip()}
        absent = subprocess.run(prefix + ["container", "inspect", owned_name],
            capture_output=True, text=True, timeout=20)
        result["owned_container_absent"] = (absent.returncode != 0 and
            "No such container" in absent.stderr)
        result["wall_s"] = time.monotonic() - begin
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        evidence = {str(p.relative_to(out)): {"sha256": sha(p), "bytes": p.stat().st_size}
                    for p in out.rglob("*") if p.is_file()}
        (out / "return_manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

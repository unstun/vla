#!/usr/bin/env python3
"""Hash-sync, bound, and collect one isolated RTX probe on gpu5070ti."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BRIDGE = ROOT / "references/upstream/2026-09-16_lite3_isaac_harness_backend/source/machine-dog-nav/integration/lite3_sim_bridge"
ASSETS = ROOT / "references/upstream/2026-09-24_isaac_official_police_human"
CANDIDATE = HERE.parent / "isaac_candidate"
CACHE = HERE.parent / "official_human_cache"
SSH = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "gpu5070ti"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stage", choices=("import", "sensing"), required=True)
    parser.add_argument("--enable-extension", action="store_true")
    parser.add_argument("--lifecycle-result", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", args.run_id):
        raise ValueError("invalid run id")
    if args.stage == "sensing":
        if args.lifecycle_result is None:
            raise ValueError("sensing requires a passing --lifecycle-result")
        lifecycle = json.loads(args.lifecycle_result.read_text())
        if lifecycle.get("stage") != "import" or lifecycle.get("passed") is not True or lifecycle.get("gpu_cleanup_pass") is not True:
            raise ValueError("RTX lifecycle gate has not passed")
    output = HERE / "runs" / args.run_id
    output.mkdir(parents=True, exist_ok=False)
    remote = "/home/sun/vla_exec/2026-09-26_rtx_stair_video/" + args.run_id
    history = []

    def run(label, command, timeout=90, input_text=None):
        started = time.monotonic()
        try:
            proc = subprocess.run(command, input=input_text, capture_output=True,
                                  text=True, timeout=timeout)
            stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
            stdout = stdout.decode(errors="replace") if isinstance(stdout, bytes) else stdout
            stderr = stderr.decode(errors="replace") if isinstance(stderr, bytes) else stderr
            rc = 124
        (output / (label + ".log")).write_text(stdout + stderr)
        history.append({"label": label, "command": command, "exit_code": rc,
                        "wall_seconds": time.monotonic() - started})
        write(output / "commands.json", history)
        print(label, rc, flush=True)
        return subprocess.CompletedProcess(command, rc, stdout, stderr)

    preflight = run("preflight", SSH + ["nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits"])
    if preflight.returncode or preflight.stdout.strip():
        raise RuntimeError("GPU occupied or preflight unavailable")
    source = output / "source"
    source.mkdir()
    for path in BRIDGE.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            dest = source / "bridge" / path.relative_to(BRIDGE)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
    mappings = {"candidate/official_building_human.py": CANDIDATE / "official_building_human.py",
                "assets/male_adult_police_04.usd": ASSETS / "male_adult_police_04.usd"}
    for path in (ASSETS / "textures").glob("*.png"):
        mappings["assets/textures/" + path.name] = path
    for name in ("official_human_retarget_cache.npz", "official_human_retarget_cache.json"):
        mappings["cache/" + name] = CACHE / name
    for path in HERE.glob("*.py"):
        mappings["probe/" + path.name] = path
    for rel, path in mappings.items():
        dest = source / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    expected = {p.relative_to(source).as_posix(): digest(p)
                for p in sorted(source.rglob("*")) if p.is_file()}
    write(output / "source_sha256.json", expected)
    setup = "test ! -e " + shlex.quote(remote) + " && mkdir -p " + shlex.quote(remote + "/outputs")
    if run("mkdir", SSH + [setup]).returncode:
        raise RuntimeError("remote directory is not fresh")
    if run("sync_source", ["rsync", "-a", str(source) + "/", "gpu5070ti:" + remote + "/source/"], 180).returncode:
        raise RuntimeError("source transfer failed")
    gate = ("import hashlib,json\nfrom pathlib import Path\n"
            f"root=Path({remote + '/source'!r})\ne=json.loads({json.dumps(expected)!r})\n"
            "bad=[n for n,h in e.items() if not (root/n).is_file() or hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]\n"
            "print(json.dumps({'files':len(e),'mismatches':bad}));raise SystemExit(bool(bad))\n")
    if run("source_gate_before", SSH + ["python3 -"], input_text=gate).returncode:
        raise RuntimeError("source gate failed")
    if args.stage == "import":
        limit = 150
        argv = ["python", "-u", remote + "/source/probe/probe_lifecycle.py", "--output", remote + "/outputs/lifecycle.json"]
        if args.enable_extension:
            argv.append("--enable-extension")
    else:
        limit = 450
        argv = ["python", "-u", remote + "/source/probe/probe_animated_human.py",
                "--asset-root", remote + "/source/assets", "--cache-dir", remote + "/source/cache",
                "--output", remote + "/outputs"]
    command = " && ".join([
        "source /home/sun/miniconda3/etc/profile.d/conda.sh", "conda activate isaaclab",
        "export PYTHONPATH=" + shlex.quote(remote + "/source/bridge:" + remote + "/source/candidate"),
        "export PYTHONDONTWRITEBYTECODE=1",
        f"timeout --signal=TERM --kill-after=15 {limit} " + shlex.join(argv),
    ])
    probe = run("probe", SSH + [command], limit + 45)
    after = run("source_gate_after", SSH + ["python3 -"], input_text=gate)
    artifact_script = ("import hashlib,json\nfrom pathlib import Path\n"
                       f"r=Path({remote + '/outputs'!r})\n"
                       "print(json.dumps({p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(r.rglob('*')) if p.is_file()}))\n")
    hashes = run("remote_artifact_hashes", SSH + ["python3 -"], input_text=artifact_script)
    returned = run("sync_outputs", ["rsync", "-a", "gpu5070ti:" + remote + "/outputs/", str(output / "outputs") + "/"], 180)
    gpu_after = run("gpu_after", SSH + ["nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader"])
    remote_hashes = json.loads(hashes.stdout) if hashes.returncode == 0 else {}
    mismatches = [n for n, h in remote_hashes.items()
                  if not (output / "outputs" / n).is_file() or digest(output / "outputs" / n) != h]
    proof = output / "outputs" / ("lifecycle.json" if args.stage == "import" else "result.json")
    result = json.loads(proof.read_text()) if proof.is_file() else {}
    behavior_pass = (result.get("state") == "teardown_completed" and result.get("module_import_completed") is True
                     if args.stage == "import" else result.get("passed") is True)
    cleanup_pass = gpu_after.returncode == 0 and not gpu_after.stdout.strip()
    teardown_path = output / "outputs/teardown.json"
    teardown_pass = (args.stage == "import" or (teardown_path.is_file()
                     and json.loads(teardown_path.read_text()).get("state") == "teardown_completed"))
    verdict = {"passed": bool(probe.returncode == 0 and after.returncode == 0 and returned.returncode == 0
                               and hashes.returncode == 0 and remote_hashes and not mismatches and behavior_pass
                               and cleanup_pass and teardown_pass),
               "stage": args.stage, "probe_exit_code": probe.returncode,
               "source_matches_before_after": after.returncode == 0,
               "artifact_hashes": remote_hashes, "artifact_mismatches": mismatches,
               "gpu_cleanup_pass": cleanup_pass, "teardown_pass": teardown_pass,
               "remote_root": remote, "behavior_result": result,
               "claim": "isolated RTX sensor gate only; no robot, ROS or stair episode"}
    write(output / "execution_result.json", verdict)
    print(json.dumps({k: verdict[k] for k in ("passed", "stage", "probe_exit_code", "gpu_cleanup_pass")}), flush=True)
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Hash-sync and execute one bounded, no-robot official-mesh Isaac probe."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BRIDGE = ROOT / "references/upstream/2026-09-16_lite3_isaac_harness_backend/source/machine-dog-nav/integration/lite3_sim_bridge"
ASSETS = ROOT / "references/upstream/2026-09-24_isaac_official_police_human"
CACHE = HERE.parent / "official_human_cache"
SSH = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "gpu5070ti"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="first_hit_v1")
    args = parser.parse_args()
    if not args.run_id.replace("_", "").isalnum():
        raise ValueError("invalid run id")
    output = HERE / args.run_id
    output.mkdir(exist_ok=False)
    source_snapshot = output / "source"
    source_snapshot.mkdir()
    for name in ("official_building_human.py", "smoke_official_mesh_two_poses.py",
                 "first_hit_sha256.txt", "execute_official_first_hit.py"):
        shutil.copy2(HERE / name, source_snapshot / name)
    remote = "/home/sun/vla_exec/2026-09-23_scan_reactive_stair/official_mesh_" + args.run_id
    commands = []

    def run(label, command, timeout=60, input_text=None):
        start = time.monotonic()
        proc = subprocess.run(command, input=input_text, capture_output=True,
                              text=True, timeout=timeout)
        (output / (label + ".log")).write_text(proc.stdout + proc.stderr)
        commands.append({"label": label, "command": command, "exit_code": proc.returncode,
                         "elapsed_s": time.monotonic() - start})
        (output / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        print(label, proc.returncode, flush=True)
        return proc

    preflight = run("preflight", SSH + ["nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits"])
    if preflight.returncode or preflight.stdout.strip():
        raise RuntimeError("GPU is not free or preflight failed")
    mkdir = run("mkdir", SSH + ["test ! -e " + shlex.quote(remote) + " && mkdir -p " +
                                " ".join(shlex.quote(remote + "/" + part)
                                         for part in ("bridge", "candidate", "assets/textures", "cache", "logs", "results"))])
    if mkdir.returncode:
        raise RuntimeError("fresh remote directory gate failed")

    mappings = {}
    for path in BRIDGE.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            mappings["bridge/" + path.relative_to(BRIDGE).as_posix()] = path
    for name in ("official_building_human.py", "smoke_official_mesh_two_poses.py", "first_hit_sha256.txt"):
        mappings["candidate/" + name] = HERE / name
    mappings["assets/male_adult_police_04.usd"] = ASSETS / "male_adult_police_04.usd"
    for path in (ASSETS / "textures").glob("*.png"):
        mappings["assets/textures/" + path.name] = path
    for name in ("official_human_retarget_cache.npz", "official_human_retarget_cache.json"):
        mappings["cache/" + name] = CACHE / name
    expected = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in sorted(mappings.items())}
    (output / "source_sha256.json").write_text(json.dumps(expected, indent=2) + "\n")
    sync_sets = [
        ("sync_bridge", ["rsync", "-a", "--exclude=__pycache__", "--exclude=*.pyc", str(BRIDGE) + "/", "gpu5070ti:" + remote + "/bridge/"]),
        ("sync_candidate", ["rsync", "-a", *[str(HERE / name) for name in ("official_building_human.py", "smoke_official_mesh_two_poses.py", "first_hit_sha256.txt")], "gpu5070ti:" + remote + "/candidate/"]),
        ("sync_usd", ["rsync", "-a", str(ASSETS / "male_adult_police_04.usd"), "gpu5070ti:" + remote + "/assets/"]),
        ("sync_textures", ["rsync", "-a", str(ASSETS / "textures") + "/", "gpu5070ti:" + remote + "/assets/textures/"]),
        ("sync_cache", ["rsync", "-a", str(CACHE / "official_human_retarget_cache.npz"), str(CACHE / "official_human_retarget_cache.json"), "gpu5070ti:" + remote + "/cache/"]),
    ]
    for label, command in sync_sets:
        if run(label, command, timeout=120).returncode:
            raise RuntimeError(label + " failed")
    gate = (
        "import hashlib,json\nfrom pathlib import Path\n"
        f"root=Path({remote!r})\nexpected=json.loads({json.dumps(expected)!r})\n"
        "bad=[name for name,value in expected.items() if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=value]\n"
        "print(json.dumps({'files':len(expected),'mismatches':bad}))\nraise SystemExit(bool(bad))\n"
    )
    if run("source_gate_before", SSH + ["python3 -"], input_text=gate).returncode:
        raise RuntimeError("source sync gate failed")
    command = " && ".join((
        "source /home/sun/miniconda3/etc/profile.d/conda.sh",
        "conda activate isaaclab",
        "export PYTHONPATH=" + shlex.quote(remote + "/bridge:" + remote + "/candidate"),
        "export PYTHONDONTWRITEBYTECODE=1",
        "timeout --kill-after=15 300 python " + shlex.quote(remote + "/candidate/smoke_official_mesh_two_poses.py") +
        " --asset-root " + shlex.quote(remote + "/assets") +
        " --cache-dir " + shlex.quote(remote + "/cache") +
        " --output " + shlex.quote(remote + "/results/" + args.run_id),
    ))
    probe = run("smoke", SSH + [command], timeout=340)
    after = run("source_gate_after", SSH + ["python3 -"], input_text=gate)
    returned = run("sync_result", ["rsync", "-a", "gpu5070ti:" + remote + "/results/" + args.run_id + "/", str(output) + "/"], timeout=60)
    result_path = output / "result.json"
    result = json.loads(result_path.read_text()) if result_path.is_file() else {}
    verdict = {"passed": probe.returncode == 0 and after.returncode == 0 and returned.returncode == 0 and result.get("passed") is True,
               "probe_exit_code": probe.returncode, "source_gate_after_passed": after.returncode == 0,
               "remote_root": remote, "local_result": str(result_path),
               "claim": "No-robot official USD mesh LiDAR first-hit smoke only"}
    (output / "execution_result.json").write_text(json.dumps(verdict, indent=2) + "\n")
    print(json.dumps(verdict), flush=True)
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

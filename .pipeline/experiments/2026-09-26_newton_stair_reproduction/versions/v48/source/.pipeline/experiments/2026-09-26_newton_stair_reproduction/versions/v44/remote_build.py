"""Bounded native build on the execution copy, never on the Mac."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
NATIVE = BASE / "runtime/scan69_shared_attempt_cache_v44"
PARENT = BASE / "runtime/scan68_raw_contributor_cache_v39"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    assert str(ROOT) == "/home/sun/vla_exec/vla", "Build only on gpu5070ti execution copy"
    manifest = json.loads((NATIVE / "source_sha256.json").read_text())
    assert all(sha(NATIVE / name) == expected for name, expected in manifest.items())
    out = HERE / ("build_evidence" if args.attempt==1 else f"build_evidence_retry{args.attempt:02d}")
    assert not out.exists()
    for name in ("build", "install"):
        if not (NATIVE / name).exists():
            shutil.copytree(PARENT / name, NATIVE / name, symlinks=True)
    workspace = NATIVE
    if args.attempt > 1:
        # The shared bounded builder refuses a completed workspace. Preserve
        # that result and build each revised unfrozen candidate in a fresh one.
        workspace = NATIVE / f"build_attempt_{args.attempt:02d}"
        workspace.mkdir()
        for name in ("src", "build", "install"):
            shutil.copytree(NATIVE/name, workspace/name, symlinks=True)
        shutil.copyfile(NATIVE/"source_sha256.json", workspace/"source_sha256.json")
    spec = importlib.util.spec_from_file_location("bounded_build", BASE / "setup/build_scan_local.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.WORKSPACE = workspace
    builder.NAME = "vla-build-scan69-shared-attempt-v44"
    builder.main()
    if workspace != NATIVE:
        (NATIVE/"install").rename(NATIVE/f"install_before_build_{args.attempt:02d}")
        shutil.copytree(workspace/"install", NATIVE/"install", symlinks=True)
        for name in ("build_result.json", "build_request.json", "build.log", "build_inside.sh",
                     "install_sha256.json", "package_versions.txt"):
            shutil.copyfile(workspace/name, NATIVE/name)
    out.mkdir()
    for name in ("build_result.json", "build_request.json", "build.log", "build_inside.sh",
                 "install_sha256.json", "package_versions.txt", "source_sha256.json"):
        shutil.copyfile(NATIVE / name, out / name)
    records = {str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size}
               for p in out.iterdir() if p.is_file()}
    (out / "return_manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    print((out / "build_result.json").read_text())


if __name__ == "__main__":
    main()

"""Compile and test the local v35 source copy on the authorized gpu5070ti host."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan65_evidence_floor_v34"
NEW = BASE / "runtime/scan66_periodic_replan_v35"
OUT = HERE / "remote5070ti"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root):
    manifest = json.loads((root / "source_sha256.json").read_text())
    assert all(sha(root / name) == digest for name, digest in manifest.items())
    return manifest


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, default=3, choices=range(3, 10))
    args = parser.parse_args()
    if args.attempt != 3:
        OUT = HERE / f"remote5070ti_retry{args.attempt:02d}"
    OUT.mkdir()
    before = verify(NEW)
    parent = verify(OLD)
    assert before == json.loads((HERE / "native_source_sha256.json").read_text())
    assert json.loads((OLD / "build_result.json").read_text())["passed"]
    # Only the execution copy gets these caches. Frozen v34 is read, not edited.
    build_reused = (NEW / "build_result.json").exists()
    if build_reused:
        assert json.loads((NEW / "build_result.json").read_text())["passed"]
    else:
        for name in ("build", "install"):
            shutil.copytree(OLD / name, NEW / name, symlinks=True)
        spec = importlib.util.spec_from_file_location("bounded_build", BASE / "setup/build_scan_local.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        builder.WORKSPACE = NEW
        builder.NAME = "vla-build-scan66-periodic-replan-v35"
        builder.main()
    for name in ("build_result.json", "build_request.json", "build.log", "build_inside.sh",
                 "install_sha256.json", "package_versions.txt", "source_sha256.json"):
        shutil.copyfile(NEW / name, OUT / name)
    with (OUT / "contract_execution.log").open("w") as log:
        contract = subprocess.run([sys.executable, str(HERE / "contract/run.py"), "--attempt", str(args.attempt)],
                                  stdout=log, stderr=subprocess.STDOUT, timeout=1900)
    result = {"host": "gpu5070ti", "recorded_utc": datetime.now(timezone.utc).isoformat(),
              "local_source_of_truth": "/Users/sun/tongbu/study/phdproject/vla",
              "execution_copy": str(ROOT), "native_build_passed": True,
              "build_reused": build_reused,
              "native_source_files": len(before), "source_unchanged": verify(NEW) == before,
              "parent_source_unchanged": verify(OLD) == parent,
              "contract_exit_code": contract.returncode,
              "physics_run": False, "navigation_validated": False}
    if (HERE / "contract/contract_results.json").exists():
        result["contract_passed"] = json.loads((HERE / "contract/contract_results.json").read_text())["passed"]
    result["passed"] = (contract.returncode == 0 and result["source_unchanged"] and
                        result["parent_source_unchanged"] and result.get("contract_passed", False))
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    records = {str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size}
               for directory in (OUT, HERE / f"contract/attempt_green{args.attempt:02d}", HERE / f"contract/attempt_red{args.attempt:02d}", NEW / "install")
               for p in directory.rglob("*") if p.is_file()}
    if (HERE / "contract/contract_results.json").exists():
        records[str((HERE / "contract/contract_results.json").relative_to(ROOT))] = {
            "sha256": sha(HERE / "contract/contract_results.json"),
            "bytes": (HERE / "contract/contract_results.json").stat().st_size}
    (OUT / "return_manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()

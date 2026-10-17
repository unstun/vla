"""Reuse the bounded native build; return ignored-build evidence locally."""
import importlib.util
import argparse
import json
from pathlib import Path
import shutil

from materialize import BASE, HERE, WORKSPACE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.attempt <= 20:
        parser.error("attempt must be in [1,20]")
    workspace = WORKSPACE.with_name(f"scan34_geometry_v{args.attempt}")
    if args.attempt != 1:
        if workspace.exists():
            raise FileExistsError(workspace)
        shutil.copytree(WORKSPACE / "src", workspace / "src")
        shutil.copyfile(WORKSPACE / "source_sha256.json", workspace / "source_sha256.json")
    spec = importlib.util.spec_from_file_location("bounded_native_build", BASE / "setup/build_scan_local.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.WORKSPACE = workspace
    module.NAME = f"vla-newton-scan34-geometry-build-v{args.attempt}"
    try:
        module.main()
    finally:
        out = HERE / ("build_evidence" if args.attempt == 1 else f"build_evidence_v{args.attempt}")
        out.mkdir(exist_ok=True)
        for name in ("source_sha256.json", "install_sha256.json", "build_request.json", "build_result.json",
                     "build_inside.sh", "build.log", "package_versions.txt"):
            if (workspace / name).exists():
                shutil.copyfile(workspace / name, out / name)
        print(json.dumps({"evidence": str(out)}))


if __name__ == "__main__":
    main()

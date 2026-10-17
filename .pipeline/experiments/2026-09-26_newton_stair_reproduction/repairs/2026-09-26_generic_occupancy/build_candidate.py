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
    parser.add_argument("--source-candidate", type=Path, default=WORKSPACE)
    parser.add_argument("--cache-from", type=Path)
    args = parser.parse_args()
    if not 1 <= args.attempt <= 20:
        parser.error("attempt must be in [1,20]")
    source_candidate = args.source_candidate.resolve()
    workspace = (source_candidate if args.attempt == 1 else
                 source_candidate.with_name(source_candidate.name.rsplit("_v", 1)[0] + f"_v{args.attempt}"))
    if args.attempt != 1:
        if workspace.exists():
            raise FileExistsError(workspace)
        shutil.copytree(source_candidate / "src", workspace / "src")
        shutil.copyfile(source_candidate / "source_sha256.json", workspace / "source_sha256.json")
    if args.cache_from:
        cache = args.cache_from.resolve()
        if not json.loads((cache / "build_result.json").read_text())["passed"]:
            raise ValueError("Cache source build did not pass")
        for name in ("build", "install"):
            shutil.copytree(cache / name, workspace / name, symlinks=True)
        (workspace / "cache_source.json").write_text(json.dumps({"source": str(cache), "purpose": "Colcon incremental cache; source identity and compiled tests remain mandatory"}, indent=2) + "\n")
    spec = importlib.util.spec_from_file_location("bounded_native_build", BASE / "setup/build_scan_local.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.WORKSPACE = workspace
    module.NAME = "vla-build-" + workspace.name.replace("_", "-")
    try:
        module.main()
    finally:
        out = HERE / ("build_evidence_" + workspace.name)
        out.mkdir(exist_ok=True)
        for name in ("source_sha256.json", "install_sha256.json", "build_request.json", "build_result.json",
                     "build_inside.sh", "build.log", "package_versions.txt", "cache_source.json", "executed_materialize.py"):
            if (workspace / name).exists():
                shutil.copyfile(workspace / name, out / name)
        print(json.dumps({"evidence": str(out)}))


if __name__ == "__main__":
    main()

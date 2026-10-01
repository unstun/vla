"""Mutation checks for the actual frozen-native launch guard; no physics."""
from pathlib import Path
import hashlib
import importlib.util
import json
import tempfile

HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location("v36_run_gate", HERE / "run_local_episode.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    checks = {}
    with tempfile.TemporaryDirectory() as directory:
        build = Path(directory) / "native"
        (build / "src").mkdir(parents=True)
        (build / "install").mkdir()
        runner.BUILD = build
        (build / "src/test.cpp").write_bytes(b"reviewed-source")
        (build / "install/controller").write_bytes(b"reviewed-binary")
        maps = {"native_source_sha256": {"src/test.cpp": digest(b"reviewed-source")},
                "native_install_sha256": {"install/controller": digest(b"reviewed-binary")}}
        for filename, key in (("source_sha256.json", "native_source_sha256"),
                              ("install_sha256.json", "native_install_sha256")):
            (build / filename).write_text(json.dumps(maps[key]))
        (build / "build_result.json").write_text(json.dumps({"passed": True, "source_unchanged": True}))
        runner.verify_native_build(build, maps)
        checks["reviewed_install_accepted"] = True

        def rejected(path, name):
            try:
                runner.verify_native_build(path, maps)
            except ValueError:
                checks[name] = True
            else:
                raise AssertionError("Unreviewed executable accepted: " + name)

        (build / "install/controller").write_bytes(b"changed-binary")
        rejected(build, "changed_binary_rejected")
        (build / "install_sha256.json").write_text(json.dumps({"install/controller": digest(b"changed-binary")}))
        rejected(build, "changed_binary_and_rehashed_live_manifest_rejected")
        rejected(Path(directory) / "alternate", "alternate_build_rejected")
    result = {"source_sha256": digest((HERE / "run_local_episode.py").read_bytes()),
              "test_sha256": digest(Path(__file__).read_bytes()), "checks": checks,
              "physics_run": False, "passed": all(checks.values())}
    target = HERE / "launch_gate_test_remote.json"
    assert not target.exists(), "Preserve prior gate test evidence"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

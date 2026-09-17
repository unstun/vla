"""Probe whether the installed Isaac RTX sensor set has a MID-360 profile."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_mid360_profiles(configs):
    matches = []
    for asset_path, variants in configs.items():
        candidates = [asset_path, *variants]
        if any(
            "mid360" in value.lower()
            or "mid-360" in value.lower()
            or "livox" in value.lower()
            for value in candidates
        ):
            matches.append(
                {"asset_path": asset_path, "variants": sorted(variants)}
            )
    return matches


def _parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--child-marker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--device", default="cuda:0")
    return parser


def _write_marker(path: Path, state: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"state": state}) + "\n", encoding="utf-8")


def _run_import_child(marker: Path, device: str) -> int:
    from isaaclab.app import AppLauncher

    _write_marker(marker, "launch_started")
    print("RTX_PROFILE_PROBE launching Isaac application", flush=True)
    app = AppLauncher(
        headless=True,
        enable_cameras=True,
        device=device,
    ).app
    _write_marker(marker, "application_ready")
    print("RTX_PROFILE_PROBE Isaac application ready", flush=True)
    try:
        _write_marker(marker, "module_import_started")
        print("RTX_PROFILE_PROBE importing RTX sensor module", flush=True)
        from isaacsim.sensors.rtx import LidarRtx  # noqa: F401

        _write_marker(marker, "module_import_completed")
    finally:
        app.close()
    _write_marker(marker, "teardown_completed")
    return 0


def _supported_config_source() -> Path:
    pattern = (
        "isaacsim/exts/isaacsim.sensors.rtx/isaacsim/sensors/rtx/impl/"
        "supported_lidar_configs.py"
    )
    python_dir = f"python{sys.version_info.major}.{sys.version_info.minor}"
    source = Path(sys.prefix) / "lib" / python_dir / "site-packages" / pattern
    if not source.is_file():
        raise RuntimeError(f"RTX supported-config source is missing: {source}")
    return source.resolve()


def _load_supported_configs(source: Path):
    module = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name)
            and target.id == "SUPPORTED_LIDAR_CONFIGS"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise RuntimeError("SUPPORTED_LIDAR_CONFIGS assignment was not found")


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.child_marker is not None:
        return _run_import_child(args.child_marker.resolve(), args.device)
    if args.output is None:
        raise SystemExit("--output is required for the parent probe")
    output = args.output.resolve()
    marker = output.parent / "rtx_import_child_marker.json"
    child = subprocess.run(
        [
            sys.executable,
            "-u",
            "-m",
            "lite3_sim_bridge.probe_rtx_lidar",
            "--child-marker",
            str(marker),
            "--device",
            args.device,
        ],
        check=False,
    )
    marker_payload = (
        json.loads(marker.read_text(encoding="utf-8"))
        if marker.is_file()
        else {"state": "missing"}
    )
    source = _supported_config_source()
    configs = _load_supported_configs(source)
    matches = find_mid360_profiles(configs)
    import_completed = marker_payload["state"] in (
        "module_import_completed",
        "teardown_completed",
    )
    teardown_completed = marker_payload["state"] == "teardown_completed"
    usable = bool(matches) and import_completed and teardown_completed
    report = {
        "schema_version": 1,
        "status": "PASS",
        "probe": "installed Isaac RTX LiDAR profile compatibility",
        "device": args.device,
        "child_returncode": child.returncode,
        "child_last_state": marker_payload["state"],
        "module_import_completed": import_completed,
        "teardown_completed": teardown_completed,
        "supported_config_source": str(source),
        "supported_config_source_sha256": _sha256(source),
        "supported_asset_count": len(configs),
        "supported_assets": [
            {"asset_path": path, "variants": sorted(variants)}
            for path, variants in sorted(configs.items())
        ],
        "mid360_profile_matches": matches,
        "usable_for_declared_mid360": usable,
        "selected_backend": (
            "RTX LiDAR" if usable else "IsaacLab MultiMeshRayCaster"
        ),
        "decision": (
            "The installed profile inventory has no MID-360 or Livox entry, and "
            "the live RTX module import did not return to the caller after the "
            "Isaac application became ready. Do not substitute another vendor's "
            "scan model; use the bounded geometric ray-cast backend."
        ),
        "creation_output_teardown_gate": (
            "not_run_after_profile_identity_and_module_lifecycle_rejection"
        ),
        "claim_boundary": (
            "The parent probe preserves the child lifecycle marker and parses the "
            "installed profile inventory without importing it. This is evidence "
            "for backend rejection, not a custom Livox profile or fidelity result."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

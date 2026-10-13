"""Verify corner-test identities and archived video evidence without rerunning physics."""

import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
HASHES = {}


def sha(path):
    path = path.resolve()
    stat = path.stat()
    key = (path, stat.st_size, stat.st_mtime_ns)
    if key not in HASHES:
        HASHES[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return HASHES[key]


def main():
    results = {"stage": "experiment + analysis", "versions": {}, "runs": {}}
    for version in ("v74", "v75", "v76", "v77"):
        directory = BASE / "versions" / version
        manifest = json.loads((directory / "manifest.json").read_text())
        for relative, expected in manifest["source_files"].items():
            assert sha(ROOT / relative) == expected, (version, "source", relative)
            snapshot = manifest["snapshot_locations"].get(relative)
            path = ROOT / snapshot if snapshot else directory / "source" / relative
            assert sha(path) == expected, (version, "snapshot", relative)
        assert sha(BASE / "versions" / manifest["parent"] / "manifest.json") == manifest["parent_manifest_sha256"]
        parsed = 0
        for path in directory.glob("*.py"):
            ast.parse(path.read_text(), filename=str(path))
            parsed += 1
        results["versions"][version] = {
            "manifest_sha256": sha(directory / "manifest.json"),
            "source_and_snapshot_files_verified": len(manifest["source_files"]),
            "owned_python_files_parsed": parsed,
            "parent_identity_verified": True,
        }

    pairs = (
        ("v76", "attempt01", "v76_mac_trial01_attempt01"),
        ("v77", "attempt02", "v77_mac_trial01_attempt02"),
    )
    handoffs = []
    for version, attempt, run in pairs:
        directory = BASE / "versions" / version
        evidence = directory / "mac_trials" / attempt / run
        gate = json.loads((evidence.parent / "entry_gate.json").read_text())
        assert gate["actual_native_source_install_gate_passed"]
        assert gate.get("mac_component_subset_passed", gate.get("native_transport_smoke_passed"))
        handoffs.append((evidence / "factory_handoff.json").read_bytes())
        video = json.loads((evidence / "video_closeout.json").read_text())
        verification = json.loads((evidence / "review/video_verification.json").read_text())
        timeline = json.loads((evidence / "review/timeline_verification.json").read_text())
        assert verification["status"] == "passed" and verification["full_decode_passed"]
        assert timeline["passed"] and timeline["all_original_times_indices_causal"] and timeline["no_interpolation"]
        assert sha(Path(video["local_video"])) == video["sha256"] == verification["sha256"]
        assert Path(video["local_video"]).stat().st_size == video["bytes"]
        remote_files = remote_bytes = 0
        for stored in evidence.glob("*_storage.json"):
            manifest = json.loads(stored.read_text())
            proof = json.loads(stored.with_name(stored.name.replace("_storage.json", "_remote_verification.json")).read_text())
            assert proof["passed"] and not proof["gpu_job_started"]
            assert proof["files"] == len(manifest["files"])
            assert proof["bytes"] == sum(row["bytes"] for row in manifest["files"].values()) == manifest["bytes"]
            remote_files += proof["files"]
            remote_bytes += proof["bytes"]
        review = {
            "physical_source_version": version,
            "native_planning_source": "v63" if version == "v76" else "v71 pinned upstream ROS2 probe",
            "source_run": run,
            "local_video_path": video["local_video"],
            "sha256": video["sha256"],
            "bytes": video["bytes"],
            "duration_s": float(verification["stream"]["duration"]),
            "frames": verification["frames"],
            "fps": 30,
            "width": verification["stream"]["width"],
            "height": verification["stream"]["height"],
            "full_ffmpeg_decode_passed": True,
            "three_sample_frames_visually_reviewed": True,
            "visual_observation": "Crosses the landing corner and climbs onward; goal active at bound." if version == "v76" else "Moves briefly then stands; upstream partial-capture label retained.",
            "timeline": timeline,
            "render_only_no_physics_steps": True,
            "incomplete_physical_recording": version == "v77",
            "physics_goal_acceptance": False,
            "durable_raw_location": "gpu5070ti:" + video["raw_remote_root"],
            "display_fps_is_not_planning_hz": True,
        }
        assert len(list((evidence / "review/frame_samples").glob("*.png"))) == 3
        (directory / "REVIEW_VIDEO.json").write_text(json.dumps(review, indent=2) + "\n")
        results["runs"][run] = {
            "actual_entry_gate_passed": True,
            "video_sha_decode_timeline_and_visual_review_passed": True,
            "remote_files_verified": remote_files,
            "remote_bytes_verified": remote_bytes,
            "incomplete_physical_recording": version == "v77",
        }

    assert handoffs[0] == handoffs[1], "Actual factory handoffs differ"
    assert sha(BASE / "versions/v76/corner_scenario.json") == sha(BASE / "versions/v77/corner_scenario.json")
    assert json.loads((BASE / "versions/current.json").read_text())["current"] == "v48"
    results.update(
        passed=True,
        actual_initial_factory_handoffs_byte_exact=True,
        current_reference="v48",
        navigation_and_30hz_acceptance=False,
        production_fix=False,
        remote_gpu_job_started=False,
        checker_sha256=sha(Path(__file__)),
    )
    (HERE / "completion_checks.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

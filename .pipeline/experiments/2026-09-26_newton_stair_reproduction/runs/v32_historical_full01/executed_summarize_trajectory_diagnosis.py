"""Validate captured diagnostic comparisons and plot actual candidate points."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = Path(__file__).resolve().parents[1]
BUILD = BASE / "builds/scan33_humble_amd64_v1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    runs = BASE / "runs"
    names = ("tracking_replay_diagnosis_v1", "tracking_replay_diagnosis_v2",
             "tracking_gate_diagnosis_v1", "ray_coverage_diagnosis_v1",
             "ray_orientation_diagnosis_v1", "native_timing_diagnosis_v1")
    checks, source_checks = {}, {}
    for name in names:
        process = json.loads((runs / name / "process.json").read_text())
        checks[f"{name}_completed"] = process["exit_code"] == 0 and not process["timed_out"]
    for manifest, root in (("source_sha256.json", BUILD), ("install_sha256.json", BUILD)):
        records = json.loads((root / manifest).read_text())
        mismatches = [path for path, expected in records.items() if digest(root / path) != expected]
        source_checks[manifest] = {"files": len(records), "mismatches": mismatches}
    for name, key in (("source_identity.json", "inputs"), ("runtime_sources.json", "records")):
        records = json.loads((BASE / "setup" / name).read_text())[key]
        mismatches = [row["path"] for row in records if digest(BASE / row["path"]) != row["sha256"]]
        source_checks[name] = {"files": len(records), "mismatches": mismatches}
    reference = BASE / "references/2026-09-26_trajectory_diagnosis"
    references = json.loads((reference / "source.json").read_text())["files"]
    source_checks["upstream_references"] = {
        "files": len(references),
        "mismatches": [row["path"] for row in references if digest(reference / row["path"]) != row["sha256"]],
    }
    checks["source_manifests_intact"] = all(not row["mismatches"] for row in source_checks.values())
    for name in names[:2]:
        result = json.loads((runs / name / "result.json").read_text())
        checks[f"{name}_280_live_matches"] = result["frames"] == result["live_matches"] == 280
        checks[f"{name}_two_target_failures"] = result["failure_times_s"] == [12.901583672, 13.001624107]
    checks["repeated_tracker_replay_byte_exact"] = (
        (runs / names[0] / "tracker_replay.json").read_bytes()
        == (runs / names[1] / "tracker_replay.json").read_bytes()
    )
    gate_rows = json.loads((runs / "tracking_gate_diagnosis_v1/gate_trace.json").read_text())
    frames = {row["scan_index"]: row for row in gate_rows}
    for index in (128, 129):
        parts = frames[index]["components"]
        checks[f"frame_{index}_vertical_gate_only"] = (
            len(parts) == 1 and parts[0]["failed_gates"] == ["vertical_span"]
        )
    orientation = json.loads((runs / "ray_orientation_diagnosis_v1/result.json").read_text())
    coverage = json.loads((runs / "ray_coverage_diagnosis_v1/result.json").read_text())
    checks["zero_physics_steps"] = orientation["physics_steps"] == coverage["physics_steps"] == 0
    for index in (128, 129):
        rows = {row["condition"]: row for row in orientation["conditions"] if row["scan_index"] == index}
        checks[f"frame_{index}_ray_parity"] = rows["recorded"]["saved_cloud_exact"]
        checks[f"frame_{index}_orientation_restores_candidate"] = rows["previous_orientation_only"]["detections"] == 1
        checks[f"frame_{index}_position_does_not_restore_candidate"] = rows["previous_position_only"]["detections"] == 0
        controls = {row["condition"]: row for row in coverage["conditions"] if row["scan_index"] == index}
        checks[f"frame_{index}_pattern_and_visibility_do_not_restore"] = (
            controls["previous_pattern_only"]["detections"] == controls["visible_human_only"]["detections"] == 0
        )
    timing = json.loads((runs / "native_timing_diagnosis_v1/result.json").read_text())
    checks["published_curves_native_feasible"] = all(row["feasible"] for row in timing if row["condition"] == "recorded")
    checks["compressed_final_geometry_native_infeasible"] = all(
        not row["feasible"] for row in timing if row["condition"] == "same_geometry_seed_duration"
    )
    video_states = runs / "stair_native_walk_v2/video_states.json"
    prior = json.loads((BASE / "validation/stair_native_walk_v2_review.json").read_text())
    checks["original_video_states_unchanged"] = digest(video_states) == prior["video_states_sha256"]

    sources = out / "diagnostic_sources_as_reviewed"
    sources.mkdir()
    for path in sorted((BASE / "scripts").glob("diagnose_*")):
        if path.suffix == ".py":
            ast.parse(path.read_text(), filename=str(path))
        if path.is_file():
            shutil.copyfile(path, sources / path.name)
    shutil.copyfile(__file__, sources / Path(__file__).name)

    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 4, figsize=(11.2, 4.5), sharex=True, sharey=True)
    for ax, index in zip(axes, (127, 128, 129, 130), strict=True):
        row = frames[index]
        part = row["components"][0]
        points = np.asarray(part["points_world"])
        accepted = not part["failed_gates"]
        color = "#187b77" if accepted else "#c64e30"
        ax.scatter(points[:, 0], points[:, 2], s=15, color=color, alpha=.8)
        ax.set_title(f'{row["sim_time_s"]:.3f} s\n{len(points)} points | {"accepted" if accepted else "rejected"}', color=color)
        ax.set_xlabel("World x (m)")
        ax.set_xlim(-6.25, -5.6)
        ax.set_ylim(1.0, 2.55)
        ax.grid(alpha=.15)
        ax.text(.04, .95, f'Height span\n{part["vertical_span_m"]:.3f} m',
                transform=ax.transAxes, va="top", color=color)
    axes[0].set_ylabel("World z (m)")
    fig.suptitle("Measured foreground: two scans fall below the 0.45 m height-span gate", fontsize=14)
    fig.text(.5, .015, "Actual points after background / height filters. Equal axes; no predicted or truth-derived points.", ha="center", fontsize=10)
    fig.tight_layout(rect=(0, .05, 1, .92))
    fig.savefig(out / "tracking_coverage.png", dpi=160)
    fig.savefig(out / "tracking_coverage.pdf")
    plt.close(fig)
    report = {
        "stage": "experiment + analysis", "scope": "diagnosis only",
        "checks": checks, "source_checks": source_checks,
        "diagnostic_checks_passed": all(checks.values()), "navigation_validated": False,
        "evidence_sha256": {
            str(path.relative_to(BASE)): digest(path)
            for name in names for path in (runs / name).rglob("*") if path.is_file()
        },
        "source_snapshots": {path.name: digest(path) for path in sources.iterdir()},
        "limits": [
            "Exact initializer seed arrays were not recorded; the 21.4064 initial scale is logged, not exactly replayed.",
            "Compressed cases keep the final optimized geometry; feasibility ratios on already-feasible curves are ignored.",
            "Ray orientation controls are sensitivity diagnostics, not proposed sensor calibration or validated fixes.",
            "Current-only detection, native thresholds and the old live run are unchanged.",
        ],
    }
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("evidence_sha256", "source_snapshots")}, indent=2))
    if not all(checks.values()):
        raise AssertionError("Diagnosis evidence validation failed")


if __name__ == "__main__":
    main()

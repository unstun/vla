"""Geometry-only comparison of verified, actually returned native PCT paths."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parents[3]
STEP_M = 0.10
COLORS = {"v247": "#C76A24", "v251": "#1768A6"}
LABELS = {"v247": "v247 returned graph", "v251": "v251 returned GPMP"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def turns(headings: np.ndarray) -> np.ndarray:
    return np.abs(np.remainder(np.diff(headings) + np.pi, 2 * np.pi) - np.pi) * 180 / np.pi


def distribution(values: np.ndarray) -> dict:
    if not len(values):
        return {"count": 0, "p50_deg": None, "p90_deg": None, "p95_deg": None,
                "p99_deg": None, "max_deg": None, "total_absolute_deg": 0.0}
    return dict(count=len(values), **{
        f"p{p}_deg": float(np.percentile(values, p)) for p in (50, 90, 95, 99)},
        max_deg=float(np.max(values)), total_absolute_deg=float(np.sum(values)))


def regular_grid(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Zero-XY segments retain their original 3-D length in the separate length
    # metric. They cannot define a planar tangent; retain the last such pose.
    distances = np.linalg.norm(np.diff(xyz[:, :2], axis=0), axis=1)
    keep = np.r_[distances > 1e-9, True]
    xy = xyz[keep]
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(xy[:, :2], axis=0), axis=1))]
    assert len(s) >= 3 and np.all(np.diff(s) > 0)
    q = np.arange(0.0, s[-1] + 1e-9, STEP_M)
    points = np.column_stack([np.interp(q, s, xy[:, k]) for k in range(3)])
    return q, points


def analyze(path: Path, start: np.ndarray, goal: np.ndarray, measured_yaw: float) -> tuple[dict, dict]:
    route = np.genfromtxt(path, names=True, delimiter=",")
    xyz = np.column_stack([route[key] for key in ("x", "y", "z")])
    assert xyz.shape[0] >= 3 and np.isfinite(xyz).all() and np.isfinite(route["yaw"]).all()
    delta = np.diff(xyz, axis=0)
    xy_segment = np.linalg.norm(delta[:, :2], axis=1)
    valid = xy_segment > 1e-6
    geometric_heading = np.arctan2(delta[valid, 1], delta[valid, 0])
    connector = xyz[0] - start
    connector_xy = float(np.linalg.norm(connector[:2]))
    connected = np.vstack([start, xyz]) if np.linalg.norm(connector) > 1e-9 else xyz
    q, points = regular_grid(connected)
    heading = np.arctan2(np.diff(points[:, 1]), np.diff(points[:, 0]))
    jumps = turns(heading)
    centers = q[1:-1]
    # Coordinate-free stair/ramp neighborhood. This is a geometric definition,
    # not an assertion that a particular mesh point is a physical foot contact.
    before = np.interp(np.maximum(centers - .5, q[0]), q, points[:, 2])
    after = np.interp(np.minimum(centers + .5, q[-1]), q, points[:, 2])
    vertical = np.abs(after - before) >= .10
    initial = {}
    if connector_xy > 1e-6:
        cy = float(np.arctan2(connector[1], connector[0]))
        initial = {"connector_yaw_deg": float(np.degrees(cy)),
                   "connector_to_first_segment_jump_deg": float(turns(np.array([cy, geometric_heading[0]]))[0]),
                   "measured_body_to_connector_yaw_deg": float(turns(np.array([measured_yaw, cy]))[0])}
    result = dict(points=len(xyz), first_xyz=xyz[0].tolist(), last_xyz=xyz[-1].tolist(),
                  requested_start_xyz=start.tolist(), requested_goal_xyz=goal.tolist(),
                  first_point_offset_xy_m=connector_xy,
                  first_point_offset_3d_m=float(np.linalg.norm(connector)),
                  sample_reference_initial_rotation_deg=float(turns(np.array([measured_yaw, route["yaw"][0]]))[0]),
                  returned_goal_error_3d_m=float(np.linalg.norm(xyz[-1] - goal)),
                  returned_xy_length_m=float(np.sum(xy_segment)),
                  returned_3d_length_m=float(np.sum(np.linalg.norm(delta, axis=1))),
                  returned_total_vertical_variation_m=float(np.sum(np.abs(delta[:, 2]))),
                  request_connected_xy_length_m=float(np.sum(xy_segment) + connector_xy),
                  request_connected_3d_length_m=float(np.sum(np.linalg.norm(delta, axis=1)) + np.linalg.norm(connector)),
                  zero_xy_segments=int(np.sum(~valid)),
                  native_geometry_jumps=distribution(turns(geometric_heading)),
                  stored_pose_yaw_jumps=distribution(turns(route["yaw"])),
                  native_last_yaw_vs_terminal_tangent_deg=float(turns(np.array([geometric_heading[-1], route["yaw"][-1]]))[0]),
                  uniform_0p10m_geometry_jumps=distribution(jumps),
                  vertical_neighborhood_uniform_jumps=distribution(jumps[vertical]),
                  uniform_tail_not_sampled_m=float(np.sum(xy_segment) + connector_xy - q[-1]),
                  initial_connector=initial)
    traces = dict(xyz=xyz, connected=connected, s=q, points=points, jump_s=centers,
                  jumps=jumps, vertical=vertical)
    return result, traces


def intervals(s: np.ndarray, mask: np.ndarray) -> list[tuple[float, float]]:
    selected = np.flatnonzero(mask)
    if not len(selected):
        return []
    groups = np.split(selected, np.flatnonzero(np.diff(selected) > 1) + 1)
    return [(float(s[g[0]] - STEP_M / 2), float(s[g[-1]] + STEP_M / 2)) for g in groups]


def draw(report: dict, traces: dict) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/vla_route_comparison_mpl")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": .18,
                         "svg.fonttype": "none", "pdf.fonttype": 42})
    cases = [case for case in ("G07", "R11") if case in report["paired_admitted_cases"]]
    if not cases:
        return
    fig, axes = plt.subplots(len(cases), 3, figsize=(12.5, 3.7 * len(cases)), squeeze=False,
                             constrained_layout=True)
    for row, case in enumerate(cases):
        plan, height, angle = axes[row]
        for version in ("v247", "v251"):
            t = traces[(case, version)]
            data = report["cases"][case][version]
            xy = t["connected"]
            plan.plot(xy[:, 0], xy[:, 1], color=COLORS[version], lw=1.2, alpha=.85, label=LABELS[version])
            height.plot(t["s"], t["points"][:, 2], color=COLORS[version], lw=1.2, label=version)
            angle.plot(t["jump_s"], t["jumps"], color=COLORS[version], lw=.9, alpha=.85,
                       label=f"{version}: p95 {data['uniform_0p10m_geometry_jumps']['p95_deg']:.2f}°, max {data['uniform_0p10m_geometry_jumps']['max_deg']:.2f}°")
        # Gray spans use the v251 geometric vertical-transition neighborhood.
        t = traces[(case, "v251")]
        for left, right in intervals(t["jump_s"], t["vertical"]):
            height.axvspan(left, right, color="0.85", alpha=.45, zorder=-1)
            angle.axvspan(left, right, color="0.85", alpha=.45, zorder=-1)
        start = report["cases"][case]["v251"]["requested_start_xyz"]
        goal = report["cases"][case]["v251"]["requested_goal_xyz"]
        plan.scatter([start[0]], [start[1]], c="black", marker="o", s=23, zorder=4)
        plan.scatter([goal[0]], [goal[1]], c="black", marker="*", s=58, zorder=4)
        plan.set(title=f"{case} | returned geometry and request connector", xlabel="World x (m)", ylabel="World y (m)")
        plan.set_aspect("equal", adjustable="datalim")
        plan.legend(fontsize=8, loc="best")
        height.set(title="Support-aligned height profile", xlabel="XY arclength from requested start (m)", ylabel="Body reference z (m)")
        height.legend(fontsize=8)
        angle.set(title="Planar heading change on a common 0.10 m grid", xlabel="XY arclength from requested start (m)", ylabel="Absolute heading change (deg)", ylim=(-1, 48))
        angle.legend(fontsize=7.5, loc="upper right")
    fig.suptitle("Frozen rep01 requests: native returned route geometry (v247 vs v251)", fontsize=13)
    fig.get_layout_engine().set(rect=(0, .035, 1, .96))
    fig.text(.02, .008, "Gray: |z(s+0.5 m) − z(s−0.5 m)| ≥ 0.10 m. Route geometry only; no speed, pause, or physical-execution inference.", fontsize=8)
    for extension in ("png", "pdf"):
        metadata = {"CreationDate": None, "ModDate": None} if extension == "pdf" else None
        fig.savefig(HERE / f"route_geometry_comparison.{extension}", dpi=220, metadata=metadata)
    plt.close(fig)

    fig, axes = plt.subplots(1, len(cases), figsize=(6.1 * len(cases), 4.4), squeeze=False, constrained_layout=True)
    for ax, case in zip(axes[0], cases):
        for version in ("v247", "v251"):
            t = traces[(case, version)];values = np.sort(t["jumps"][t["vertical"]])
            ax.step(values, np.arange(1, len(values) + 1) / len(values), where="post", color=COLORS[version],
                    label=f"{version}, n={len(values)}")
        ax.set(title=f"{case}: vertical-transition neighborhood", xlabel="Heading change over common 0.10 m samples (deg)", ylabel="Empirical cumulative probability", xlim=(-.5, 46), ylim=(0, 1.02))
        ax.legend()
    fig.suptitle("Stair/ramp geometric context: equal spatial sampling", fontsize=12)
    for extension in ("png", "pdf"):
        metadata = {"CreationDate": None, "ModDate": None} if extension == "pdf" else None
        fig.savefig(HERE / f"vertical_transition_turns.{extension}", dpi=220, metadata=metadata)
    plt.close(fig)


def main() -> None:
    receipt_path = HERE / "collection_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    assert receipt["cases_manifest_sha256"] == sha(EXPERIMENT / "versions/v242/cases_manifest.json")
    report = {"collection_receipt_sha256": sha(receipt_path), "repetition": 1,
              "uniform_xy_spacing_m": STEP_M, "vertical_neighborhood_definition":
              "|z(s+0.5m)-z(s-0.5m)|>=0.10m on the common XY-arclength polyline", "cases": {},
              "paired_admitted_cases": [], "source_binding_local_verified": {}}
    for version, entry in receipt["versions"].items():
        report["source_binding_local_verified"][version] = {}
        for name, artifact in entry["source_binding"].items():
            local = EXPERIMENT / "versions" / version / name
            assert sha(local) == artifact["sha256"], str(local)
            report["source_binding_local_verified"][version][name] = artifact["sha256"]
    traces = {}
    rows = []
    for cid, fixture in receipt["fixtures"].items():
        endpoint = np.array(list(map(float, fixture["files"]["endpoints.txt"]["text"].split())))
        assert len(endpoint) == 7
        row = report["cases"][cid] = {}
        for version, entry in receipt["versions"].items():
            artifact = entry["cases"][cid]
            if not artifact["completed"]:
                row[version] = {"completed": False}
                continue
            for data in artifact["files"].values():
                assert sha(HERE / data["local_path"]) == data["sha256"]
            summary = json.loads((HERE / artifact["files"]["summary.json"]["local_path"]).read_text())
            common = {"completed": True, "global_admitted": summary["global_admitted"],
                      "first_gpmp_static_pass": summary["first_gpmp_static_pass"],
                      "graph_fallback_attempted": summary["graph_fallback_attempted"],
                      "end_to_end_component_pass": summary["end_to_end_pass"],
                      "global_time_s": summary["metrics"].get("global_s"),
                      "static_requests": summary["metrics"].get("static_requests"),
                      "static_rejected_samples": summary["metrics"].get("static_rejected_samples"),
                      "edge_margin_min_m": summary.get("edge_margin_min"),
                      "raw_solid_margin_min_m": summary.get("raw_solid_margin_min"),
                      "diagnostic_lines": artifact.get("diagnostic_lines", []),
                      "scenario_sha256": fixture["case"]["scenario_sha256"],
                      "endpoints_sha256": fixture["files"]["endpoints.txt"]["sha256"]}
            if not summary["global_admitted"]:
                row[version] = common
                continue
            route_artifact = artifact["files"]["route.csv"]
            result, trace = analyze(HERE / route_artifact["local_path"], endpoint[:3], endpoint[3:6], endpoint[6])
            result.update(common, route_sha256=route_artifact["sha256"],
                          remote_route_path=route_artifact["remote_path"])
            row[version] = result
            traces[cid, version] = trace
            rows.append(dict(case_id=cid, version=version, points=result["points"],
                returned_xy_length_m=result["returned_xy_length_m"], returned_3d_length_m=result["returned_3d_length_m"],
                connected_xy_length_m=result["request_connected_xy_length_m"],
                connector_xy_m=result["first_point_offset_xy_m"], global_time_s=result["global_time_s"],
                native_max_deg=result["native_geometry_jumps"]["max_deg"], native_p95_deg=result["native_geometry_jumps"]["p95_deg"],
                common_p50_deg=result["uniform_0p10m_geometry_jumps"]["p50_deg"],
                common_p90_deg=result["uniform_0p10m_geometry_jumps"]["p90_deg"],
                common_p95_deg=result["uniform_0p10m_geometry_jumps"]["p95_deg"],
                common_p99_deg=result["uniform_0p10m_geometry_jumps"]["p99_deg"],
                common_max_deg=result["uniform_0p10m_geometry_jumps"]["max_deg"],
                vertical_p95_deg=result["vertical_neighborhood_uniform_jumps"]["p95_deg"],
                vertical_max_deg=result["vertical_neighborhood_uniform_jumps"]["max_deg"],
                total_turn_deg=result["uniform_0p10m_geometry_jumps"]["total_absolute_deg"]))
        if all(row[v].get("global_admitted") for v in ("v247", "v251")):
            assert row["v247"]["endpoints_sha256"] == row["v251"]["endpoints_sha256"]
            report["paired_admitted_cases"].append(cid)
    (HERE / "comparison_metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    with (HERE / "comparison_metrics.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    draw(report, traces)
    for cid in ("G07", "R11"):
        if cid not in report["paired_admitted_cases"]:
            print(cid, "not yet paired/completed");continue
        for version in ("v247", "v251"):
            r = report["cases"][cid][version]
            print(cid, version, "XY", round(r["request_connected_xy_length_m"], 3),
                  "3D", round(r["request_connected_3d_length_m"], 3),
                  "0.1m p95/max", round(r["uniform_0p10m_geometry_jumps"]["p95_deg"], 3),
                  round(r["uniform_0p10m_geometry_jumps"]["max_deg"], 3),
                  "vertical p95/max", round(r["vertical_neighborhood_uniform_jumps"]["p95_deg"], 3),
                  round(r["vertical_neighborhood_uniform_jumps"]["max_deg"], 3),
                  "global_s", r["global_time_s"])
    files = {str(p.relative_to(HERE)): {"sha256": sha(p), "bytes": p.stat().st_size}
             for p in sorted(HERE.rglob("*")) if p.is_file() and
             "__pycache__" not in p.parts and p.name != "artifact_sha256.json"}
    (HERE / "artifact_sha256.json").write_text(json.dumps(files, indent=2) + "\n")


if __name__ == "__main__":
    main()

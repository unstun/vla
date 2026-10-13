#!/usr/bin/env python3
"""Render v48 timing evidence without modifying the frozen implementation.

Run with Python 3 plus NumPy and Matplotlib. Outputs are written beside this
script. The frequency denominator is wall time; the shared x-axis is simulation
time, interpolated between the logged attempt-start clock pairs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "v48-matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "v48-plot-cache"))
Path(os.environ["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter
import numpy as np


OUT = Path(__file__).resolve().parent
ANALYSIS = OUT.parent
BASE = ANALYSIS.parents[2]
RUN = BASE / "runs" / "v48_realtime_trial01"
EXPECTED_SCAN_SHA256 = "bac497c6543e018cf0b50168d79e821ee9cf52717e1d55374d72c3e59a41a07b"
WINDOW_S = 1.0
GRID_STEP_S = 0.05
FAST_MS = 10.0
BUDGET_MS = 1000.0 / 30.0
START_RE = re.compile(
    r"nominal_replan frequency_hz=([\d.]+) "
    r"start_schedule_s=([\d.]+) clock=(\w+) ros_s=([\d.]+) "
    r"state=(\d+) skipped_slots=(\d+)"
)
RESULT_RE = re.compile(r"nominal_replan_result success=(\d+) wall_s=([\d.]+)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group(round_data: dict) -> str:
    if round_data["warm_graph_fallbacks"] > 0:
        return "warm_to_graph_fallback"
    if round_data["warm_accepts"] > 0:
        return "warm_only_fast" if round_data["wall_s"] * 1000 < FAST_MS else "warm_only_slow"
    return "no_warm_acceptance"


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    log_path = RUN / "scan.log"
    rounds_path = ANALYSIS / "v48_rounds.json"
    metrics_path = ANALYSIS / "metrics.json"
    if sha256(log_path) != EXPECTED_SCAN_SHA256:
        raise ValueError("The raw scan.log differs from the recorded v48 trial.")
    lines = log_path.read_text().splitlines()
    starts = []
    for line_number, line in enumerate(lines, 1):
        match = START_RE.search(line)
        if match:
            target_hz, wall_s, clock, sim_s, state, skipped = match.groups()
            if clock != "wall" or float(target_hz) != 30.0:
                raise ValueError("Unexpected scheduler clock or requested frequency.")
            starts.append({"start_line": line_number, "wall_s": float(wall_s),
                           "sim_s": float(sim_s), "state": int(state),
                           "skipped_slots": int(skipped)})
    rounds = json.loads(rounds_path.read_text())
    metrics = json.loads(metrics_path.read_text())["v48"]
    if len(starts) != metrics["nominal_attempt_starts"] or len(rounds) != metrics["completed_rounds"]:
        raise ValueError("Raw start count or completed-round count differs from the recorded analysis.")

    # Cross-check every plotted latency and warm classification against its raw
    # log segment, rather than trusting the prior JSON alone.
    starts_by_line = {item["start_line"]: item for item in starts}
    for row in rounds:
        original = starts_by_line[row["start_line"]]
        if not np.isclose(original["sim_s"], row["ros_s"], rtol=0, atol=1e-8):
            raise ValueError("Round simulation timestamp differs from its raw start marker.")
        segment = lines[row["start_line"] - 1:row["end_line"]]
        result = RESULT_RE.search(segment[-1])
        if result is None or bool(int(result[1])) != row["success"]:
            raise ValueError("Round completion status differs from the raw result marker.")
        if not np.isclose(float(result[2]), row["wall_s"], rtol=0, atol=1e-10):
            raise ValueError("Round latency differs from the raw result marker.")
        text = "\n".join(segment)
        for key, marker in (("warm_selections", "V48_WARM_SEED selected=1"),
                            ("warm_accepts", "V48_WARM_RESULT accepted=1"),
                            ("warm_graph_fallbacks", "V48_WARM_RESULT accepted=0 graph_fallback=1")):
            if text.count(marker) != row[key]:
                raise ValueError(f"Round {key} differs from the raw log segment.")

    wall = np.array([item["wall_s"] for item in starts])
    sim = np.array([item["sim_s"] for item in starts])
    if not np.all(np.diff(wall) > 0) or not np.all(np.diff(sim) >= 0):
        raise ValueError("Clock pairs must be monotonic for interpolation.")
    grid = np.arange(wall[0] + WINDOW_S, wall[-1], GRID_STEP_S)
    grid = np.append(grid, wall[-1])
    hz = (np.searchsorted(wall, grid, side="right")
          - np.searchsorted(wall, grid - WINDOW_S, side="right")) / WINDOW_S
    grid_sim = np.interp(grid, wall, sim)
    attempt_hz = (len(wall) - 1) / (wall[-1] - wall[0])
    if not np.isclose(attempt_hz, metrics["actual_local_attempt_hz"], rtol=0, atol=1e-10):
        raise ValueError("The global attempt frequency differs from the prior analysis.")
    solve_ms = np.array([item["wall_s"] * 1000 for item in rounds])
    round_sim = np.array([item["ros_s"] for item in rounds])
    groups = np.array([group(item) for item in rounds])
    failed = np.array([not item["success"] for item in rounds])
    computed_latency = {"median": float(np.median(solve_ms)),
                        "p95": float(np.percentile(solve_ms, 95)),
                        "p99": float(np.percentile(solve_ms, 99)),
                        "maximum": float(np.max(solve_ms))}
    for key, value in computed_latency.items():
        if not np.isclose(value, metrics["local_solve_ms"][key], rtol=0, atol=1e-8):
            raise ValueError(f"Recomputed latency {key} differs from the prior analysis.")

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.titlesize": 12, "axes.labelsize": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#aeb9c4", "axes.linewidth": 0.7,
                         "text.color": "#233144", "axes.labelcolor": "#233144",
                         "xtick.color": "#526174", "ytick.color": "#526174",
                         "svg.fonttype": "none", "pdf.fonttype": 42})
    fig, (rate_ax, latency_ax) = plt.subplots(
        2, 1, figsize=(13.0, 8.5), sharex=True,
        gridspec_kw={"height_ratios": [1, 1.45]})
    fig.subplots_adjust(left=0.083, right=0.975, bottom=0.21, top=0.80, hspace=0.28)
    fig.text(0.083, 0.948, "v48  |  Real-time local planning", fontsize=21, weight="bold")
    fig.text(0.083, 0.912, "gpu5070ti  ·  v48_realtime_trial01  ·  Simulation time on both x-axes",
             fontsize=11, color="#526174")
    fig.text(0.083, 0.866,
             f"Overall attempt rate  {attempt_hz:.2f} Hz     |     "
             f"Median solve  {computed_latency['median']:.2f} ms     |     "
             f"P99  {computed_latency['p99']:.2f} ms     |     "
             f"Peak  {computed_latency['maximum']:,.0f} ms",
             fontsize=11, weight="medium")

    for ax in (rate_ax, latency_ax):
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#e6ebf0", linewidth=0.7)
        ax.grid(axis="x", color="#eef1f5", linewidth=0.6)
        ax.tick_params(length=3)
    rate_ax.set_title("A   Local planning frequency  ·  trailing 1 wall-second window", loc="left", pad=12)
    rate_ax.fill_between(grid_sim, hz, color="#c7e7e5", alpha=0.75, linewidth=0)
    rate_ax.plot(grid_sim, hz, color="#167b82", linewidth=1.2)
    rate_ax.axhline(30, color="#455368", linestyle=(0, (5, 3)), linewidth=1.15)
    rate_ax.axhline(attempt_hz, color="#8c9aab", linestyle=(0, (2, 3)), linewidth=0.9)
    rate_ax.text(89.5, 30.6, "30 Hz target", ha="right", color="#455368", fontsize=9)
    rate_ax.text(89.5, attempt_hz + 0.6, f"Overall {attempt_hz:.2f} Hz", ha="right",
                 color="#657489", fontsize=9, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1})
    rate_ax.axvspan(sim[0], grid_sim[0], color="#e9edf1", alpha=0.8)
    rate_ax.set_ylabel("Attempt starts / wall second (Hz)")
    rate_ax.set_ylim(0, max(34, float(hz.max()) + 2))
    rate_ax.set_yticks([0, 10, 20, 30])

    latency_ax.set_title("B   Per-round solve latency  ·  plotted at the attempt's simulation start time", loc="left", pad=12)
    latency_ax.set_yscale("log")
    latency_ax.axhspan(0.6, FAST_MS, color="#e5f4ed", zorder=0)
    latency_ax.axhspan(BUDGET_MS, 1600, color="#fff7eb", zorder=0)
    styles = [
        ("warm_only_fast", "Warm only, <10 ms", "#1a996e", "o", 10, 0.70),
        ("warm_only_slow", "Warm only, ≥10 ms", "#4c7bad", "o", 10, 0.55),
        ("no_warm_acceptance", "No warm acceptance", "#d68132", "o", 20, 0.85),
        ("warm_to_graph_fallback", "Warm → graph fallback", "#9866ac", "D", 28, 0.90),
    ]
    for key, label, color, marker, size, alpha in styles:
        mask = groups == key
        latency_ax.scatter(round_sim[mask], solve_ms[mask], s=size, color=color,
                           marker=marker, linewidths=0, alpha=alpha,
                           label=f"{label} (n={int(mask.sum()):,})", zorder=3)
    latency_ax.scatter(round_sim[failed], solve_ms[failed], s=42, color="#b74549",
                       marker="x", linewidths=1.2, label=f"Failed rounds (n={int(failed.sum())})", zorder=4)
    latency_ax.axhline(FAST_MS, color="#33846d", linewidth=0.9, linestyle=(0, (3, 3)))
    latency_ax.axhline(BUDGET_MS, color="#ad7a39", linewidth=0.9, linestyle=(0, (3, 3)))
    latency_ax.text(89.5, 8.5, "Fast regime <10 ms", ha="right", va="top", fontsize=9,
                    color="#33846d", bbox={"facecolor": "#e5f4ed", "edgecolor": "none", "alpha": 0.9, "pad": 1})
    latency_ax.text(89.5, 38, "30 Hz budget: 33.3 ms", ha="right", va="bottom", fontsize=9,
                    color="#ad7a39", bbox={"facecolor": "#fff7eb", "edgecolor": "none", "alpha": 0.9, "pad": 1})
    max_index = int(np.argmax(solve_ms))
    latency_ax.annotate(f"Peak {solve_ms[max_index]:,.0f} ms\nat {round_sim[max_index]:.2f} s",
                        xy=(round_sim[max_index], solve_ms[max_index]), xytext=(69, 1030),
                        fontsize=9, color="#875526", ha="left", va="center",
                        arrowprops={"arrowstyle": "-", "color": "#ac845f", "linewidth": 0.9},
                        bbox={"facecolor": "#fff7eb", "edgecolor": "none", "alpha": 0.95, "pad": 2})
    latency_ax.set_ylabel("Round solve time (wall ms; log scale)")
    latency_ax.set_xlabel("Simulation time (s)", labelpad=9)
    latency_ax.set_ylim(0.6, 1600)
    latency_ax.yaxis.set_major_locator(FixedLocator([1, 3, 10, BUDGET_MS, 100, 300, 1000]))
    latency_ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: "33.3" if np.isclose(value, BUDGET_MS) else f"{value:g}"))
    latency_ax.minorticks_off()
    latency_ax.set_xlim(sim[0] - 0.5, 90.3)
    latency_ax.set_xticks(np.arange(15, 91, 5))
    handles, labels = latency_ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower left", bbox_to_anchor=(0.079, 0.078),
               ncol=3, frameon=False, fontsize=9, handletextpad=0.4, columnspacing=1.5,
               markerscale=1.3)
    fig.text(0.083, 0.043,
             "Frequency: all 1,312 nominal starts; first partial window excluded. Simulation clock interpolated between start markers.",
             fontsize=8.5, color="#657489")
    fig.text(0.083, 0.023,
             "Latency: 1,311 completed rounds, including failures; full local-replan wall duration. Warm only = accepted warm seed without graph fallback.",
             fontsize=8.5, color="#657489")

    output_stem = OUT / "v48_planning_time_series"
    for extension in ("png", "svg", "pdf"):
        fig.savefig(output_stem.with_suffix(f".{extension}"), dpi=240, facecolor="white")
    plt.close(fig)

    frequency_rows = [{"simulation_time_s": float(x), "wall_elapsed_since_first_start_s": float(t - wall[0]),
                       "rolling_1_wall_second_hz": float(rate)} for x, t, rate in zip(grid_sim, grid, hz)]
    write_csv(OUT / "v48_frequency.csv", list(frequency_rows[0]), frequency_rows)
    latency_rows = [{"simulation_start_time_s": row["ros_s"],
                     "wall_start_elapsed_since_first_start_s": row["start_wall_s"] - wall[0],
                     "solve_ms": row["wall_s"] * 1000, "group": group(row),
                     "success": row["success"], "start_log_line": row["start_line"],
                     "end_log_line": row["end_line"]} for row in rounds]
    write_csv(OUT / "v48_round_latency.csv", list(latency_rows[0]), latency_rows)
    provenance = {
        "run": "v48_realtime_trial01", "host": "gpu5070ti",
        "inputs": [{"path": str(path.relative_to(BASE)), "sha256": sha256(path)}
                   for path in (log_path, rounds_path, metrics_path)],
        "script_sha256": sha256(Path(__file__)),
        "raw_log_crosscheck": "All 1311 completed round timestamps, latencies, success flags, and warm counters match their raw log segments.",
        "frequency_definition": "At wall time t: count nominal attempt starts in (t - 1.0 s, t] / 1.0 s. Sample every 0.05 wall seconds; append final start. Exclude the first partial window.",
        "frequency_x_definition": "Simulation clock linearly interpolated from logged start_schedule_s / ros_s pairs; no extrapolation.",
        "latency_definition": "nominal_replan_result wall_s * 1000, including failed completed rounds; x = the matching nominal start ros_s. This is full-round wall duration, not optimizer-only latency.",
        "warm_only_definition": "warm_accepts > 0 and warm_graph_fallbacks == 0; fast strictly < 10 ms.",
        "log_simulation_start_s": float(sim[0]), "log_simulation_end_s": float(sim[-1]),
        "attempt_starts": len(starts), "completed_rounds": len(rounds),
        "failed_rounds": int(failed.sum()), "overall_attempt_hz": float(attempt_hz),
        "rolling_rate_min_hz": float(hz.min()), "rolling_rate_max_hz": float(hz.max()),
        "latency_ms": computed_latency,
        "group_counts": {key: int((groups == key).sum()) for key, *_ in styles},
        "peak_round_simulation_start_s": float(round_sim[max_index]),
        "output_sha256": {path.name: sha256(path) for path in sorted(OUT.iterdir())
                          if path.suffix in (".png", ".svg", ".pdf", ".csv")},
        "rendering_versions": {"matplotlib": matplotlib.__version__, "numpy": np.__version__},
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps({"outputs": str(OUT), "attempts": len(starts), "rounds": len(rounds),
                      "overall_attempt_hz": attempt_hz, "rolling_min_max_hz": [float(hz.min()), float(hz.max())],
                      "latency_ms": computed_latency, "group_counts": provenance["group_counts"]}, indent=2))


if __name__ == "__main__":
    main()

"""Plot captured first-replan geometry; no simulated robot motion is depicted."""
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
record = json.loads((HERE / "GEOMETRY_TRACE.json").read_text())
log = (HERE / "scan25_optimizer_first_v1/replay_result/scan.log").read_text()
ts = float(re.search(r"OPT_TRACE boundary ts=([^ ]+)", log).group(1))
seed = np.array(record["points"]["seed"])
sampled = np.array(record["points"]["sampled"])


def evaluate(controls, time):
    """Same cubic knot construction and De Boor recurrence as pinned native code."""
    knots = []
    for i in range(len(controls) + 4):
        knots.append((-3 + i) * ts if i <= 3 else knots[-1] + ts)
    time = min(max(knots[3], time), knots[-4])
    k = 3
    while knots[k + 1] < time:
        k += 1
    values = [p.copy() for p in controls[k - 3:k + 1]]
    for order in range(1, 4):
        for i in range(3, order - 1, -1):
            alpha = (time - knots[i + k - 3]) / (knots[i + 1 + k - order] - knots[i + k - 3])
            values[i] = (1 - alpha) * values[i - 1] + alpha * values[i]
    return values[3]


curves, collisions = {}, {}
for stage, label in (("initial_control", "initial_fitted"), ("optimized_control", "post_optimized")):
    controls = np.array(record["points"][stage])
    # Check the plot reconstruction against directly recorded native positions.
    row = re.search(r"OPT_TRACE curve_boundary label=" + label + r" p0=\(([^)]+)\)", log)
    expected = np.array([float(v) for v in row.group(1).split(",")])
    assert np.linalg.norm(evaluate(controls, 0) - expected) < 1e-12
    collision_time = record["fitted_curve_first_collision_s" if stage == "initial_control" else "optimized_curve_first_collision_s"]
    collisions[label] = evaluate(controls, collision_time)
    native_collision = re.search(r"OPT_TRACE_DIAGNOSTIC curve=" + label + r"[^\n]*\n[^\n]*initial_spline_collision pos=\(([^)]+)\)", log)
    native_point = np.array([float(v) for v in native_collision.group(1).split(",")])
    assert np.linalg.norm(collisions[label] - native_point) < 2e-8
    curves[label] = np.array([evaluate(controls, t) for t in np.linspace(0, (len(controls) - 3) * ts, 1200)])

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [1.35, 1]})
styles = [(seed, "Checked seed (76 vertices)", "#28749c", 2.0),
          (sampled, "Old resampled chain (24 points)", "#d28a22", 1.3),
          (curves["initial_fitted"], "Initial fitted spline", "#8067a5", 1.5),
          (curves["post_optimized"], "After optimization", "#be5663", 1.5)]
for points, label, color, width in styles:
    forward = seed[0, 1] - points[:, 1]
    axes[0].plot(forward, points[:, 2], label=label, color=color, lw=width)
    axes[1].plot(forward, 100 * (points[:, 0] - seed[0, 0]), color=color, lw=width)
axes[0].scatter(seed[0, 1] - sampled[:, 1], sampled[:, 2], color="#d28a22", s=16, zorder=4)
edge = sampled[9:11]
for ax, values in ((axes[0], edge[:, 2]), (axes[1], 100 * (edge[:, 0] - seed[0, 0]))):
    ax.plot(seed[0, 1] - edge[:, 1], values, color="#c2343f", lw=4, zorder=6)
for label, color in (("initial_fitted", "#8067a5"), ("post_optimized", "#be5663")):
    p = collisions[label]
    axes[0].scatter(seed[0, 1] - p[1], p[2], marker="X", s=85, color=color, edgecolors="white", zorder=7)
axes[0].annotate("Initial spline: height rejection", (.576, .607), (.92, .47),
                 arrowprops={"arrowstyle": "->", "color": "#8067a5"}, color="#685184")
min_lateral = min(100 * (points[:, 0].min() - seed[0, 0]) for points, *_ in styles)
axes[1].annotate("Resampled edge 10 cuts across the turn\nand fails the original collision check",
                 (1.23, 2.5), (.1, min_lateral + 2),
                 arrowprops={"arrowstyle": "->", "color": "#c2343f"}, color="#a72530")
axes[0].set_ylabel("Body reference height Z (m)")
axes[1].set_ylabel("Lateral displacement X (cm)")
axes[1].set_xlabel("Forward progress from measured start, along -Y (m)")
axes[1].set_ylim(min_lateral - 2, 9)
axes[1].set_xlim(-.04, 3.82)
for ax in axes:
    ax.grid(alpha=.17)
axes[0].legend(ncol=2, loc="upper left", frameon=False)
fig.suptitle("Where the checked stair path loses safety", x=.075, ha="left", fontsize=16)
fig.text(.075, .014, "Actual native CPU replay at 5.01 s. Reference geometry only; no robot motion. X markers: first spline rejections.", fontsize=9, color="#555555")
fig.tight_layout(rect=(0, .04, 1, .95))
fig.savefig(HERE / "spline_seed_failure.png", dpi=180)
fig.savefig(HERE / "spline_seed_failure.svg")
print(HERE / "spline_seed_failure.png")

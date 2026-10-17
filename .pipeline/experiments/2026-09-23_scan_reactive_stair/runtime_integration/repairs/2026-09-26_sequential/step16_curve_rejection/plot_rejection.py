"""Show recorded rejected geometry and the paired footprint orientations."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from analyze_probe import evaluate

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "GEOMETRY.json").read_text())
result = json.loads((HERE / "RESULT.json").read_text())
seed = np.array(data["seed"])
fig = plt.figure(figsize=(12, 7))
grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.25])
overview = fig.add_subplot(grid[0, :])
overview.plot(seed[0, 1] - seed[:, 1], seed[:, 2], color="#8b969e", lw=2.5, label="Checked seed")
colors = {"timed_initial": "#16878f", "final": "#8067b3"}
for label, color in colors.items():
    curve = data[label]
    times = np.linspace(0, result[label]["duration_s"], 2500)
    xyz = np.array([evaluate(curve["controls"], curve["knots"], t) for t in times])
    overview.plot(seed[0, 1] - xyz[:, 1], xyz[:, 2], color=color, lw=1.1, label=label.replace("_", " "))
    p = result[label]["position"]
    overview.scatter(seed[0, 1] - p[1], p[2], color=color, edgecolor="white", s=65, zorder=6)
overview.set(xlabel="Forward progress along -Y (m)", ylabel="Body reference Z (m)")
overview.legend(frameon=False, ncol=3, loc="upper left")
for index, label in enumerate(colors):
    ax = fig.add_subplot(grid[1, index])
    row = result[label]
    center = np.array(row["position"][:2])
    parent = row["parent_edge"]
    local_seed = seed[max(0, parent-2):parent+3, :2] - center
    ax.plot(100 * local_seed[:, 0], 100 * local_seed[:, 1], color="#8b969e", lw=2, label="Seed centerline")
    for yaw, color, name in [(row["parent_yaw_rad"], "#2c9561", "Seed yaw: clear here"),
                             (row["curve_yaw_rad"], "#d4493f", "Curve yaw: blocked here")]:
        d = .18 * np.array([np.cos(yaw), np.sin(yaw)])
        ax.plot([-100*d[0], 100*d[0]], [-100*d[1], 100*d[1]], color=color, lw=2, label=name)
        ax.scatter([-100*d[0], 100*d[0]], [-100*d[1], 100*d[1]], color=color, s=30)
    yaw = row["curve_yaw_rad"]
    blocked_sign = 1 if label == "timed_initial" else -1
    blocked = blocked_sign * 18 * np.array([np.cos(yaw), np.sin(yaw)])
    ax.scatter(*blocked, s=130, facecolors="none", edgecolors="#d4493f", linewidth=2)
    ax.scatter(0, 0, color="#212a34", marker="x", s=45)
    ax.set_aspect("equal")
    ax.set(xlim=(-24, 24), ylim=(-24, 24), xlabel="X relative to query (cm)", ylabel="Y relative to query (cm)")
    cause = "Front: wrong support height" if label == "timed_initial" else "Rear: unknown support"
    ax.set_title(f"{label.replace('_', ' ')} | heading difference {row['heading_difference_degrees']:.2f} deg\n{cause}", fontsize=11)
for ax in fig.axes:
    ax.grid(alpha=.18)
    ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("SCAN29: why a checked seed still becomes a rejected curve", fontsize=15, x=.08, ha="left")
fig.text(.08, .03, "Green: seed heading. Red: curve heading. Circle: first rejected query center. Gray: seed centerline.", fontsize=9, color="#4c5660")
fig.text(.08, .01, "Recorded-input diagnostic, not robot motion. Dots show front/rear query centers, not the entire collision volume. Same map time: 5.57 s.", fontsize=8, color="#4c5660")
fig.tight_layout(rect=(0, .045, 1, .95))
fig.savefig(HERE / "curve_rejection.png", dpi=170)
fig.savefig(HERE / "curve_rejection.svg")
print(HERE / "curve_rejection.png")

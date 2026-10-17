"""Plot actual first-search samples; no inferred occupancy outside those samples."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
run = HERE / "scan23_first_frontier"
r = json.loads((run / "frontier_review.json").read_text())
sensor = json.loads((HERE / "sensor_blind_band.json").read_text())
y0 = r["adjusted_start_goal"][1]
rows = [v.strip().split(",") for v in (run / "replay_result/scan.log").open() if v.startswith("STF_")]
queries = {code: np.array([[float(v[5]), float(v[6])] for v in rows if v[0] == "STF_QUERY" and int(v[2]) == code])
           for code in (0, 6, 8, 10)}
fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
for code, label, color, marker in ((0, "Free query", "#b5c0c8", "."), (6, "Unknown occupancy", "#da7c30", "x"),
                                   (8, "Unknown support", "#9562a6", "+"), (10, "Height mismatch", "#ba3c48", "s")):
    a = queries[code]
    if len(a): ax.scatter(y0 - a[:, 0], a[:, 1], s=18 if code else 9, marker=marker, color=color, label=label, alpha=.65)
ground = []
path = HERE.parent / "step3_layers/native_audit_v1/scan_23_support.csv"
for v in csv.DictReader(path.open()):
    if abs(float(v["x"]) - r["adjusted_start_goal"][0]) < .05 and float(v["z"]) < .6:
        x = y0 - float(v["y"])
        if -.35 <= x <= .85: ground.append((x, float(v["z"])))
ground = np.array(sorted(ground))
ax.step(ground[:, 0], ground[:, 1], where="mid", color="#394650", linewidth=2, label="Selected ground at center X")
for v in rows:
    if v[0] == "STF_EDGE" and int(v[8]) == 1:
        ax.plot([y0 - float(v[3]), y0 - float(v[6])], [float(v[4]), float(v[7])], color="#2167ad", linewidth=1.7)
nodes = np.array(r["closest_nodes"])
ax.scatter(y0 - nodes[:, 1], nodes[:, 2], s=40, facecolors="white", edgecolors="#2167ad", linewidth=1.8,
           label="Reachable body-reference states", zorder=5)
s = sensor["last_sensor_world_xyz"]
ax.scatter([y0 - s[1]], [s[2]], marker="D", color="#111111", s=45, label="Measured LiDAR position", zorder=6)
ax.annotate("Only 0.15 m forward progress\nin this graph", (.15, nodes[0, 2]), (.31, .59),
            arrowprops={"arrowstyle": "->", "color": "#2167ad"}, color="#2167ad", fontsize=10)
ax.annotate("Raise: rear query unknown", (y0 - 5.99475788752, .437875469526), (-.29, .60),
            arrowprops={"arrowstyle": "->", "color": "#da7c30"}, fontsize=9)
ax.annotate("Level: front query too low", (y0 - 5.64309122086, .404542136192), (.43, .48),
            arrowprops={"arrowstyle": "->", "color": "#ba3c48"}, fontsize=9)
ax.set(xlim=(-.34, .85), ylim=(0, .68), xlabel="Forward distance from measured body origin (m)", ylabel="World height Z (m)",
       title="First native search: 8 reachable grid states, full target unreached")
ax.grid(alpha=.16)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(loc="lower right", fontsize=8, frameon=False)
fig.text(.01, -.025, "Actual sampled queries projected to Y/Z; lateral X differs. This is not a complete occupancy map or a physical infeasibility proof.", fontsize=8)
for suffix in ("png", "svg"):
    fig.savefig(HERE / ("first_search_frontier." + suffix), dpi=180, bbox_inches="tight")
print(HERE / "first_search_frontier.png")

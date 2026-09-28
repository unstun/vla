"""Top view of SCAN's scored walkway support near the v29 landing stall, with
the PCT route, the stuck frontier, the stopped body and the per-sample reason
from the landing replay breakdown."""
from pathlib import Path
import csv, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D

here = Path(__file__).resolve().parent
audit = here.parent
experiment = audit.parents[1]
cells = list(csv.DictReader((here / "support_cells.csv").open()))
WALK = (1.35, 1.65)  # landing 1.42, rise 1.51-1.56, upper floor 1.56-1.58
COLORS = {0: "#f0a030", 1: "#5cb85c", 2: "#9fd89f", 3: "#d9534f"}
NAMES = {0: "Unknown support", 1: "Flat", 2: "Stair", 3: "Unsupported"}

fig, ax = plt.subplots(figsize=(11, 7.2), dpi=150)
by_cell = {}
for r in cells:
    by_cell.setdefault((float(r["x0"]), float(r["y0"])), []).append(r)
for (x0, y0), layers in by_cell.items():
    walk = [r for r in layers if WALK[0] <= float(r["elevation"]) <= WALK[1]]
    if walk:
        support = int(walk[0]["support"])
        ax.add_patch(Rectangle((x0, y0), 0.1, 0.1, facecolor=COLORS[support], edgecolor="white", linewidth=0.3))
    else:
        ax.add_patch(Rectangle((x0, y0), 0.1, 0.1, facecolor="#dddddd", edgecolor="white", linewidth=0.3))

obs = [json.loads(l) for l in (experiment / "runs/v29_historical_full01/artifacts/reactive_observations.jsonl").open()]
route = next(o for o in obs if o["event"] == "pct_route")["data"]["path"]["poses"]
rx = [p["pose"]["position"]["x"] for p in route]
ry = [p["pose"]["position"]["y"] for p in route]
ax.plot(rx, ry, color="#1f3b73", linewidth=1.2, zorder=3)

rows = list(csv.DictReader((audit / "landing/result_breakdown.csv").open()))
result = json.loads((audit / "landing/result.json").read_text())
frontier = result["frontier_time_s"]
samples = {}
for r in rows:
    samples.setdefault(r["i"], {})[r["circle"]] = r
marker = {"support": ("s", "#8b0000"), "UnknownObstacle": ("x", "#6a0dad"), "free": ("o", "#1f3b73")}
for i, pair in samples.items():
    front, rear = pair["front"], pair["rear"]
    t = float(front["t"])
    deciding = front if front["native_circle"] == "1" else rear
    if front["native"] == "0":
        kind = "free"
    elif deciding["stage"].startswith("support"):
        kind = "support"
    else:
        kind = "UnknownObstacle"
    m, c = marker[kind]
    ax.plot(float(front["x"]), float(front["y"]), m, color=c, markersize=3.2 if kind != "free" else 2.5, zorder=4)

fx, fy = result["target"][0], result["target"][1]
bx, by = result["start"][0], result["start"][1]
ax.plot(fx, fy, "*", color="#ffd700", markeredgecolor="black", markersize=13, zorder=6)
ax.plot(bx, by, "o", color="white", markeredgecolor="black", markersize=7, zorder=6)
ax.annotate("frontier t=%.4f s (stuck 47.4-88.3 s)" % frontier, (fx, fy), xytext=(-5.95, -2.2), fontsize=8,
            arrowprops=dict(arrowstyle="->", linewidth=0.6))
ax.annotate("robot at 80.98 s", (bx, by), xytext=(-4.6, -2.25), fontsize=8, arrowprops=dict(arrowstyle="->", linewidth=0.6))
ax.axvline(-4.99531478882, color="black", linestyle=":", linewidth=0.6)
ax.text(-4.99, -4.78, "x=-4.995 cell edge", fontsize=7, rotation=90, va="bottom")
ax.set_xlim(-6.0, -1.5); ax.set_ylim(-4.8, -2.0); ax.set_aspect("equal")
ax.set_xlabel("world x (m)"); ax.set_ylabel("world y (m)")
ax.set_title("v29 landing stall: SCAN scored support of the 1.35-1.65 m walkway layer (pinned PCT navigation ground)", fontsize=9)
handles = [Patch(color=COLORS[k], label=NAMES[k]) for k in (1, 2, 0, 3)]
handles.append(Patch(color="#dddddd", label="cell present, no walkway layer (other floors only)"))
handles += [Line2D([], [], color="#1f3b73", label="PCT route"),
            Line2D([], [], marker="s", color="#8b0000", linestyle="", label="route sample blocked: support query"),
            Line2D([], [], marker="x", color="#6a0dad", linestyle="", label="route sample blocked: never-observed voxel"),
            Line2D([], [], marker="o", color="#1f3b73", linestyle="", label="route sample free")]
ax.legend(handles=handles, loc="lower right", fontsize=7, framealpha=0.9)
fig.tight_layout()
fig.savefig(here / "landing_support_map.png")
print("wrote", here / "landing_support_map.png")

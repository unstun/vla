"""Render compact existing geometric evidence; no additional geometry queries."""
import os
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"
os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
from pathlib import Path
import argparse
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as PatchPolygon, Rectangle
from shapely.geometry import shape


def polygons(g):
    if g.geom_type == "Polygon":
        yield g
    elif hasattr(g, "geoms"):
        for part in g.geoms:
            yield from polygons(part)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    panels = [("attempt01", "actual_final_post_pd", "A02 measured pose: target-cell overreach"),
              ("attempt03", "g07_failed_start_edge_0", "G07 edge yaw 0: target-cell overreach"),
              ("attempt03", "g07_failed_start_edge_m3pi4", "G07 edge yaw -3pi/4: source-cell conservatism"),
              ("attempt03", "g07_failed_start_edge_pi2", "G07 edge yaw pi/2: genuine missing support")]
    fig, axes = plt.subplots(2, 2, figsize=(11, 10))
    for axis, (attempt, label, title) in zip(axes.flat, panels):
        folder = args.root/attempt
        report = json.loads((folder/"geometry_report.json").read_text())
        pose = next(p for p in report["poses"] if p["label"] == label)
        geometry = json.loads((folder/(label+"_geometry.geojson")).read_text())
        support = shape(geometry["features"][0]["geometry"])
        axis.set_facecolor("#fff3e8")
        for polygon in polygons(support):
            axis.add_patch(PatchPolygon(list(polygon.exterior.coords), color="#e5eee3", zorder=0))
            for hole in polygon.interiors:
                axis.add_patch(PatchPolygon(list(hole.coords), color="#fff3e8", zorder=1))
            axis.plot(*polygon.exterior.xy, color="#53614b", lw=1)
        triggers = [r for r in json.loads((folder/"mask_trigger_sources.json").read_text()) if r["pose"] == label]
        seen = set()
        for row in triggers:
            x, y, z = row["source_xyz"]
            if (x, y, z) not in seen:
                axis.add_patch(Rectangle((x-.05, y-.05), .1, .1, fill=False, edgecolor="#c56c00", lw=1.1))
                seen.add((x, y, z))
        samples = [r for r in json.loads((folder/"mask_source_samples.json").read_text()) if r["pose"] == label and not r["present_generator_level"]]
        axis.scatter([s["x"] for s in samples], [s["y"] for s in samples], marker="x", s=9, color="#b54034", zorder=3)
        for side in pose["sides"]:
            x, y = side["center_xy"]
            color = "#1769aa" if side["continuous_disc_covered"] else "#bd2530"
            axis.add_patch(Circle((x, y), .35, fill=False, edgecolor=color, lw=1.7, zorder=4))
            axis.scatter([x], [y], color=color, s=13, zorder=5)
            bounds = side["mask_target_bounds"]
            if side["mask_blocks"]:
                axis.add_patch(Rectangle(bounds[:2], bounds[2]-bounds[0], bounds[3]-bounds[1], fill=False, edgecolor="#a6005d", lw=1, linestyle="--"))
            axis.annotate(f'{side["side"]}: {side["distance_to_uncovered_domain_m"]:.4f} m', (x, y), xytext=(4, 6), textcoords="offset points", color=color, fontsize=8)
        bx, by = pose["body_xyz"][:2]
        axis.scatter([bx], [by], marker="+", color="black", s=40, zorder=5)
        axis.set(xlim=(bx-.85, bx+.65), ylim=(by-.75, by+.75), aspect="equal", xlabel="World x (m)", ylabel="World y (m)", title=title)
        axis.grid(alpha=.18)
    fig.suptitle("Original simulator mesh, unchanged 0.35 m cylinders and measured poses", fontsize=13)
    fig.text(.5, .014, "Green = mesh support in original height band; orange squares = negative source cells; red x = failed subcell samples; dashed magenta = blocked target cells.\nLabels show center-to-uncovered-domain distance. Coverage verdict uses exact polygon-boundary distance; circles are drawn for review.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .045, 1, .965))
    fig.savefig(args.root/"mesh_mask_comparison.png", dpi=160)
    fig.savefig(args.root/"mesh_mask_comparison.svg")


if __name__ == "__main__":
    main()

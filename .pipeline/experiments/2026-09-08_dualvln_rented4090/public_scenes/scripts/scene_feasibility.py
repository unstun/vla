"""Measure whether a public test scene can host a non-degenerate VLN episode.

The official success criterion is "within 3.0 m of the goal AND the policy emitted
STOP". In a scene whose navigable extent is itself close to 3 m, almost every
reachable pose already satisfies the distance half of that test, so the episode
cannot discriminate. This runs before any instruction is written and before any
model query, and its numbers decide which scenes are usable.
"""
import argparse
import json
import math
from pathlib import Path

import habitat_sim
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SUCCESS_RADIUS = 3.0


def geo(pf, a, b):
    sp = habitat_sim.ShortestPath()
    sp.requested_start = np.array(a, dtype=np.float32)
    sp.requested_end = np.array(b, dtype=np.float32)
    if not pf.find_path(sp) or not math.isfinite(sp.geodesic_distance):
        return None
    return float(sp.geodesic_distance)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenes', nargs='+', required=True)
    ap.add_argument('--seed', type=int, default=20260909)
    ap.add_argument('--samples', type=int, default=400)
    a = ap.parse_args()

    report = {'success_radius_m': SUCCESS_RADIUS, 'seed': a.seed,
              'samples_per_scene': a.samples, 'scenes': {}}

    for scene in a.scenes:
        navmesh = ROOT / 'public_scenes/data/scene_data/public' / scene / f'{scene}.navmesh'
        pf = habitat_sim.nav.PathFinder()
        pf.load_nav_mesh(str(navmesh))
        pf.seed(a.seed)
        pts = [pf.get_random_navigable_point() for _ in range(a.samples)]
        pts = [p for p in pts if np.all(np.isfinite(p))]

        # geodesic diameter over the sample
        best = (None, None, -1.0)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                d = geo(pf, pts[i], pts[j])
                if d is not None and d > best[2]:
                    best = (i, j, d)
        i, j, diam = best

        # For the far end of that diameter, how much of the scene is already
        # "successful" without moving?
        goal = pts[j] if j is not None else pts[0]
        within = [geo(pf, p, goal) for p in pts]
        within = [d for d in within if d is not None]
        frac_already_success = sum(1 for d in within if d <= SUCCESS_RADIUS) / max(len(within), 1)

        lo, hi = pf.get_bounds()
        report['scenes'][scene] = {
            'navigable_area_m2': float(pf.navigable_area),
            'bounds_extent_m': [float(hi[k] - lo[k]) for k in range(3)],
            'sampled_points': len(pts),
            'geodesic_diameter_m': float(diam),
            'max_start_goal_distance_m': float(diam),
            'fraction_of_navigable_samples_already_within_success_radius': round(frac_already_success, 4),
            'usable_for_nondegenerate_episode': bool(diam > 2 * SUCCESS_RADIUS
                                                     and frac_already_success < 0.5),
        }
        print(f'{scene}: area={pf.navigable_area:.1f} m2 diameter={diam:.2f} m '
              f'already-within-3m={frac_already_success:.1%} '
              f'usable={report["scenes"][scene]["usable_for_nondegenerate_episode"]}')

    out = ROOT / 'public_scenes/setup/scene_feasibility.json'
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print('FEASIBILITY_WRITTEN', out.relative_to(ROOT))


if __name__ == '__main__':
    main()

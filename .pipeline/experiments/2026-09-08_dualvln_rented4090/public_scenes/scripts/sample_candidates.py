"""Enumerate navigable start/goal candidates in a public Habitat test scene.

Uses only habitat_sim's PathFinder against the downloaded .navmesh: no renderer,
no model, no simulator. Output is a deterministic, seeded candidate list that the
preview step renders before any instruction is written or any model is queried.
"""
import argparse
import json
import math
from pathlib import Path

import habitat_sim
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def geodesic(pf, a, b):
    path = habitat_sim.ShortestPath()
    path.requested_start = np.array(a, dtype=np.float32)
    path.requested_end = np.array(b, dtype=np.float32)
    ok = pf.find_path(path)
    if not ok or not math.isfinite(path.geodesic_distance):
        return None, None
    return float(path.geodesic_distance), [[float(v) for v in p] for p in path.points]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scene', required=True, help='scene stem, e.g. skokloster-castle')
    ap.add_argument('--seed', type=int, default=20260909)
    ap.add_argument('--samples', type=int, default=400)
    ap.add_argument('--geo-min', type=float, default=6.0)
    ap.add_argument('--geo-max', type=float, default=14.0)
    ap.add_argument('--keep', type=int, default=12)
    a = ap.parse_args()

    scene_dir = ROOT / 'public_scenes/data/scene_data/public' / a.scene
    navmesh = scene_dir / f'{a.scene}.navmesh'
    pf = habitat_sim.nav.PathFinder()
    pf.load_nav_mesh(str(navmesh))
    if not pf.is_loaded:
        raise SystemExit(f'navmesh failed to load: {navmesh}')

    lo, hi = pf.get_bounds()
    info = {
        'scene': a.scene,
        'navmesh': str(navmesh.relative_to(ROOT)),
        'navmesh_bounds_min': [float(v) for v in lo],
        'navmesh_bounds_max': [float(v) for v in hi],
        'navigable_area_m2': float(pf.navigable_area),
        'seed': a.seed,
        'samples': a.samples,
        'geodesic_band_m': [a.geo_min, a.geo_max],
    }

    pf.seed(a.seed)
    pts = []
    for _ in range(a.samples):
        p = pf.get_random_navigable_point()
        if not np.all(np.isfinite(p)):
            continue
        pts.append(([float(v) for v in p], int(pf.island_radius(p))))
    info['sampled_points'] = len(pts)

    # Deterministic pair enumeration: sample order is fixed by the seed above.
    cands = []
    for i, (s, s_isl) in enumerate(pts):
        for j, (g, g_isl) in enumerate(pts):
            if i == j:
                continue
            gd, path = geodesic(pf, s, g)
            if gd is None or not (a.geo_min <= gd <= a.geo_max):
                continue
            eu = float(np.linalg.norm(np.array(s) - np.array(g)))
            if eu < 1e-6:
                continue
            # keep both feet roughly on one floor: the R2R task is single-storey
            if abs(s[1] - g[1]) > 0.5:
                continue
            cands.append({
                'start_index': i,
                'goal_index': j,
                'start_position': s,
                'goal_position': g,
                'start_island_radius': s_isl,
                'goal_island_radius': g_isl,
                'geodesic_distance': gd,
                'euclidean_distance': eu,
                'tortuosity': gd / eu,
                'path_points': path,
                'n_path_points': len(path),
            })
            break  # first qualifying goal for this start, in sampled order

    # Deterministic ranking: prefer a route with at least one real turn (more path
    # points), then the longer geodesic, then the sample index. No model involved.
    cands.sort(key=lambda c: (-c['n_path_points'], -c['geodesic_distance'], c['start_index']))
    info['n_candidates'] = len(cands)
    info['candidates'] = cands[: a.keep]

    out = ROOT / 'public_scenes/setup' / f'candidates_{a.scene}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(info, indent=2, sort_keys=True) + '\n')
    print(f'{a.scene}: navigable_area={pf.navigable_area:.1f} m2 '
          f'points={len(pts)} candidates={len(cands)} kept={len(info["candidates"])}')
    for c in info['candidates'][:6]:
        print(f"  start={c['start_index']:3d} goal={c['goal_index']:3d} "
              f"geo={c['geodesic_distance']:.2f} eu={c['euclidean_distance']:.2f} "
              f"tort={c['tortuosity']:.2f} pts={c['n_path_points']}")
    print('CANDIDATES_WRITTEN', out.relative_to(ROOT))


if __name__ == '__main__':
    main()

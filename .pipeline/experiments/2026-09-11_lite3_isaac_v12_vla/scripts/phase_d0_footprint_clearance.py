"""Phase D.0a: offline footprint clearance of the Phase C runs.

    python3 phase_d0_footprint_clearance.py RUN_DIR [RUN_DIR ...] --out ../analysis/phase_d0_footprint_clearance.json

For every logged policy step, the robot footprint (a rectangle in the body frame, placed at the logged base x, y, yaw)
is compared with each landmark box footprint. Clearance is the 2D distance between the two convex polygons, negative
(minus the smallest separating-axis overlap) when they intersect. Measurement only: this is not a safety layer.

Footprints come from the pinned Lite3 URDF
(references/upstream/2026-09-11_lite3_v12_locomotion/source/v12_runtime/resources/lite3/urdf/lite3.urdf):
- torso: the torso.STL bounding box, x -0.269..0.279 m, y -0.109..0.108 m;
- legs: the same length, widened to y +-0.182 m, the outer face of the thigh collision boxes (hip-Y joint at
  y +-0.159 m plus half of the 0.045 m box). Leg swing, roll and pitch are not modelled; the log has base yaw only.
Standard library only.
"""

import argparse
import json
import math
from pathlib import Path

FOOTPRINTS = {
    'torso': (-0.269, 0.279, -0.109, 0.108),
    'legs': (-0.269, 0.279, -0.182, 0.182),
}


def rectangle(x_min, x_max, y_min, y_max):
    return [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]


def place(polygon, x, y, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return [(x + c * px - s * py, y + s * px + c * py) for px, py in polygon]


def _axes(polygon):
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
        ex, ey = x2 - x1, y2 - y1
        length = math.hypot(ex, ey)
        yield (-ey / length, ex / length)


def _point_segment(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(p[0] - qx, p[1] - qy), (qx, qy)


def signed_distance(robot, obstacle):
    """Distance between two convex polygons; negative penetration depth when they overlap. Also returns the robot
    point closest to the obstacle."""
    min_overlap = math.inf
    for axis in list(_axes(robot)) + list(_axes(obstacle)):
        pa = [v[0] * axis[0] + v[1] * axis[1] for v in robot]
        pb = [v[0] * axis[0] + v[1] * axis[1] for v in obstacle]
        overlap = min(max(pa), max(pb)) - max(min(pa), min(pb))
        if overlap < 0:
            min_overlap = None
            break
        min_overlap = min(min_overlap, overlap)
    best = (math.inf, None)
    for poly_p, poly_e, robot_side in ((robot, obstacle, True), (obstacle, robot, False)):
        for p in poly_p:
            for a, b in zip(poly_e, poly_e[1:] + poly_e[:1]):
                d, q = _point_segment(p, a, b)
                if d < best[0]:
                    best = (d, p if robot_side else q)
    if min_overlap is not None:
        return -min_overlap, best[1]
    return best[0], best[1]


def body_part(point, x, y, yaw):
    """Which part of the body the closest robot point is on, in the body frame."""
    c, s = math.cos(yaw), math.sin(yaw)
    bx = c * (point[0] - x) + s * (point[1] - y)
    by = -s * (point[0] - x) + c * (point[1] - y)
    return '{}-{}'.format('front' if bx > 0.1 else 'rear' if bx < -0.1 else 'mid', 'left' if by > 0 else 'right'), \
        (round(bx, 3), round(by, 3))


def analyse(run_dir):
    run_dir = Path(run_dir)
    episode = json.loads((run_dir / 'client' / 'client_episode.json').read_text())['episode']
    steps = [json.loads(line) for line in (run_dir / 'isaac' / 'isaac_steps.jsonl').read_text().splitlines() if line]
    boxes = {}
    for lm in episode['landmarks']:
        (cx, cy), (sx, sy) = lm['center'][:2], lm['size'][:2]
        boxes[lm['name']] = rectangle(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2)
    result = {'run': run_dir.name, 'target': episode['target_landmark'], 'steps': len(steps), 'footprints': {}}
    for name, extents in FOOTPRINTS.items():
        body = rectangle(*extents)
        best = None
        for step in steps:
            x, y, _ = step['xyz']
            placed = place(body, x, y, step['yaw'])
            for box_name, box in boxes.items():
                d, point = signed_distance(placed, box)
                if best is None or d < best['clearance_m']:
                    part, body_xy = body_part(point, x, y, step['yaw'])
                    best = {'clearance_m': round(d, 4), 'sim_s': round(step['sim_ns'] / 1e9, 2), 'landmark': box_name,
                            'body_part': part, 'body_frame_point': body_xy,
                            'base_xy_yaw_deg': [round(x, 3), round(y, 3), round(math.degrees(step['yaw']), 1)],
                            'nonfoot_substep_max_n': step.get('nonfoot_substep_max_n')}
        result['footprints'][name] = best
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('runs', nargs='+')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    results = [analyse(run) for run in args.runs]
    args.out.write_text(json.dumps(results, indent=2) + '\n')
    print('{:24s} {:>9s} {:>7s} {:>9s} {:>7s} {:>10s} {:>12s} {:>8s}'.format(
        'run', 'torso_m', 'at_s', 'legs_m', 'at_s', 'landmark', 'body_part', 'force_N'))
    for r in results:
        t, g = r['footprints']['torso'], r['footprints']['legs']
        print('{:24s} {:9.3f} {:7.2f} {:9.3f} {:7.2f} {:>10s} {:>12s} {:8.1f}'.format(
            r['run'][-24:], t['clearance_m'], t['sim_s'], g['clearance_m'], g['sim_s'], g['landmark'], g['body_part'],
            g['nonfoot_substep_max_n'] or 0.0))


if __name__ == '__main__':
    main()

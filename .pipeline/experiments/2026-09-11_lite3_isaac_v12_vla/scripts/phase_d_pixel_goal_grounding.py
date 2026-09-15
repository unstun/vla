"""Phase D (offline, no GPU): does System 2's pixel goal point at the instructed target?

    python3 phase_d_pixel_goal_grounding.py --out ../analysis/phase_d_pixel_goal_grounding

For every System 2 answer that is a pixel coordinate, in every collected Isaac VLA run (Phase C, D.0d, D.0e, D.0f):
- image: the exact frame the upstream agent saved for that call (`client/test_data/<episode dir>/debug_raw_ NNN.jpg`, or
  `..._look_down.jpg` when the decision looked down; in these runs the look-down call re-uses the level image);
- pose: that decision's `frame_odom` (world x, y, yaw at image time), matched to the answer in order, and base height
  from `isaac/isaac_steps.jsonl` at the image time;
- camera: the episode's level 640x480 HFOV 79 pinhole at its logged mount (D.0f: the fusion virtual camera).

Measured per answer:
1. target visibility, from a colour mask of the target box (HSV thresholds for the red, green and blue boxes; the grey
   box is not segmented). The box projected from the pose must overlap the mask's column span (pose cross-check);
2. bearing error: angle between the goal pixel's column ray and the direction to the target box centre (x, y, yaw
   only; body pitch and roll are not logged and do not enter);
3. image hit: goal pixel on the target mask, on another coloured box mask, or elsewhere;
4. estimated floor distance from the goal to the target centre. Pitch is unknown, so the horizon row is calibrated
   per image from the lowest row of the target mask (its nearest bottom corner at a known floor distance). Only
   computed when that corner is inside the image; roll is ignored;
5. ray miss: perpendicular distance from the target centre to the goal column ray (target distance x sin error);
6. coordinate reuse: how many runs' answers contain the exact same coordinate, and the most common coordinates of the
   Habitat castle runs for comparison (`--habitat-runs`).
"""

import argparse
import collections
import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

EXP = Path(__file__).resolve().parent.parent
RUNS = EXP / 'runs'
W, H, HFOV = 640, 480, 79.0
F = (W / 2) / math.tan(math.radians(HFOV / 2))
CX, CY = W / 2, H / 2
MIN_MASK_PX = 150
COORD = re.compile(r'(\d+) (\d+)')


def hsv_mask(hsv, name):
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    if name == 'red_box':
        return ((h < 12) | (h > 240)) & (s > 90) & (v > 80)
    if name == 'green_box':
        return (h > 70) & (h < 120) & (s > 90) & (v > 80)
    if name == 'blue_box':
        return (h > 145) & (h < 175) & (s > 180) & (v > 60)
    return None


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def camera_frame(cam_xy, yaw, point_xy):
    dx, dy = point_xy[0] - cam_xy[0], point_xy[1] - cam_xy[1]
    forward = math.cos(yaw) * dx + math.sin(yaw) * dy
    left = -math.sin(yaw) * dx + math.cos(yaw) * dy
    return forward, left


def box_corners(lm):
    cx, cy = lm['center'][:2]
    sx, sy = lm['size'][0] / 2, lm['size'][1] / 2
    return [(cx + a * sx, cy + b * sy) for a in (-1, 1) for b in (-1, 1)]


def answers_for_run(run_dir):
    dirs = sorted(p for p in (run_dir / 'client' / 'test_data').iterdir() if p.is_dir())
    episode_dir = dirs[-1]           # the first directory is the warm-up call before reset()
    files = []
    for path in sorted(episode_dir.glob('llm_output_*.txt')):
        text = path.read_text().strip()
        if COORD.fullmatch(text):
            files.append((int(path.stem.split('_')[-1]), text))
    decisions = [d for d in rows(run_dir / 'client' / 'decisions.jsonl')
                 if d.get('llm_output') and COORD.fullmatch(d['llm_output'].strip())]
    if [t for _, t in files] != [d['llm_output'].strip() for d in decisions]:
        raise RuntimeError('{}: answer files and decisions do not match in order'.format(run_dir.name))
    return episode_dir, list(zip(files, decisions))


def base_height_at(steps, sim_ns):
    best = min(steps, key=lambda s: abs(s['sim_ns'] - sim_ns))
    return best['xyz'][2]


def analyse_answer(run, episode, camera_pos, steps, episode_dir, index, text, decision):
    col, row = (int(v) for v in text.split())
    suffix = '_look_down' if decision.get('looked_down') else ''
    image_path = episode_dir / 'debug_raw_{: 04d}{}.jpg'.format(index, suffix)
    image = Image.open(image_path).convert('RGB')
    if image.size != (W, H):
        raise RuntimeError('{}: unexpected size {}'.format(image_path, image.size))
    hsv = np.asarray(image.convert('HSV')).astype(int)
    x, y, yaw = decision['frame_odom']
    cam_xy = (x + math.cos(yaw) * camera_pos[0] - math.sin(yaw) * camera_pos[1],
              y + math.sin(yaw) * camera_pos[0] + math.cos(yaw) * camera_pos[1])
    cam_h = base_height_at(steps, decision['image_sim_ns']) + camera_pos[2]
    target = episode['target_landmark']
    landmarks = {lm['name']: lm for lm in episode['landmarks']}

    masks = {name: hsv_mask(hsv, name) for name in landmarks}
    visible = {}
    for name, mask in masks.items():
        if mask is None:
            continue
        area = int(mask.sum())
        cols = np.where(mask.any(axis=0))[0]
        corners = [camera_frame(cam_xy, yaw, c) for c in box_corners(landmarks[name])]
        in_front = [(f, l) for f, l in corners if f > 0.05]
        projected_cols = sorted(CX - F * l / f for f, l in in_front) if in_front else []
        overlap = None
        if area >= MIN_MASK_PX and projected_cols:
            lo, hi = max(cols.min(), projected_cols[0]), min(cols.max(), projected_cols[-1])
            overlap = bool(hi >= lo)
        visible[name] = {'mask_px': area, 'visible': area >= MIN_MASK_PX,
                         'mask_cols': [int(cols.min()), int(cols.max())] if area else None,
                         'projected_cols': [round(projected_cols[0], 1), round(projected_cols[-1], 1)]
                         if projected_cols else None, 'projection_overlaps_mask': overlap}

    tf, tl = camera_frame(cam_xy, yaw, landmarks[target]['center'][:2])
    target_bearing = math.degrees(math.atan2(tl, tf))
    goal_bearing = math.degrees(math.atan2(CX - col, F))
    bearing_error = (goal_bearing - target_bearing + 180) % 360 - 180
    target_half_width_deg = math.degrees(math.asin(min(1.0, 0.3 * math.sqrt(2) / max(math.hypot(tf, tl), 0.43))))

    hit = 'elsewhere'
    for name, mask in masks.items():
        if mask is not None and mask[min(row, H - 1), min(col, W - 1)]:
            hit = 'target' if name == target else 'other_box'

    estimate = None
    tv = visible.get(target)
    if tv and tv['visible']:
        mask = masks[target]
        lowest_row = int(np.where(mask.any(axis=1))[0].max())
        corners = [camera_frame(cam_xy, yaw, c) for c in box_corners(landmarks[target])]
        nearest_f, nearest_l = min(corners, key=lambda c: c[0])
        nearest_col = CX - F * nearest_l / nearest_f if nearest_f > 0.05 else None
        if lowest_row < H - 3 and nearest_col is not None and 3 <= nearest_col <= W - 3:
            horizon = lowest_row - F * cam_h / nearest_f
            if row > horizon + 2:
                goal_forward = F * cam_h / (row - horizon)
                goal_left = (CX - col) * goal_forward / F
                gx = cam_xy[0] + math.cos(yaw) * goal_forward - math.sin(yaw) * goal_left
                gy = cam_xy[1] + math.sin(yaw) * goal_forward + math.cos(yaw) * goal_left
                estimate = {'horizon_row': round(horizon, 1), 'goal_forward_m': round(goal_forward, 2),
                            'goal_world_xy': [round(gx, 2), round(gy, 2)],
                            'target_forward_m': round(tf, 2),
                            'goal_to_target_centre_m': round(math.dist((gx, gy), landmarks[target]['center'][:2]), 2)}
            else:
                estimate = {'horizon_row': round(horizon, 1), 'goal_at_or_above_horizon': True}

    return {
        'run': run, 'answer_index': index, 'decision': decision['decision'], 'text': text, 'col': col, 'row': row,
        'image': str(image_path.relative_to(RUNS)), 'looked_down': bool(decision.get('looked_down')),
        'camera_xy': [round(cam_xy[0], 3), round(cam_xy[1], 3)], 'yaw': round(yaw, 4), 'camera_height_m': round(cam_h, 3),
        'target': target, 'target_distance_m': round(math.hypot(tf, tl), 2), 'target_in_front': tf > 0,
        'target_bearing_deg': round(target_bearing, 1), 'goal_bearing_deg': round(goal_bearing, 1),
        'bearing_error_deg': round(bearing_error, 1), 'target_half_width_deg': round(target_half_width_deg, 1),
        'boxes': visible, 'hit': hit, 'distance_estimate': estimate,
    }


def run_family(name):
    if name.startswith('phase_c_'):
        return 'C (ideal camera)'
    if 'fused' in name:
        return 'D.0f (fused camera)'
    if 'behind_box' in name:
        return 'D.0e (ideal, goal behind box)'
    return 'D.0d (ideal camera)'


def summarise(answers):
    visible = [a for a in answers if a['boxes'].get(a['target'], {}).get('visible')]
    hidden = [a for a in answers if a not in visible]
    pose_checked = [a for a in visible if a['boxes'][a['target']]['projection_overlaps_mask']]
    abs_err = [abs(a['bearing_error_deg']) for a in visible]
    miss = [a['target_distance_m'] * math.sin(math.radians(min(abs(a['bearing_error_deg']), 90))) for a in visible]
    on_span = [a for a in visible if abs(a['bearing_error_deg']) <= a['target_half_width_deg']]
    distance = [a['distance_estimate']['goal_to_target_centre_m'] for a in visible
                if a['distance_estimate'] and 'goal_to_target_centre_m' in a['distance_estimate']]
    other_visible = [a for a in visible if any(v['visible'] for n, v in a['boxes'].items() if n != a['target'])]

    def closer_to_other(a):
        for name, v in a['boxes'].items():
            if name != a['target'] and v['visible'] and v['mask_cols']:
                centre = (v['mask_cols'][0] + v['mask_cols'][1]) / 2
                if abs(a['col'] - centre) < abs(a['col'] - (a['boxes'][a['target']]['mask_cols'][0]
                                                           + a['boxes'][a['target']]['mask_cols'][1]) / 2):
                    return True
        return False

    return {
        'answers': len(answers),
        'target_visible': len(visible),
        'target_not_visible': len(hidden),
        'pose_cross_check_overlap': '{} of {}'.format(len(pose_checked), len(visible)),
        'visible_median_abs_bearing_error_deg': round(float(np.median(abs_err)), 1) if abs_err else None,
        'visible_abs_bearing_error_deg_min_q1_q3_max': [round(float(v), 1) for v in np.percentile(abs_err, [0, 25, 75, 100])]
        if abs_err else None,
        'visible_median_ray_miss_m': round(float(np.median(miss)), 2) if miss else None,
        'visible_goal_column_within_target_angular_width': '{} of {}'.format(len(on_span), len(visible)),
        'visible_goal_pixel_on_target_mask': sum(a['hit'] == 'target' for a in visible),
        'visible_goal_pixel_on_other_box_mask': sum(a['hit'] == 'other_box' for a in visible),
        'visible_with_another_box_visible': len(other_visible),
        'of_those_goal_column_closer_to_another_box': sum(closer_to_other(a) for a in other_visible),
        'distance_estimates': len(distance),
        'median_goal_to_target_centre_m': round(float(np.median(distance)), 2) if distance else None,
        'goal_within_1m_of_target_centre': sum(d <= 1.0 for d in distance),
        'goal_within_3m_of_target_centre': sum(d <= 3.0 for d in distance),
    }


def contact_sheet(answers, out, per_row=5, scale=0.5):
    tile_w, tile_h = int(W * scale), int(H * scale) + 28
    sheet = Image.new('RGB', (tile_w * per_row, tile_h * math.ceil(len(answers) / per_row)), (255, 255, 255))
    for i, a in enumerate(answers):
        image = Image.open(RUNS / a['image']).convert('RGB')
        draw = ImageDraw.Draw(image)
        draw.ellipse((a['col'] - 10, a['row'] - 10, a['col'] + 10, a['row'] + 10), outline=(255, 255, 0), width=4)
        draw.line((a['col'], 0, a['col'], H), fill=(255, 255, 0), width=1)
        tile = image.resize((tile_w, tile_h - 28))
        x, y = (i % per_row) * tile_w, (i // per_row) * tile_h
        sheet.paste(tile, (x, y + 28))
        d = ImageDraw.Draw(sheet)
        est = a['distance_estimate'] or {}
        d.text((x + 3, y + 2), '{} #{} "{}" {}'.format(a['run'].replace('phase_', ''), a['answer_index'], a['text'],
                                                      a['target']), fill=(0, 0, 0))
        d.text((x + 3, y + 14), 'target {:.1f} m, bearing err {:+.1f} deg, hit {}, goal-target {} m'.format(
            a['target_distance_m'], a['bearing_error_deg'], a['hit'], est.get('goal_to_target_centre_m', '-')),
            fill=(0, 0, 0))
    sheet.save(out)


def habitat_coordinate_counts(runs_root):
    """Pixel goals of the Habitat castle runs (camera ablation and public eval), same 640x480 model input."""
    counts, contexts, total = collections.Counter(), collections.defaultdict(set), 0
    for trace in sorted(runs_root.glob('*/trace_0/*.jsonl')):
        condition = trace.parts[-3].rsplit('_v', 1)[0]
        for record in rows(trace):
            if record['record'] == 'pixel_goal':
                if record['model_input_image_size'] != [W, H]:
                    raise RuntimeError('{}: unexpected model input size'.format(trace))
                text = '{} {}'.format(*record['raw_coords_from_text'])
                counts[text] += 1
                contexts[text].add((condition, trace.name))
                total += 1
    return {'runs_root': str(runs_root.relative_to(EXP.parent)), 'runs': len({t.parts[-3] for t in runs_root.glob('*/trace_0/*.jsonl')}),
            'pixel_goals': total, 'distinct': len(counts), 'most_common': counts.most_common(10),
            'condition_episode_pairs_for_most_common': {k: len(contexts[k]) for k, _ in counts.most_common(10)}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--habitat-runs', type=Path,
                        default=EXP.parent / '2026-09-08_dualvln_rented4090' / 'public_scenes' / 'runs')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    answers = []
    for run_dir in sorted(RUNS.glob('phase_[cd]_*')):
        if not (run_dir / 'client' / 'test_data').is_dir() or not (run_dir / 'isaac' / 'isaac_episode.json').exists():
            continue
        record = json.loads((run_dir / 'isaac' / 'isaac_episode.json').read_text())
        episode = record['episode']
        camera = episode['camera']
        if (camera['width'], camera['height'], camera['hfov'], camera['pitch_up']) != (W, H, HFOV, 0.0):
            raise RuntimeError('{}: camera is not the level 640x480 HFOV 79 view'.format(run_dir.name))
        camera_pos = record['fusion']['config']['virtual']['pos'] if 'fusion' in record else camera['pos']
        steps = rows(run_dir / 'isaac' / 'isaac_steps.jsonl')
        episode_dir, pairs = answers_for_run(run_dir)
        for (index, text), decision in pairs:
            answers.append(analyse_answer(run_dir.name, episode, camera_pos, steps, episode_dir, index, text, decision))

    reuse = collections.defaultdict(set)
    for a in answers:
        reuse[a['text']].add(a['run'])
    for a in answers:
        a['same_coordinate_in_other_runs'] = len(reuse[a['text']]) - 1

    families = collections.defaultdict(list)
    for a in answers:
        families[run_family(a['run'])].append(a)
    counts = collections.Counter(a['text'] for a in answers)
    result = {
        'camera_model': {'width': W, 'height': H, 'hfov_deg': HFOV, 'f_px': round(F, 2), 'pitch': 'level mount; body '
                         'pitch/roll not logged'},
        'runs': sorted({a['run'] for a in answers}),
        'summary_all': summarise(answers),
        'summary_by_family': {k: summarise(v) for k, v in sorted(families.items())},
        'coordinate_reuse': {'distinct': len(counts), 'answers': len(answers),
                             'answers_whose_coordinate_appears_in_another_run':
                                 sum(a['same_coordinate_in_other_runs'] > 0 for a in answers),
                             'most_common': counts.most_common(8)},
        'habitat_coordinate_reuse': habitat_coordinate_counts(args.habitat_runs),
        'answers': answers,
    }
    (args.out / 'pixel_goal_grounding.json').write_text(json.dumps(result, indent=1) + '\n')
    visible = [a for a in answers if a['boxes'].get(a['target'], {}).get('visible')]
    contact_sheet(visible, args.out / 'fig_target_visible_answers.jpg')
    print(json.dumps({k: v for k, v in result.items() if k != 'answers'}, indent=1))


if __name__ == '__main__':
    main()

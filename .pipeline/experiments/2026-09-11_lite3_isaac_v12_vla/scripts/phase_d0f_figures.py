"""Phase D.0f: figures and a video for the fused-camera runs, from the collected run directories only.

    python3 phase_d0f_figures.py --out ../analysis/phase_d0f_figures [--pairs FUSED_RUN:IDEAL_RUN ...]

- fig0 (preflight): for saved decision images of the scripted preflight, the ideal head_eval render, the fused image the
  model received, the coverage map, |ideal - fused| x8, and the two raw renders it was fused from
  (`isaac/fusion/image_NNNN_*`, all saved losslessly by the server).
- fig1 (VLA): one column per pair. Rows: the first System 2 decision image of the ideal-camera run (D.0d) and of the
  fused run (D.0f), each with its pixel goal as logged by the client; then both base paths over the layout, with the
  success radius and each run's outcome.
- video1: per fused run, the fused head view (`isaac/frames/fused_*.jpg`) beside the chase camera, with a banner.
Requires matplotlib, numpy, Pillow and OpenCV; ffmpeg re-encodes the video to H.264.
"""

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                           # noqa: E402
import numpy as np                                                         # noqa: E402
from PIL import Image, ImageDraw                                           # noqa: E402

from phase_d0c_figures import RUNS, Run, banner, draw_box, rows, write_video   # noqa: E402

IDEAL, FUSED = '#1f77b4', '#e67e22'
COVERAGE_COLOURS = np.array([[0, 0, 0], [70, 130, 200], [220, 120, 40], [240, 220, 60]], np.uint8)


def preflight_panel(run_dir, index, out):
    stem = run_dir / 'isaac' / 'fusion' / 'image_{:04d}'.format(index)
    ideal = Image.open(str(stem) + '_ideal.png').convert('RGB')
    fused = Image.open(str(stem) + '_fused.png').convert('RGB')
    coverage = Image.fromarray(COVERAGE_COLOURS[np.asarray(Image.open(str(stem) + '_coverage.png'))])
    diff = np.abs(np.asarray(ideal, np.int16) - np.asarray(fused, np.int16)).mean(axis=2)
    diff = Image.fromarray(np.clip(diff * 8, 0, 255).astype(np.uint8)).convert('RGB')
    head = Image.open(str(stem) + '_head.png').convert('RGB').resize((640, 360))
    d435 = Image.open(str(stem) + '_d435.png').convert('RGB').resize((640, 360))
    canvas = Image.new('RGB', (640 * 4, 480 + 360 + 40), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    for i, (image, label) in enumerate(((ideal, 'ideal head_eval render'), (fused, 'fused image (sent to the model)'),
                                        (coverage, 'coverage: blue head, orange D435i, yellow blend, black none'),
                                        (diff, '|ideal - fused| x8'))):
        canvas.paste(image, (640 * i, 20))
        draw.text((640 * i + 5, 4), label, fill=(0, 0, 0))
    canvas.paste(head, (0, 520))
    draw.text((5, 504), 'built-in head camera 1280x720, HFOV 105, +16.7 deg (resized for display)', fill=(0, 0, 0))
    canvas.paste(d435, (640, 520))
    draw.text((645, 504), 'D435i colour 1280x720, HFOV 69, -20 deg (resized for display)', fill=(0, 0, 0))
    canvas.save(out)


def first_decision(run):
    decisions = rows(run.dir / 'client' / 'decisions.jsonl')
    return next(d for d in decisions if d.get('llm_output'))


def decision_axis(ax, run, label, colour):
    first = first_decision(run)
    ax.imshow(np.asarray(Image.open(run.dir / 'client' / 'decision_frames' /
                                    'decision_{:04d}.jpg'.format(first['decision']))))
    if first.get('pixel_goal'):
        row_px, col_px = first['pixel_goal']
        ax.plot(col_px, row_px, marker='x', ms=14, mew=3, color=colour)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title('{} ({}): decision {} image\nfirst action {}, answer "{}"'.format(
        label, run.name, first['decision'], first['first_action'], first['llm_output']), fontsize=8)


def outcome_text(run):
    target = run.episode['target_landmark']
    centre = next(lm['center'][:2] for lm in run.episode['landmarks'] if lm['name'] == target)
    closest = min(math.dist(p, centre) for p in run.xy)
    return '{} {:.0f} s, success {}, oracle {} ({:.2f} m)'.format(
        run.record['termination'], run.t[-1], run.client['success'], closest <= run.episode['success_radius_m'], closest)


def vla_pairs_figure(pairs, out):
    fig = plt.figure(figsize=(6 * len(pairs), 15))
    grid = fig.add_gridspec(3, len(pairs), height_ratios=[1.0, 1.0, 1.6], hspace=0.35, wspace=0.18)
    for col, (fused, ideal) in enumerate(pairs):
        decision_axis(fig.add_subplot(grid[0, col]), ideal, 'ideal camera, D.0d', IDEAL)
        decision_axis(fig.add_subplot(grid[1, col]), fused, 'fused camera, D.0f', FUSED)
        ax = fig.add_subplot(grid[2, col])
        for name, box in fused.boxes.items():
            draw_box(ax, box, name)
        target = fused.episode['target_landmark']
        centre = next(lm['center'][:2] for lm in fused.episode['landmarks'] if lm['name'] == target)
        ax.add_patch(plt.Circle(centre, fused.episode['success_radius_m'], fill=False, color='k', lw=0.8, ls=':'))
        for run, colour, label, style in ((ideal, IDEAL, 'ideal (D.0d)', '--'), (fused, FUSED, 'fused (D.0f)', '-')):
            ax.plot(run.xy[:, 0], run.xy[:, 1], color=colour, lw=1.5, ls=style,
                    label='{}: {}'.format(label, outcome_text(run)))
            ax.plot(*run.xy[-1], marker='o', ms=6, color=colour)
        corners = [p for box in fused.boxes.values() for p in box]
        xy = np.vstack([ideal.xy, fused.xy, np.array(corners)])
        ax.set_xlim(xy[:, 0].min() - 0.8, xy[:, 0].max() + 0.8)
        ax.set_ylim(xy[:, 1].min() - 0.8, xy[:, 1].max() + 0.8)
        ax.set_aspect('equal')
        ax.grid(alpha=0.3)
        ax.set_xlabel('world x (m)')
        ax.set_ylabel('world y (m)')
        ax.set_title('"{}"'.format(fused.episode['instruction']), fontsize=9)
        ax.legend(fontsize=7, loc='upper center', bbox_to_anchor=(0.5, -0.1))
    fig.savefig(out, dpi=110, bbox_inches='tight')
    plt.close(fig)


def fused_video(runs, out_path):
    frames = []
    for run in runs:
        steps = sorted(int(p.stem.split('_')[1]) for p in (run.sim_dir / 'frames').glob('fused_*.jpg'))
        for step in steps:
            fused = np.asarray(Image.open(run.sim_dir / 'frames' / 'fused_{:06d}.jpg'.format(step)))[..., ::-1]
            chase = np.asarray(Image.open(run.sim_dir / 'frames' / 'chase_{:06d}.jpg'.format(step)))[..., ::-1]
            chase = np.asarray(Image.fromarray(chase).resize((int(chase.shape[1] * 480 / chase.shape[0]), 480)))
            frame = np.concatenate([banner(np.ascontiguousarray(fused), '{} fused view (what the model sees) t={:.1f} s'.format(
                run.name, step * 0.02)), banner(np.ascontiguousarray(chase), 'chase camera')], axis=1)
            frames.append(frame)
    write_video(frames, out_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--preflight', default='phase_d_fused_scripted_preflight_v3')
    parser.add_argument('--pairs', nargs='*', default=[], help='FUSED_RUN:IDEAL_RUN')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    preflight = RUNS / args.preflight
    for fused_path in sorted((preflight / 'isaac' / 'fusion').glob('image_*_fused.png')):
        index = int(fused_path.name.split('_')[1])
        preflight_panel(preflight, index, args.out / 'fig0_preflight_v3_image_{:04d}_ideal_fused_coverage.png'.format(index))
    if args.pairs:
        pairs = [(Run(f), Run(i)) for f, i in (p.split(':') for p in args.pairs)]
        vla_pairs_figure(pairs, args.out / 'fig1_d0f_fused_vs_ideal_first_decision_and_paths.png')
        fused_video([f for f, _ in pairs], args.out / 'video1_d0f_fused_view_and_chase.mp4')


if __name__ == '__main__':
    main()

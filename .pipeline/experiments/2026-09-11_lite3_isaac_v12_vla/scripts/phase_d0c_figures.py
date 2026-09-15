"""Phase D.0c: figures and videos for the scripted collision-monitor runs, from the collected run directories only.

    python3 phase_d0c_figures.py --out ../analysis/phase_d0c_figures

Everything drawn comes from logs written by the runs themselves:
- simulator step logs (`sim/isaac_steps.jsonl`): base x, y, yaw, body velocity, applied command, every 20 ms;
- relay tick logs (`relay/relay_ticks.jsonl`): command in, command out of Nav2, cloud-perceived clearance, cloud age;
- chase-camera frames rendered by Isaac (`sim/frames/chase_*.jpg`, every 5 policy steps), pasted unmodified apart from
  a text banner.
Ground-truth clearance is the D.0a leg-width rectangle against the box footprint (phase_d0_footprint_clearance.py).
Requires matplotlib, numpy, Pillow and OpenCV; ffmpeg re-encodes the videos to H.264.
"""

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                           # noqa: E402
import numpy as np                                                         # noqa: E402
from matplotlib.patches import Polygon as PolygonPatch                    # noqa: E402
from PIL import Image                                                      # noqa: E402

from phase_d0_footprint_clearance import FOOTPRINTS, place, rectangle, signed_distance   # noqa: E402

EXP = Path(__file__).resolve().parent.parent
RUNS = EXP / 'runs'
LEGS = rectangle(*FOOTPRINTS['legs'])
APPROACH = [(0.329, 0.232), (0.329, -0.232), (-0.319, -0.232), (-0.319, 0.232)]   # collision_monitor_lite3.yaml
STOP = [(0.309, 0.212), (0.309, -0.212), (-0.299, -0.212), (-0.299, 0.212)]
STEP_S = 0.02
WITHOUT, WITH, GREY = '#c0392b', '#1f77b4', '#7f7f7f'


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class Run:
    def __init__(self, name):
        self.name = name
        self.dir = RUNS / name
        command = (self.dir / 'command.txt').read_text().split()
        self.vla = (self.dir / 'isaac').is_dir()      # D.0d episodes keep Phase C's layout (isaac/, client/)
        self.sim_dir = self.dir / ('isaac' if self.vla else 'sim')
        episode = json.loads((EXP / 'phase_c' / 'episodes' / command[2 if self.vla else 4]).read_text())
        self.episode = episode
        self.client = json.loads((self.dir / 'client' / 'client_episode.json').read_text()) if self.vla else None
        self.boxes = {lm['name']: rectangle(lm['center'][0] - lm['size'][0] / 2, lm['center'][0] + lm['size'][0] / 2,
                                            lm['center'][1] - lm['size'][1] / 2, lm['center'][1] + lm['size'][1] / 2)
                      for lm in episode['landmarks']}
        self.steps = rows(self.sim_dir / 'isaac_steps.jsonl')
        self.ticks = rows(self.dir / 'relay' / 'relay_ticks.jsonl')
        self.record = json.loads((self.sim_dir / 'isaac_episode.json').read_text())
        self.t = np.array([s['sim_ns'] / 1e9 for s in self.steps])
        self.xy = np.array([s['xyz'][:2] for s in self.steps])
        self.yaw = np.array([s['yaw'] for s in self.steps])
        self.vx = np.array([s['vel_body'][0] for s in self.steps])
        self.clearance = np.array([min(signed_distance(place(LEGS, x, y, a), box)[0] for box in self.boxes.values())
                                   for (x, y), a in zip(self.xy, self.yaw)])
        self.tick_t = np.array([t['sim_ns'] / 1e9 for t in self.ticks])
        self.v_in = np.array([t['in'][0] for t in self.ticks])
        self.v_out = np.array([t['out'][0] for t in self.ticks])
        self.perceived = np.array([np.nan if t.get('cloud_min_leg_clearance_m') is None
                                   else t['cloud_min_leg_clearance_m'] for t in self.ticks])
        self.cloud_age = np.array([np.nan if t.get('last_published_cloud_age_ms') is None
                                   else t['last_published_cloud_age_ms'] / 1e3 for t in self.ticks])
        changed = [t for t in self.ticks if any(abs(a - b) > 1e-9 for a, b in zip(t['in'], t['out']))]
        self.first_change_s = changed[0]['sim_ns'] / 1e9 if changed else None
        self.contact = self.record['termination'] == 'nonfoot_contact'

    def index_at(self, seconds):
        return int(np.clip(np.searchsorted(self.t, seconds - 1e-9), 0, len(self.t) - 1))

    def frame(self, seconds, crop=None):
        step = min(int(round(seconds / STEP_S / 5)) * 5, int(round(self.t[-1] / STEP_S)) // 5 * 5)
        path = self.sim_dir / 'frames' / 'chase_{:06d}.jpg'.format(max(step, 5))
        image = np.asarray(Image.open(path))
        if crop is not None:                       # (x0, y0, x1, y1) in pixels; a crop only, no resampling
            image = image[crop[1]:crop[3], crop[0]:crop[2]]
        return image, max(step, 5) * STEP_S


def draw_box(ax, box, name):
    ax.add_patch(PolygonPatch(box, closed=True, facecolor={'red_box': '#e74c3c', 'blue_box': '#3b6fd6',
                                                           'green_box': '#2e9e44', 'grey_box': '#8c8c8c'}[name],
                              alpha=0.85, edgecolor='k'))


def draw_footprint(ax, run, i, color, lw=1.0, alpha=1.0, fill=False, label=None, zones=False):
    x, y = run.xy[i]
    ax.add_patch(PolygonPatch(place(LEGS, x, y, run.yaw[i]), closed=True, fill=fill, facecolor=color, edgecolor=color,
                              lw=lw, alpha=alpha, label=label))
    if zones:
        ax.add_patch(PolygonPatch(place(APPROACH, x, y, run.yaw[i]), closed=True, fill=False, edgecolor=color, lw=0.8,
                                  ls='--', alpha=0.9, label='approach zone (+0.05 m)'))
        ax.add_patch(PolygonPatch(place(STOP, x, y, run.yaw[i]), closed=True, fill=False, edgecolor=color, lw=0.8,
                                  ls=':', alpha=0.9, label='stop zone (+0.03 m)'))


def topdown(ax, runs_colors, xlim, ylim, title, every_s=0.5, zones_on=None, legend_loc='best'):
    for name, box in runs_colors[0][0].boxes.items():
        draw_box(ax, box, name)
    for run, color, label in runs_colors:
        ax.plot(run.xy[:, 0], run.xy[:, 1], color=color, lw=1.4, label=label + ' base path')
        for s in np.arange(0.0, run.t[-1], every_s):
            i = run.index_at(s)
            if xlim[0] - 0.5 < run.xy[i, 0] < xlim[1] + 0.5 and ylim[0] - 0.5 < run.xy[i, 1] < ylim[1] + 0.5:
                draw_footprint(ax, run, i, color, lw=0.6, alpha=0.35)
        end_label = '{} leg footprint at {} ({:.2f} s)'.format(
            label, 'contact' if run.contact else 'end', run.t[-1])
        draw_footprint(ax, run, len(run.t) - 1, color, lw=2.0, fill=True, alpha=0.35, label=end_label,
                       zones=(zones_on is run))
        if run.first_change_s is not None:
            i = run.index_at(run.first_change_s)
            ax.plot(*run.xy[i], marker='o', ms=7, mfc='white', mec=color, mew=2, ls='none',
                    label='{} monitor first acts ({:.1f} s)'.format(label, run.first_change_s))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect('equal')
    ax.grid(alpha=0.3)
    ax.set_xlabel('world x (m)')
    ax.set_ylabel('world y (m)')
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=6 if legend_loc != 'best' else 7, loc=legend_loc)


def banner(image, text, color=(255, 255, 255), bg=(0, 0, 0)):
    out = image.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 26), bg, -1)
    cv2.putText(out, text, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    return out


def green_pair_figure(g1b, g2, out):
    fig = plt.figure(figsize=(16, 13))
    grid = fig.add_gridspec(4, 5, height_ratios=[1, 1, 2.2, 1.6], hspace=0.35, wspace=0.12)
    times = [14.0, g2.first_change_s, 16.0, 16.8, 17.96]
    for row, (run, color, label) in enumerate(((g1b, WITHOUT, 'WITHOUT monitor (G1b)'),
                                                (g2, WITH, 'WITH monitor (G2)'))):
        for col, seconds in enumerate(times):
            ax = fig.add_subplot(grid[row, col])
            ax.set_xticks([])
            ax.set_yticks([])
            if seconds > run.t[-1] + 1e-6:
                ax.set_facecolor('#eeeeee')
                ax.text(0.5, 0.5, 'episode over:\nnon-foot contact\nat {:.2f} s'.format(run.t[-1]), ha='center',
                        va='center', color=WITHOUT, fontsize=11, transform=ax.transAxes)
            else:
                image, frame_s = run.frame(seconds, crop=(170, 70, 570, 320))
                ax.imshow(image)
                i = run.index_at(frame_s)
                ax.set_title('t = {:.2f} s   clearance {:+.3f} m'.format(frame_s, run.clearance[i]), fontsize=8)
            if col == 0:
                ax.set_ylabel(label, fontsize=10, color=color)
            for spine in ax.spines.values():
                spine.set_edgecolor(color)
                spine.set_linewidth(2)
    fig.text(0.5, 0.965, 'Green-episode replay: same commands, same server (b976284d). Isaac chase camera, cropped '
             '(not resampled); clearance = D.0a leg footprint vs box', ha='center', fontsize=12)

    ax = fig.add_subplot(grid[2, 0:2])
    topdown(ax, [(g1b, WITHOUT, 'G1b'), (g2, WITH, 'G2')], (1.85, 3.05), (1.95, 3.0),
            'Zoom at the blue box west edge (x = 2.70). Paths identical until 15.2 s (blue drawn over red)',
            every_s=0.5, zones_on=g2, legend_loc='lower right')
    corner = place(LEGS, *g1b.xy[-1], g1b.yaw[-1])[1]
    ax.annotate('G1b front-right corner at contact\n({:.2f}, {:.2f}): 0.03 m inside the box'.format(*corner), corner,
                xytext=(2.25, 2.9), fontsize=7, color=WITHOUT, arrowprops={'arrowstyle': '->', 'color': WITHOUT})
    ax = fig.add_subplot(grid[2, 2:5])
    topdown(ax, [(g1b, WITHOUT, 'G1b'), (g2, WITH, 'G2')], (-0.4, 4.6), (-0.8, 3.3),
            'Whole path (footprints every 0.5 s)', every_s=1.0)

    ax = fig.add_subplot(grid[3, 0:2])
    ax.step(g2.tick_t, g2.v_in, where='post', color=GREY, lw=1.2, label='command from replay (in)')
    ax.step(g2.tick_t, g2.v_out, where='post', color=WITH, lw=1.6, label='G2 command after monitor (out)')
    ax.plot(g1b.t, g1b.vx, color=WITHOUT, lw=0.8, alpha=0.8, label='G1b body forward speed')
    ax.plot(g2.t, g2.vx, color=WITH, lw=0.8, alpha=0.6, ls='--', label='G2 body forward speed')
    ax.axvline(g2.first_change_s, color=WITH, lw=0.8, ls=':')
    ax.axvline(g1b.t[-1], color=WITHOUT, lw=0.8, ls=':')
    ax.set_xlim(12, 18.2)
    ax.set_xlabel('simulated time (s)')
    ax.set_ylabel('forward speed (m/s)')
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    ax.set_title('Speed: the monitor scales the replayed command from 15.2 s', fontsize=10)

    ax = fig.add_subplot(grid[3, 2:5])
    ax.plot(g1b.t, g1b.clearance, color=WITHOUT, lw=1.5, label='G1b ground-truth leg-footprint clearance')
    ax.plot(g2.t, g2.clearance, color=WITH, lw=1.5, label='G2 ground-truth leg-footprint clearance')
    ax.plot(g2.tick_t, g2.perceived, color=WITH, lw=0, marker='.', ms=4, label='G2 clearance seen in the LiDAR cloud')
    ax.axhline(0.0, color='k', lw=1)
    ax.axvline(g2.first_change_s, color=WITH, lw=0.8, ls=':')
    ax.axvline(g1b.t[-1], color=WITHOUT, lw=0.8, ls=':')
    ax.annotate('G1b contact: FR_HIP {:.0f} N'.format(g1b_force(g1b)), (g1b.t[-1], g1b.clearance[-1]),
                xytext=(g1b.t[-1] - 2.6, -0.12), color=WITHOUT, fontsize=8, arrowprops={'arrowstyle': '->',
                                                                                        'color': WITHOUT})
    ax.set_xlim(12, 18.2)
    ax.set_ylim(-0.2, 1.0)
    ax.set_xlabel('simulated time (s)')
    ax.set_ylabel('clearance (m)')
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(alpha=0.3)
    ax.set_title('Clearance to the nearest box (negative = footprint overlaps the box)', fontsize=10)
    fig.savefig(out, dpi=110, bbox_inches='tight')
    plt.close(fig)


def g1b_force(run):
    return max((s.get('nonfoot_substep_max_n') or 0.0) for s in run.steps)


def identity_figure(phase_c_steps, g1, g1b, g2, out):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    floor = 1e-9

    def dev(a_xy, b_xy, n):
        return np.maximum(np.linalg.norm(a_xy[:n] - b_xy[:n], axis=1), floor)
    pc = np.array([s['xyz'][:2] for s in phase_c_steps])
    t_pc = np.array([s['sim_ns'] / 1e9 for s in phase_c_steps])
    n1 = min(len(pc), len(g1.xy))
    ax.plot(t_pc[:n1], dev(g1.xy, pc, n1), color='#2e9e44', lw=2, label='G1 (server 33a0d561, no monitor) vs Phase C green')
    n2 = min(len(pc), len(g1b.xy))
    ax.plot(t_pc[:n2], dev(g1b.xy, pc, n2), color=WITHOUT, lw=1.5,
            label='G1b (server b976284d, no monitor) vs Phase C green')
    n3 = min(len(g1b.xy), len(g2.xy))
    ax.plot(g1b.t[:n3], dev(g2.xy, g1b.xy, n3), color=WITH, lw=1.5, ls='--',
            label='G2 (monitor) vs G1b (no monitor), same server')
    ax.axvline(g2.first_change_s, color=WITH, lw=0.8, ls=':')
    ax.text(g2.first_change_s + 0.1, 3e-9, 'monitor first\nchanges a command', color=WITH, fontsize=8)
    ax.text(0.3, 1.6e-9, 'G1 vs Phase C: exactly 0 at all {} steps;  G2 vs G1b: exactly 0 until {:.2f} s'.format(
        n1, g2.first_change_s), fontsize=8, color='#2e9e44')
    ax.set_yscale('log')
    ax.set_ylim(5e-10, 1)
    ax.set_yticks([1e-9, 1e-6, 1e-3, 1])
    ax.set_yticklabels(['0 (identical)', '1 µm', '1 mm', '1 m'])
    ax.set_xlabel('simulated time (s)')
    ax.set_ylabel('base position difference')
    ax.set_title('Do the runs repeat? Same replayed commands, logged base x, y compared at every 20 ms step', fontsize=10)
    ax.legend(fontsize=8, loc='center left')
    ax.grid(alpha=0.3, which='both')
    fig.savefig(out, dpi=110, bbox_inches='tight')
    plt.close(fig)


def scripted_figure(g3, g4, g5, out):
    fig = plt.figure(figsize=(17, 16))
    grid = fig.add_gridspec(4, 3, height_ratios=[1.0, 1.5, 0.9, 0.9], hspace=0.38, wspace=0.25)
    specs = [(g3, 'G3', 'G3 head-on: line y = 0 at 0.3 m/s', (2.4, 4.6), (-0.7, 0.7)),
             (g4, 'G4', 'G4 corner graze: line y = 0.45 at 0.3 m/s', (2.4, 4.6), (-0.5, 1.1)),
             (g5, 'G5', 'G5 stale cloud: line y = 0, clouds stop after 5.0 s', (-0.3, 4.6), (-1.0, 1.0))]
    for col, (run, short, title, xlim, ylim) in enumerate(specs):
        ax = fig.add_subplot(grid[0, col])
        image, frame_s = run.frame(run.t[-1])
        ax.imshow(image)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title('{}\nchase camera at the end, t = {:.2f} s'.format(title, frame_s), fontsize=9)
        ax = fig.add_subplot(grid[1, col])
        topdown(ax, [(run, WITH, short)], xlim, ylim,
                'min ground-truth clearance {:.3f} m; at end {:.3f} m'.format(run.clearance.min(), run.clearance[-1]),
                zones_on=run)
        window = (3.5, 7.0) if run is g5 else (9.0, run.t[-1])
        ax = fig.add_subplot(grid[2, col])
        ax.step(run.tick_t, run.v_in, where='post', color=GREY, lw=1.2, label='scripted command (in)')
        ax.step(run.tick_t, run.v_out, where='post', color=WITH, lw=1.6, label='command after monitor (out)')
        ax.plot(run.t, run.vx, color='k', lw=0.7, alpha=0.7, label='body forward speed')
        if run.first_change_s is not None:
            ax.axvline(run.first_change_s, color=WITH, lw=0.8, ls=':')
        ax.set_xlim(*window)
        ax.set_ylabel('speed (m/s)')
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc='upper right')
        ax = fig.add_subplot(grid[3, col])
        if run is g5:
            ax.step(run.tick_t, run.cloud_age, where='post', color='#e67e22', lw=1.4,
                    label='age of last cloud given to Nav2')
            ax.axhline(0.35, color='#e67e22', lw=0.8, ls='--', label='source_timeout 0.35 s')
            ax.axvline(5.0, color='#e67e22', lw=0.8, ls=':')
            ax.axvline(run.first_change_s, color=WITH, lw=0.8, ls=':', label='first STOP ({:.1f} s)'.format(
                run.first_change_s))
            ax.set_ylabel('cloud age (s)')
            ax.set_ylim(0, 1.0)
        else:
            ax.plot(run.t, run.clearance, color='#8e44ad', lw=1.3, label='ground-truth leg-footprint clearance')
            ax.plot(run.tick_t, run.perceived, color='#8e44ad', lw=0, marker='.', ms=3,
                    label='clearance seen in the LiDAR cloud')
            ax.axhline(0.0, color='k', lw=1)
            ax.axvline(run.first_change_s, color=WITH, lw=0.8, ls=':')
            ax.set_ylabel('clearance (m)')
            ax.set_ylim(-0.05, 1.0)
        ax.set_xlim(*window)
        ax.set_xlabel('simulated time (s)')
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc='upper right')
    fig.text(0.5, 0.925, 'Scripted approaches with the monitor on (Isaac, server b976284d). No non-foot contact in any.',
             ha='center', fontsize=12)
    fig.savefig(out, dpi=110, bbox_inches='tight')
    plt.close(fig)


def vla_figure(runs, phase_c_names, out, title, decision_row=False):
    rows_spec = [1.0, 1.0, 1.3, 0.9] if decision_row else [1.0, 2.0, 0.9]
    fig = plt.figure(figsize=(17, 19 if decision_row else 17))
    grid = fig.add_gridspec(len(rows_spec), 3, height_ratios=rows_spec, hspace=0.5 if decision_row else 0.62,
                            wspace=0.22)
    r0 = 1 if decision_row else 0
    for col, (run, pc_name) in enumerate(zip(runs, phase_c_names)):
        if decision_row:
            decisions = rows(run.dir / 'client' / 'decisions.jsonl')
            first = next(d for d in decisions if d.get('llm_output'))
            ax = fig.add_subplot(grid[0, col])
            ax.imshow(np.asarray(Image.open(run.dir / 'client' / 'decision_frames' /
                                            'decision_{:04d}.jpg'.format(first['decision']))))
            if first.get('pixel_goal'):
                row_px, col_px = first['pixel_goal']
                ax.plot(col_px, row_px, marker='x', ms=14, mew=3, color=WITHOUT)
                ax.annotate('pixel goal "{}"'.format(first['llm_output']), (col_px, row_px), xytext=(col_px - 250, row_px + 120),
                            color=WITHOUT, fontsize=9, arrowprops={'arrowstyle': '->', 'color': WITHOUT})
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title('{}: decision {} head image (what System 2 saw)\nfirst answer {}, then the look-down call'.format(
                run.name.replace('phase_d_vla_monitor_', ''), first['decision'], first['first_action']), fontsize=9)
        target = run.episode['target_landmark']
        centre = next(lm['center'][:2] for lm in run.episode['landmarks'] if lm['name'] == target)
        i_close = int(np.argmin(run.clearance))
        ax = fig.add_subplot(grid[r0, col])
        image, frame_s = run.frame(run.t[i_close])
        ax.imshow(image)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title('{}: "{}"\nchase camera at the closest pass to any box, t = {:.2f} s'.format(
            run.name.replace('phase_d_vla_monitor_', ''), run.episode['instruction'], frame_s), fontsize=9)
        ax = fig.add_subplot(grid[r0 + 1, col])
        if pc_name is not None:
            pc = rows(RUNS / pc_name / 'isaac' / 'isaac_steps.jsonl')
            ax.plot([p['xyz'][0] for p in pc], [p['xyz'][1] for p in pc], color=GREY, lw=1.0, ls='--',
                    label='Phase C {} (no monitor, different sampling; reference only)'.format(pc_name.replace('phase_c_', '')))
        corners = [p for box in run.boxes.values() for p in box]
        x_lo = min(run.xy[:, 0].min(), min(c[0] for c in corners)) - 0.6
        x_hi = max(run.xy[:, 0].max(), max(c[0] for c in corners)) + 0.6
        y_lo = min(run.xy[:, 1].min(), min(c[1] for c in corners)) - 0.6
        y_hi = max(run.xy[:, 1].max(), max(c[1] for c in corners)) + 0.6
        topdown(ax, [(run, WITH, 'VLA')], (x_lo, x_hi), (y_lo, y_hi), '', every_s=1.0)
        ax.add_patch(plt.Circle(centre, run.episode['success_radius_m'], fill=False, color='k', lw=0.8, ls=':'))
        stop_s = run.client.get('stop_sim_s')
        if stop_s is not None:
            i = run.index_at(stop_s)
            ax.plot(*run.xy[i], marker='s', ms=8, color='k', ls='none', label='model says STOP ({:.1f} s)'.format(stop_s))
        ax.plot(*run.xy[i_close], marker='x', ms=9, mew=2, color=WITHOUT, ls='none',
                label='closest pass, leg clearance {:.2f} m'.format(run.clearance[i_close]))
        closest_target = min(math.dist(p, centre) for p in run.xy)
        ax.set_title('{} after {:.0f} s; success {}\noracle success {} (closest to target {:.2f} m, radius {:.1f} m)'.format(
            run.record['termination'], run.t[-1], run.client['success'], closest_target <= run.episode['success_radius_m'],
            closest_target, run.episode['success_radius_m']), fontsize=9)
        ax.legend(fontsize=7, loc='upper center', bbox_to_anchor=(0.5, -0.13), ncol=1)
        ax = fig.add_subplot(grid[r0 + 2, col])
        ax.plot(run.t, run.clearance, color='#8e44ad', lw=1.3, label='ground-truth leg-footprint clearance, nearest box')
        ax.plot(run.tick_t, run.perceived, color='#8e44ad', lw=0, marker='.', ms=2, label='clearance seen in the LiDAR cloud')
        ax.axhline(0.05, color=WITH, lw=0.8, ls='--', label='approach zone edge (+0.05 m)')
        ax.axhline(0.0, color='k', lw=1)
        changed = int(np.sum(np.any(np.abs(np.array([t['in'] for t in run.ticks]) -
                                           np.array([t['out'] for t in run.ticks])) > 1e-9, axis=1)))
        ax.set_title('commands changed by the monitor: {} of {} ticks'.format(changed, len(run.ticks)), fontsize=9)
        ax.set_ylim(-0.05, 3.0)
        ax.set_xlabel('simulated time (s)')
        ax.set_ylabel('clearance (m)')
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc='upper right')
    fig.text(0.5, 0.925, title, ha='center', fontsize=12)
    fig.savefig(out, dpi=110, bbox_inches='tight')
    plt.close(fig)


def world_to_px(xy, xlim, ylim, size):
    w, h = size
    return (int((xy[0] - xlim[0]) / (xlim[1] - xlim[0]) * w), int(h - (xy[1] - ylim[0]) / (ylim[1] - ylim[0]) * h))


def green_pair_video(g1b, g2, out_path):
    size = (360, 360)
    xlim, ylim = (1.2, 3.6), (1.3, 3.7)
    frames = []
    last = int(round(g2.t[-1] / STEP_S))
    for step in range(5, last + 1, 5):
        seconds = step * STEP_S
        panels = []
        for run, label, color in ((g1b, 'WITHOUT monitor (G1b)', (57, 57, 192)), (g2, 'WITH monitor (G2)',
                                                                                  (180, 119, 31))):
            if seconds <= run.t[-1] + 1e-6:
                image = cv2.cvtColor(np.asarray(Image.open(run.dir / 'sim' / 'frames' /
                                                            'chase_{:06d}.jpg'.format(step))), cv2.COLOR_RGB2BGR)
                i = run.index_at(seconds)
                tick = min(int(seconds * 10), len(run.ticks) - 1)
                text = '{}  t={:.1f}s  out v={:.2f}  clear={:+.3f}m'.format(label, seconds, run.v_out[tick],
                                                                          run.clearance[i])
                image = banner(image, text)
            else:
                image = cv2.cvtColor(np.asarray(Image.open(run.dir / 'sim' / 'frames' /
                                                            'chase_{:06d}.jpg'.format(int(round(run.t[-1] / STEP_S)) // 5 * 5))),
                                     cv2.COLOR_RGB2BGR)
                image = banner(image, '{}  CONTACT FR_HIP {:.0f} N at {:.2f} s'.format(label, g1b_force(run), run.t[-1]),
                               color=(255, 255, 255), bg=(40, 40, 200))
            panels.append(image)
        mini = np.full((size[1], size[0], 3), 255, np.uint8)
        for name, box in g2.boxes.items():
            pts = np.array([world_to_px(p, xlim, ylim, size) for p in box], np.int32)
            cv2.fillPoly(mini, [pts], {'blue_box': (214, 111, 59), 'red_box': (60, 76, 231),
                                       'green_box': (68, 158, 46), 'grey_box': (140, 140, 140)}[name])
        for run, color in ((g1b, (57, 57, 192)), (g2, (180, 119, 31))):
            i = run.index_at(min(seconds, run.t[-1]))
            path = np.array([world_to_px(p, xlim, ylim, size) for p in run.xy[:i + 1]], np.int32)
            cv2.polylines(mini, [path], False, color, 1, cv2.LINE_AA)
            foot = np.array([world_to_px(p, xlim, ylim, size) for p in place(LEGS, *run.xy[i], run.yaw[i])], np.int32)
            cv2.polylines(mini, [foot], True, color, 2, cv2.LINE_AA)
        cv2.putText(mini, 'top-down, leg footprints', (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(mini, 'red: without  blue: with', (6, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1,
                    cv2.LINE_AA)
        row = np.hstack([panels[0], panels[1], cv2.resize(mini, (360, 360))])
        frames.append(row)
    write_video(frames, out_path)


def triple_video(runs, out_path):
    frames = []
    last = max(int(round(r.t[-1] / STEP_S)) for r in runs)
    for step in range(5, last + 1, 5):
        panels = []
        for run in runs:
            end = int(round(run.t[-1] / STEP_S)) // 5 * 5
            s = min(step, end)
            image = cv2.cvtColor(np.asarray(Image.open(run.sim_dir / 'frames' / 'chase_{:06d}.jpg'.format(s))),
                                 cv2.COLOR_RGB2BGR)
            tick = min(int(s * STEP_S * 10), len(run.ticks) - 1)
            i = run.index_at(s * STEP_S)
            label = ({'headon': 'G3', 'corner': 'G4', 'stale': 'G5'}[run.name.split('_')[4]] if not run.vla
                     else run.name.replace('phase_d_vla_monitor_', '').replace('green_behind_box_', 'behind_'))
            text = '{} t={:.1f}s in v={:.2f} out v={:.2f} clear={:.2f}m{}'.format(
                label, s * STEP_S, run.v_in[tick], run.v_out[tick], run.clearance[i], ' (ended)' if step > end else '')
            panels.append(banner(image, text))
        frames.append(np.hstack(panels))
    write_video(frames, out_path)


def write_video(frames, out_path):
    raw = out_path.with_suffix('.raw.mp4')
    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*'mp4v'), 10.0, (w, h))
    for frame in frames:
        writer.write(frame)
    writer.release()
    if shutil.which('ffmpeg'):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        '-crf', '23', str(out_path)], check=True)
        raw.unlink()
    else:
        raw.rename(out_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    g1 = Run('phase_d_isaac_passthrough_green_replay_v1')
    g2 = Run('phase_d_isaac_monitor_green_replay_v1')
    g1b = Run('phase_d_isaac_passthrough_green_replay_v2')
    g3 = Run('phase_d_isaac_monitor_headon_line0_v1')
    g4 = Run('phase_d_isaac_monitor_corner_line045_v1')
    g5 = Run('phase_d_isaac_monitor_stale_line0_v1')
    phase_c = rows(RUNS / 'phase_c_green_box_v1' / 'isaac' / 'isaac_steps.jsonl')
    green_pair_figure(g1b, g2, args.out / 'fig1_green_replay_with_without_monitor.png')
    identity_figure(phase_c, g1, g1b, g2, args.out / 'fig2_run_repeatability.png')
    scripted_figure(g3, g4, g5, args.out / 'fig3_scripted_headon_corner_stale.png')
    green_pair_video(g1b, g2, args.out / 'video1_green_replay_without_vs_with_monitor.mp4')
    triple_video([g3, g4, g5], args.out / 'video2_headon_corner_stale.mp4')
    vla = [Run('phase_d_vla_monitor_green_box_v1'), Run('phase_d_vla_monitor_red_box_v1'),
           Run('phase_d_vla_monitor_blue_box_v1')]
    vla_figure(vla, ['phase_c_green_box_v1', 'phase_c_red_box_v4', 'phase_c_blue_box_v1'],
               args.out / 'fig4_d0d_vla_episodes_with_monitor.png',
               'D.0d: InternVLA-N1 episodes with the Nav2 collision monitor in the command path (Isaac, one run each)')
    triple_video(vla, args.out / 'video3_d0d_vla_episodes.mp4')
    behind = [Run('phase_d_vla_monitor_green_behind_box_v{}'.format(i)) for i in (1, 2, 3)]
    vla_figure(behind, [None, None, None], args.out / 'fig5_d0e_goal_behind_box.png',
               'D.0e: goal 5 m ahead behind a grey box (d_green_behind_grey_box_v1), three runs, monitor in the loop',
               decision_row=True)
    triple_video(behind, args.out / 'video4_d0e_goal_behind_box.mp4')
    for path in sorted(args.out.iterdir()):
        print(path.name, path.stat().st_size)


if __name__ == '__main__':
    main()

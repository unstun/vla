"""Render scientific plots from compact, hash-bound remote summaries."""
from pathlib import Path
import csv
import hashlib
import json
import os

os.environ.setdefault('MPLCONFIGDIR', '/tmp/v52-live-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
RUN = 'v52_realtime_trial02'
metrics = json.loads((HERE / (RUN + '_metrics.json')).read_text())


def table(suffix):
    with (HERE / (RUN + suffix)).open() as stream:
        return np.array([[float(v) for v in row] for row in list(csv.reader(stream))[1:]])


frequency = table('_frequency.csv')
latency = table('_latency.csv')
progress = table('_progress.csv')
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10,
                     'axes.spines.top':False, 'axes.spines.right':False})
fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
axes[0].plot(frequency[:, 0], frequency[:, 2], color='#98A4B4', linewidth=.8, label='Attempts')
axes[0].plot(frequency[:, 0], frequency[:, 3], color='#126D8C', linewidth=1, label='Successful completions')
axes[0].axhline(30, color='#333333', linestyle='--', linewidth=.8)
axes[0].set_ylim(0, 35); axes[0].set_ylabel('Local frequency (Hz)\nTrailing 1 wall second')
axes[0].legend(loc='upper right')
axes[0].set_title(f"v52 Building trial02 · successful planning {metrics['whole_window_rates']['successful_hz']:.2f} Hz")
xs, ys = latency[:, 0], latency[:, 1]
ok = latency[:, 2].astype(bool); fast = ys < 10
axes[1].axhspan(.5, 10, color='#E1F2E9')
for mask, color, label in [(ok & fast, '#17815C', 'Success <10 ms'),
                           (ok & ~fast, '#176B94', 'Success >=10 ms'),
                           (~ok, '#B53B3B', 'Failed round')]:
    axes[1].scatter(xs[mask], ys[mask], s=8, c=color, alpha=.7, label=label)
axes[1].axhline(1000 / 30, color='#333333', linestyle='--', linewidth=.8)
axes[1].set_yscale('log'); axes[1].set_ylim(.5, 1500)
axes[1].set_ylabel('Complete round solve (ms)')
axes[1].set_title(f"Median {metrics['local_solve_ms']['median']:.2f} ms; maximum {metrics['local_solve_ms']['maximum']:.1f} ms")
axes[1].legend(loc='upper right')
axes[2].plot(progress[:, 0], progress[:, 1], color='#126D8C', linewidth=1.5)
axes[2].set_ylabel('Measured 3D path (m)'); axes[2].set_xlabel('Simulation time (s)')
axes[2].set_title(f"Path {metrics['measured_path_length_m']:.2f} m; longest pause {max(metrics['pauses_over_1s'], default=0):.2f} s")
for ax in axes:
    ax.grid(alpha=.2); ax.set_xlim(11, metrics['physical_duration_s'])
fig.tight_layout()
for ext in ('png', 'pdf'):
    fig.savefig(HERE / ('v52_time_series.' + ext), dpi=160)
plt.close(fig)

summary = json.loads((HERE.parent / 'idle_paired_summary.json').read_text())
fig, ax = plt.subplots(figsize=(9, 4.8))
x = np.arange(3)
for mode, offset, color, label in [('0', -.18, '#8795A9', 'Original lookup path'),
                                  ('1', .18, '#147F75', 'v52 scoped lookup reuse')]:
    values = [summary['groups'][str(i)][mode]['max_ms'] for i in range(3)]
    bars = ax.bar(x + offset, values, .36, color=color, label=label)
    ax.bar_label(bars, fmt='%.1f ms', padding=4)
ax.set_xticks(x, ['Successful cold round\nsim 33.45 s', 'Worst reproduced failure\nsim 44.95 s',
                 'Repeated corner failure\nsim 74.04 s'])
ax.set_ylim(0, 550); ax.set_ylabel('Maximum complete replay round (ms)')
ax.axhline(1000 / 30, color='#333333', linestyle='--', linewidth=.8)
ax.set_title('Idle-host paired replay: lookup reuse saves 10.7% at the worst case', fontweight='bold')
ax.legend(); ax.grid(axis='y', alpha=.15)
fig.text(.07, .03, '3 alternating pairs per case; identical outcomes and control points/knots.\n'
         'Fixed inputs and clock; no physics. All three cold cases still exceed 33.3 ms.', fontsize=9)
fig.tight_layout(rect=(0, .1, 1, 1))
for ext in ('png', 'pdf'):
    fig.savefig(HERE / ('idle_paired_latency.' + ext), dpi=160)
plt.close(fig)
paths = [Path(__file__), HERE / (RUN + '_metrics.json'), HERE.parent / 'idle_paired_summary.json']
paths += [HERE / (RUN + suffix) for suffix in ('_frequency.csv', '_latency.csv', '_progress.csv')]
provenance = {str(p.relative_to(HERE.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(HERE / 'live_plot_provenance.json').write_text(json.dumps(dict(source_sha256=provenance), indent=2) + '\n')

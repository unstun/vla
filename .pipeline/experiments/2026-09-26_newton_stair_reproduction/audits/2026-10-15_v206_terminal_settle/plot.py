"""Plot the returned compact evidence; no simulation or decision analysis."""
from pathlib import Path
import ast
import csv
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parent / 'results'
data = {v: json.loads((root/(v+'.json')).read_text()) for v in ['v204','v206']}
traces = {}
for version in data:
    with (root/(version+'.csv')).open() as f:
        traces[version] = list(csv.DictReader(f))
fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True,
                         gridspec_kw={'height_ratios':[1, 1.5, 1.5]})
for version, color in [('v204','#327ba8'), ('v206','#be4b36')]:
    start = data[version]['terminal_start_s']
    rows = data[version]['near_terminal_commands']
    # Telemetry body is post-step; stance/command belongs to the preceding step.
    dt = float(traces[version][0]['telemetry_s']) - float(traces[version][0]['input_s'])
    x = [r['physics_time_s']-dt-start for r in rows]
    axes[0].step(x, [np.hypot(*r['effective_command'][:2]) for r in rows], where='post',
                 color=color, label=version+' linear command (m/s)')
    axes[0].step(x, [abs(r['effective_command'][2]) for r in rows], where='post',
                 color=color, ls=':', label=version+' yaw command (rad/s)')
    axes[0].plot([x[-1],float(traces[version][-1]['input_s'])-start], [0,0], color=color)
rows = traces['v206']; start = data['v206']['terminal_start_s']
x = np.array([float(r['input_s'])-start for r in rows])
forces = np.array([ast.literal_eval(r['foot_forces']) for r in rows])
for i, (leg,color) in enumerate(zip(['Front left','Front right','Hind left','Hind right'],
                                  ['#9f3a31','#d58544','#3c8093','#695394'])):
    axes[1].plot(x, forces[:,i], color=color, lw=1.4, label=leg)
axes[1].axhline(10, color='#444444', ls='--', lw=1, label='Entry minimum: 10 N')
axes[2].axhspan(35,65, color='#e6f1e9', label='Existing allowed band: 35-65%')
for version,color in [('v204','#327ba8'),('v206','#be4b36')]:
    rows = traces[version]; start = data[version]['terminal_start_s']
    x = np.array([float(r['input_s'])-start for r in rows])
    shares = np.array([ast.literal_eval(r['shares'])[0]*100 for r in rows])
    axes[2].plot(x, shares, color=color, lw=1.6, label=version+' front-pair share')
    if version == 'v206':
        windows = data[version]['support_windows']
        axes[2].scatter([r['end_s']-start for r in windows], [r['shares'][0]*100 for r in windows],
                        color=color, marker='x', s=28, label='Rejected dwell mean')
end = data['v206']['zero_to_terminal_event_s']
for ax in axes:
    ax.axvline(0, color='#777777', lw=.8)
    ax.axvline(end, color='#be4b36', ls='--', lw=1)
    ax.axvspan(end, 11, color='#eeeeee')
    ax.grid(alpha=.18); ax.set_xlim(-1,11)
    ax.spines[['right','top']].set_visible(False)
    ax.legend(loc='upper right', fontsize=8, ncol=2)
axes[0].set_ylabel('Command'); axes[0].set_ylim(-.03,.85)
axes[1].set_ylabel('Contact force magnitude (N)'); axes[1].set_ylim(0,95)
axes[2].set_ylabel('Front contact-force share (%)'); axes[2].set_ylim(30,95)
axes[2].set_xlabel('Seconds since the last nonzero command ended (each run aligned separately)')
axes[0].set_title('v206 terminal timeout: zero command, underloaded hind foot, then rejected load split',
                  loc='left', fontsize=12, fontweight='bold', pad=14)
axes[2].text(1.25,36, 'v204 begins PD transfer at +1.17 s', color='#327ba8', fontsize=9)
axes[1].text(.25,81, 'v206: hind-right force stays below 10 N for about 4.18 s', fontsize=9)
axes[2].text(9.85,33, 'After failure', fontsize=8, color='#555555', rotation=90)
fig.text(.08,.015, 'Recorded decisions only. v204 ran on Mac; v206 ran on Linux. This is not a controlled version A/B.',
         fontsize=9, color='#555555')
fig.tight_layout(rect=[0,.035,1,1])
fig.savefig(root/'terminal_comparison.png',dpi=160)
fig.savefig(root/'terminal_comparison.pdf')

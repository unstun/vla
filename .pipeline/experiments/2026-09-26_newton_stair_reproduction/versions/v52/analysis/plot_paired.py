"""Plot the three paired cold replay comparisons from compact returned results."""
from pathlib import Path
import hashlib
import json
import os

HERE = Path(__file__).resolve().parent
VERSION = HERE.parent
os.environ.setdefault('MPLCONFIGDIR', '/tmp/v52-paired-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

summary = json.loads((VERSION / 'paired_summary.json').read_text())
groups = summary['groups']
fig, ax = plt.subplots(figsize=(9, 4.8))
x = np.arange(3)
for mode, offset, color, label in [('0', -.18, '#8795A9', 'Original lookup path'),
                                  ('1', .18, '#147F75', 'v52 scoped lookup reuse')]:
    y = [groups[str(case)][mode]['max_ms'] for case in range(3)]
    bars = ax.bar(x + offset, y, .36, color=color, label=label)
    ax.bar_label(bars, fmt='%.1f ms', padding=4)
ax.set_xticks(x, ['Successful cold round\nsim 33.45 s', 'Worst reproduced failure\nsim 44.95 s',
                 'Repeated corner failure\nsim 74.04 s'])
ax.set_ylabel('Maximum complete replay round latency (ms)')
ax.axhline(1000 / 30, color='#333333', linestyle='--', linewidth=.8, label='30 Hz period: 33.3 ms')
ax.set_ylim(0, 560)
ax.set_title('v52 reduces lookup overhead; long recovery rounds remain', fontweight='bold')
ax.grid(axis='y', alpha=.15); ax.legend()
fig.text(.07, .025, '3 alternating pairs per case; identical outcomes and control points/knots.\n'
         'Fixed inputs and clock; no physics. Concurrent IsaacLab job: these are shared-host measurements.', fontsize=9)
fig.tight_layout(rect=(0, .1, 1, 1))
for ext in ('png', 'pdf'):
    fig.savefig(HERE / ('paired_latency.' + ext), dpi=160)
plt.close(fig)
sources = {str(p.relative_to(VERSION)): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in [Path(__file__), VERSION / 'paired_summary.json',
                     VERSION / 'profiles/attempt01/result.json']}
(HERE / 'plot_provenance.json').write_text(json.dumps(dict(source_sha256=sources), indent=2) + '\n')

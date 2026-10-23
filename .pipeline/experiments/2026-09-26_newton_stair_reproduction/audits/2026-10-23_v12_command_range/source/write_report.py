"""Render inspectable Markdown tables from the retained compact measurements."""
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=json.loads((ROOT/'results/summary.json').read_text())
runs=[json.loads(x) for x in (ROOT/'results/extract01.jsonl').read_text().splitlines() if json.loads(x)['type']=='run']
yaws=json.loads((ROOT/'results/pure_yaw_intervals.json').read_text())
fmt=lambda x: '—' if x is None else f'{x:.3f}'

def table_run(r):
 a=r['analysis'];b=a['bands']['below_0p2'];name=r['run'];kind='circle' if a['window_kind']=='goal_circle' else '**fallback**'
 return f"| {name} | {kind} | {a['duration_s']:.2f} | {a['low_inclusive_share']*100:.2f} | {a['high_inclusive_share']*100:.2f} | {a['low_share_nonzero']*100:.2f} | {a['pure_yaw_total_s']:.3f} | {a['pure_yaw_longest_s']:.3f} | {fmt(a['pure_yaw_max_displacement_cm'])} |"

lines=['# Phase A — V12 terminal command-range audit','',
'2026-10-23. **Phase A passed: all 34 retained runs analyzed, 102 source-file identities matched, zero new physics.** '
'G1 was explicitly approved in this session. Branch `local/research-unpublished`; no push. Phase B is unrun, Phase C has not started, and G2/G3 are pending.','',
'## What the recordings establish','',
'**The current terminal spends almost all its moving-command time in the low-speed range, and v291 can remain there with almost no useful progress.** '
'Among the 28 runs that actually entered the 25 cm goal circle, 86.20–99.87% of nonzero translation time was at or below 0.2 m/s. '
'The paired v291 group spent 114.44 of 115.01 nonzero-command seconds in that band (99.50%). '
'The denominator here excludes exact-zero translation; the all-window shares below include stops.','',
'Two previously reported stall cases make the practical issue clear. In v291 CD12 r1, the (0,0.05] m/s band lasted '
'20.58 s: average commanded speed 0.04548 m/s, average measured speed along that command −0.00038 m/s. '
'In S04 r1, the same band lasted 43.48 s: 0.04582 m/s commanded, 0.00018 m/s along the command. '
'Measured total XY speeds were 0.01093 and 0.00447 m/s respectively: some body motion was sideways or oscillatory rather than useful commanded progress.','',
'**Short pure-yaw execution is present, but 90°/180° turning capability is still unmeasured.** '
'Across 39 terminal pure-yaw intervals, total exposure was only 6.297 s; 33 intervals lasted at most 0.22 s. '
'The longest interval lasted 1.559 s, turned 50.2°, and displaced the body by at most 3.03 cm. '
'The largest observed heading change was 50.4° in a 0.919 s interval at +1.0 rad/s; its maximum XY displacement was 3.61 cm. '
'These are observed short arcs on terrain, not a turn-drift margin for an entire half turn.','',
'**The training-floor premise was corrected.** The saved V12 config enables dynamic resampling; the fixed ≤0.2 m/s '
'zeroing belongs to the other branch. See [the dated source correction](../../../../../.trellis/tasks/10-23-v12-terminal-turn-stop/research/evidence.md#3-v12-command-sampling-and-the-low-speed-hypothesis-corrected-2026-10-23). '
'Phase A supports a low-speed execution problem; Phase B must measure `v_floor`, `wz_turn`, `turn_drift_margin` and `stop_distance(v)`. '
'No such values are selected here.','',
'![Applied-command exposure](figures/command_exposure.png)','',
'![Low-speed stall examples](figures/low_speed_stalls.png)','',
'## Group comparisons — actual goal-circle windows only','',
'These time-weighted groups include terrain and braking transitions. They are descriptive; different available runs and long failures change their mix. '
'Ratios above one in the parent can reflect residual motion after command reduction. They do not establish better steady tracking.','',
'| Group | Runs entering circle | Low-speed time / nonzero time (s) | Low share of nonzero | Low-band command (m/s) | Body XY speed (m/s) | Along-command speed (m/s) | Along-command ratio |',
'|---|---:|---:|---:|---:|---:|---:|---:|']
for g in s['groups']:
 if g['window_kind']!='goal_circle':continue
 b=g['bands']['below_0p2']
 lines.append(f"| {g['cohort']} {g['variant']} | {g['run_count']} | {b['duration_s']:.2f} / {g['nonzero_duration_s']:.2f} | {100*g['low_nonzero_share']:.2f}% | {fmt(b['mean_command_mps'])} | {fmt(b['mean_body_speed_mps'])} | {fmt(b['mean_axis_mps'])} | {fmt(b['axis_tracking_ratio'])} |")
lines+=['','## All 34 runs','',
'Circle means the first post-goal XY entry within 25 cm through recording end. **Fallback** means the run never entered: '
'ten seconds before its first post-goal all-zero command, clipped to observed navigation start, through recording end. '
'All six fallback runs were historical scanner failures; they are retained separately, not interpreted as terminal arrival. '
'Three additional scanner failures did enter the circle and remain in the circle group. No historical outcome was reclassified.','',
'Low = 0 < speed ≤0.2 m/s; high = speed ≥0.2 m/s. Exact-0.2 exposure was **0 s** in this cohort, so the inclusive overlap contributes nothing here. '
'All-window shares include stops. Drift is the largest sampled XY displacement among each run’s pure-yaw intervals; “—” means no interval, not zero drift.','',
'| Run | Window | Window s | Low / all % | High / all % | Low / nonzero % | Total yaw s | Longest yaw s | Max yaw drift cm |',
'|---|---|---:|---:|---:|---:|---:|---:|---:|']
lines.extend(table_run(r) for r in runs)
lines+=['','Per-band command/body-speed comparisons for every run and all 39 pure-yaw intervals, including applied yaw rates and source rows, are in '
'[TABLES.md](TABLES.md). Exact machine-readable values: [bands.json](results/bands.json), '
'[pure_yaw_intervals.json](results/pure_yaw_intervals.json), [summary.json](results/summary.json).','',
'![Pure-yaw duration and drift](figures/pure_yaw_drift.png)','',
'## Method, checks and retention','',
'- [DEFINITIONS.md](DEFINITIONS.md), analysis source, tests and the 34-run request were frozen in [frozen.json](frozen.json) before extraction. '
'Fourteen synthetic boundary, interval, direction, clock, missingness and hash checks passed.',
'- The read-only extractor used the existing ultra9 worker Python under `nice -n 19`; 133,924 telemetry rows were analyzed. '
'All 102 used source files, totaling 2,042,543,585 bytes, matched historical SHA-256 and sizes and remained stable during reads.',
'- Extraction produced 34/34 valid records: 28 circle windows, six declared fallbacks, zero missing runs, zero analysis errors. '
'Actual remote analysis took 12.34 s; SSH and local launch took 18.86 s. The prior 20–40 minute figure was a budget estimate, not measured runtime.',
'- [verification.json](results/verification.json) checks run order, source freeze, source identity, duration partitions, inclusive-band overlap and interval totals. '
'All window sample gaps stayed below the declared 0.04 s reporting threshold (exact values retained per run).',
'- Originals remain at the absolute paths in [request.json](request.json) and the extraction’s source records. '
'No remote file, simulator, controller, policy, threshold, recorded outcome or failure was changed. '
'[extract01.receipt.json](results/extract01.receipt.json) binds the returned compact stream to its execution.',
'- Re-analysis instructions: run `source/summarize.py`, then `source/render.py` and `source/write_report.py` locally against the retained compact output. '
'Do not rerun `source/run_audit.py`: `extract01` is create-exclusive, and no replacement extraction is needed. '
'Plot/report rendering is derived local presentation, separate from the frozen remote metrics.','',
'## Next gate','',
'Proceed to the flat-ground matrix at G2. The mandatory matrix is 31 cells ×3 fresh starts =93 runs, not the suggested cap of40. '
'Recommend the full required matrix on ultra9 with v216 stance, optional v291-assistance arm omitted, ≤120 simulated seconds per run and a four-hour total wall budget. '
'Freeze exact commands, metrics, ordering, source and module identities before the first run. Stop on the cap; retain unrun cells as unrun and all failures without replacement. '
'No v292 implementation or Building evaluation before the earlier phases and their gates.']
(ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')
lines=['# Phase A detailed measurement tables','',
'All values derive from the frozen `extract01` output. Window definitions, units and censoring are in [DEFINITIONS.md](DEFINITIONS.md). '
'Means use actual dt; speed means are m/s. The directional ratio is signed-axis distance divided by commanded distance, not an average of per-row ratios.','',
'## Main bands for every retained run','',
'Bands: zero; low = (0,0.2); exact =0.2; high >0.2. Empty-band values are “—”. '
'Fine bands, including the exact same body/direction measures, are retained in [bands.csv](results/bands.csv).','',
'| Run | Band | Duration s | Command m/s | Body XY m/s | Along command m/s | Perpendicular m/s | Ratio |',
'|---|---|---:|---:|---:|---:|---:|---:|']
for r in runs:
 for key,b in r['analysis']['bands'].items():
  lines.append(f"| {r['run']} | {key} | {b['duration_s']:.3f} | {fmt(b['mean_command_mps'])} | {fmt(b['mean_body_speed_mps'])} | {fmt(b['mean_axis_mps'])} | {fmt(b['mean_transverse_mps'])} | {fmt(b['axis_tracking_ratio'])} |")
lines+=['','## Every pure-yaw interval','',
'Applied yaw mean and range are rad/s; world-Z is measured angular velocity. Heading uses quaternion increments. '
'Drift includes the command-change endpoint. All intervals in this extraction are uncensored; the JSON retains those flags explicitly. '
'Each run without an interval has total/longest duration zero in REPORT.md and null maximum drift.','',
'| Run / interval | Start–end s | Command rows | Duration s | Applied yaw mean [min,max] | Measured world-Z | Heading ° | Max / net XY cm |',
'|---|---|---|---:|---|---:|---:|---:|']
for q in yaws:
 lines.append(f"| {q['run']} / {q['index']} | {q['start_s']:.3f}–{q['end_s']:.3f} | {q['command_start_row']}–{q['command_end_row']} | {q['duration_s']:.3f} | {fmt(q['mean_command_yaw_radps'])} [{q['min_command_yaw_radps']:.3f},{q['max_command_yaw_radps']:.3f}] | {fmt(q['mean_world_z_radps'])} | {math.degrees(q['heading_change_rad']):.3f} | {q['max_xy_displacement_cm']:.3f} / {q['net_xy_displacement_cm']:.3f} |")
(ROOT/'TABLES.md').write_text('\n'.join(lines)+'\n')
print('Wrote REPORT.md and full band/interval tables.')

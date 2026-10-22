# v273 complete fixed-cohort result — acceptance failed

Stage: experiment and analysis. Native v272 and benchmark v273 were frozen
before105 once-per-case calls. Original52 and fixed50+3 scenarios, endpoint
poses/headings, RL identity,0.35m model and0.1s sensor fixtures are unchanged.
CPU2/6GiB native requests ran sequentially, followed by independent raw-point
audits. No GPU/IsaacLab workload was changed; no physics was launched.

| Cohort | Global / cold SCAN | First GPMP | As-scored full gate | Global median |
|---|---:|---:|---:|---:|
| Original52 (49 positive +3illegal) | 38 /38 | 38/38 admitted | 8/49 positive | 2.536750 s |
| Fixed50 positive +3illegal | 48 /48 | 43/48 admitted | 11/50 positive | 2.743627 s |

All three illegal controls refuse in both cohorts. Fixed-cohort native refusals
are CM01 (UnknownSupport8 despite positive source-solid margin) and CS01
(valid endpoints but no graph route). The unchanged original ledger additionally
retains U11/U12/U13, D09–D15 and S03 no-route outcomes. U11/U12 endpoints now
pass support/source checks; this does not establish complete-route connectivity.

The full gate is much lower than native publication because the v273 raw-point
material audit reports negative margins on many stair/landing trajectories.
Those scores and witnesses are retained exactly. v275 read-only diagnosis
finds representative raw points only0.47–0.94micrometres from almost-vertical
source riser faces; XY-to-height inversion amplifies that difference into
centimetres. A bounded3Dmaterial-association treatment is being validated
separately. No corrected derived result is substituted into this as-scored table.

First-GPMP failures are CU08, CU11, CU13, CS02 and CE04. CU08/CU13 fail at the
actual start XYZ after the optimized heading drifts; the installed GPMP graphs
omit endpoint obstacle factors despite soft derivative priors. v274 is only
prepared for a small generic endpoint-factor treatment, deferred while the
point/source discrepancy is resolved. No scenario-specific change is included.

Coverage/smoothing/raw-margin/timing/selection acceptance is false. All physical
attempt/video counts are zero. Native source qualification and benchmark
acceptance remain distinct. Selected physical/display baseline stays v232/v233.

Local return:585compact files,7,571,596bytes, all SHA-256 values verified.
`results/return_inventory.json` pins another516numerical artifacts retained on
gpu5070ti. The local tables, per-case summaries, raw witnesses, logs and source
identities are complete; caches and full raw numerical tables were not copied.

Frozen native manifest:
`ddd01de906c0357a18ccd5c4ea9d222d7389293c907eb7f9fd9921f835b631cb`.
Frozen benchmark manifest:
`73c57b2db78f3b52dc93792193f958d64066f344c5f7604f3eb4b1508be382e1`.

# Historical complete Building success recovered

Stage: experiment + analysis. Dr Sun clarified that the remembered successful
video is a stair/complete-building route, not the local 12 m flat trial.

## Confirmed evidence

`machine-dog-nav/.pipeline/experiments/2026-09-11_pct_scan_upstream_baseline/`
contains `native_full02`: 4,904 original control records, 98.08 simulation
seconds, 74.062882 m recomputed XY travel, 0.037684 m final XY error and
`GOAL_REACHED_AND_STOPPED`. Actual body height changes from 0.4086 to 4.8404 m.
The delivered 2,452-frame full video matches its recorded SHA-256 and decodes
completely. The old conversation explicitly delivered it as the complete
planning/execution video (session `01a089c3-c4e3-75c2-b4c2-bb8f387d88e6`).
The separate `2026-09-11_pct_scan_three_view/three_view01` report and media also
exist; it is another historical episode, not this audit's new physical run.

## Correct comparison scope

| Condition | Historical full baseline | Current v7 trial |
|---|---|---|
| Execution | Isaac Sim / PhysX | Local Newton / MuJoCo-Warp CPU |
| Planner | Pinned combined upstream, no optimizer edits; listed Foxy/interface ports | Reactive/P2B SCAN lineage with subsequent local modifications |
| PCT route | 631 points, 73.237320 m XY | 46 points, 5.001119 m XY |
| Goal | Original full cross-level goal | Short initial stair-section goal |
| Body reference | 0.35 m | 0.30 m |
| Robot source | Original V12 URDF | Sensor-rig URDF |
| Configured cylinder radius | 0.25 m | 0.35 m |
| Configured Z inflation up/down | 0.1 / 0.1 m | 0.55 / 0.35 m |

The Building USDA and PCT tomogram are byte-identical to the historical inputs.
That does not prove identical simulator interpretation or sensing. New v7 also
uses reactive support/unknown checks; a configuration difference alone does not
prove which active collision branch caused failure.

The prior phrase "complete Building" described scene geometry in the local
launcher, but the actual goal did not reproduce the old full route. Treating it
as a full-route reproduction was incorrect. Likewise, the local Newton version
index does not mean no earlier Isaac full-building success existed.

## Next comparison

Use the recovered complete route, selected native algorithms, measured cloud
records and exact configuration as the historical control. First distinguish
planner/input changes from simulator/interface changes through same-input
comparisons, then use a separately versioned physical reproduction. Keep the
user's 0.6 m/s cruise request as a separately measured requirement. Do not infer
that increasing speed fixes the observed early stop.

This audit changes no production source/configuration or frozen version. It
imports no sibling code. That workspace is untracked in the sibling checkout;
its current Git HEAD cannot be substituted for its actual source provenance.
The pinned upstream commit and reviewed port manifest provide the proper clean
source-selection starting point. See `evidence.json` for primary paths/hashes.

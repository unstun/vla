# v57: corner continuity improves; 30 Hz remains unmet

Stage: experiment + analysis, 2026-10-02. Both requested Building recordings
completed on idle gpu5070ti. Each requested 90 seconds and recorded 90,000
physics steps / 89.962189 seconds on the native solver clock, with zero dropped
steps. v57 reuses the qualified v56 native build; its own change is qualification
metadata compatibility. The navigation reference remains v48.

**Both recordings pass the old corner without a measured pause over one second.
Successful planning reaches 25.65/25.76 Hz. Maximum full-round latency is
660.975/290.149 ms: lower than historical v48, but tail elimination and strict
30 Hz still fail.** These are independent physical trajectories, not paired
identical-input measurements of a causal speedup.

## Measured comparison

Successful Hz counts completed successful rounds over the complete navigation
pacing window, including initial goal setup, failures and pauses. It excludes
the separately recorded factory-startup prefix. Solve distributions use every
complete nominal round in the original log, including shutdown-edge records.

| Recording | Median solve | P95 | P99 | Maximum | Successful Hz | Measured 3D path |
|---|---:|---:|---:|---:|---:|---:|
| v48 historical trial01 | 3.092 ms | 126.496 ms | 207.175 ms | 1090.481 ms | 15.29 | 29.794 m |
| v52 trial02 | 2.039 ms | 452.706 ms | 486.063 ms | 711.404 ms | 10.19 | 23.189 m |
| v57 trial01 | 2.305 ms | 56.408 ms | 74.290 ms | 660.975 ms | 25.65 | 46.205 m |
| v57 trial02 | 2.419 ms | 60.780 ms | 76.803 ms | 290.149 ms | 25.76 | 46.616 m |

Against historical v48, the two measured maxima decrease by **39.4% and 73.4%**.
They differ substantially between trials, so the best trial is not a latency
guarantee. Trial01/02 have respectively 17/9 rounds at least 100 ms, zero rounds
at least 1000 ms, and 211/252 rounds exceeding 33.333 ms. Mean solves are
10.657/11.461 ms. Attempt rates are 25.866/25.810 Hz; the separately measured
native controller remains 30.000/30.000 Hz. Navigation RTF is 0.9524/0.9602.

[Side-by-side PNG](analysis/v57_time_series.png),
[vector PDF](analysis/v57_time_series.pdf),
[trial01 measurements](analysis/v57_realtime_trial01_metrics.json),
[trial02 measurements](analysis/v57_realtime_trial02_metrics.json).
The plot maps trailing one-wall-second counts to simulation time using actual
recorded state timestamps. Grey denotes untimed factory startup; blue marks the
39–55 s focus. Warm successes below 10 ms are green. The progress panel counts
pauses over one second; it does not imply the absence of shorter speed dips.

## Corner and remaining latency

The recordings pass within 1.3/4.8 cm XY of the frozen corner location at
46.606/45.906 s. By 55 s they travel another 5.083/6.937 m along their measured
trajectories; subsequent travel over the complete recording is 23.079/23.490 m.
Neither run has a measured pause over one second, including the 39–55 s focus.
The minimum observer-received curve reserve in that focus is 0.710/0.314 s,
sampled every 50 ms of wall time. This observation does not reconstruct
unpublished planner state or prove every possible safety property.

There are no logged emergency-state transitions or `remaining_spline_invalid`
events. Both recordings end at the observation bound with navigation active;
neither establishes arrival or final PD hold.

Two remaining mechanisms prevent 30 Hz:

- Trial01's worst round at 63.142 s fails after 11 native seed and 11 optimizer
  calls, taking 660.975 ms. Inclusive profiles show 284.77 ms seed work,
  347.53 ms optimizer work and 144.46 ms input application. Trial02's worst
  round at 56.401 s succeeds after five seed/optimizer attempts in 290.149 ms.
  These nested timers overlap and must not be summed.
- At 70–90 s, common latency also grows while warm starts remain accepted in
  464/471 and 390/395 rounds. Mean final-goal search costs 19.34/27.47 ms per
  round; mean input application costs 8.20/11.52 ms. Median complete rounds
  rise to 26.65/36.69 ms. The earlier necessary-condition precheck does not
  bypass native search when the goal neighborhood is potentially eligible.

[Band profiles and source hashes](analysis/latency_diagnosis.json) preserve this
distinction. Further optimization should address these measured costs while
retaining trajectory continuity and current safety checks. No hard timeout,
cancellation or stop-protocol modification was used.

## Validation and version boundary

The frozen lineage is v48 → v50 → v52 → v53 (compatible refresh) → v54 (clock
guard) → v55 (recovery input freshness) → v56 (typed physical-floor evidence)
→ v57 (qualification aliases). v49 is excluded. Frozen failures remain intact.

v56's build02 and contract03 passed the inherited native/cache/warm/goal/backend
checks, nine real-DDS freshness checks, 23 physical-role checks and 30 native
physical/sequence checks. v57 reuses those exact native bytes; it does not claim
to have rebuilt them. Its actual frozen entry gate and post-run verification
passed all 7,408 source and 519 installed-file hashes. Each capture archive has
795 individually verified original members. Returned compact files match their
declared hashes and sizes.

[Component qualification](component_qualification.json),
[actual entry gate](entry_gate_frozen.json),
[post-run verification](analysis/verification.json),
[return verification](analysis/return_verification.json),
[acceptance flags](acceptance.json).

## Review video and storage

The [trial02 review MP4](../../../../../output/2026-09-27_lite3_versions/v57_realtime_trial02_review.mp4)
is 8,773,409 bytes, 1280×720, 2,460 frames at 30 FPS, with full decode and frame
count verification. It replays recorded navigation wall time for 82 seconds,
covering simulation 11.041–89.942 s. The untimed factory-startup prefix is omitted;
no physics is rerun, no poses interpolated and no pauses accelerated.
Display FPS is separate from local planning Hz.
The video's local-Hz overlay counts attempts; the plots and comparison table
emphasize successful completions.

The frozen v51 renderer initially lacked its remote source dependencies, then
its original Helvetica font. Both failed render attempts are preserved. Exact
renderer/reference bytes and the original font were supplied to the execution
copy; Pillow's normal Linux font lookup uses a task-local `XDG_DATA_HOME`.
No frozen rendering or navigation source was edited. [Video provenance](REVIEW_VIDEO.json)
records hashes, storage and regeneration.

The 237,929,107-byte and 238,301,058-byte capture archives, raw NPZ/JSONL, complete
derived round/curve arrays, builds and render frame provenance remain under
`/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/`
on gpu5070ti. Only compact results/tables, plots, three preview images and the
single review MP4 returned locally. No full PNG sequence was created.

Reanalyze remotely with `versions/v57/analysis/executed_data_analysis.py --skip-plots`
(the original executed helper is preserved locally and must first be synced),
then render plots from verified compact tables with
`versions/v57/analysis/compare_trials.py --plots-only`. The post-run helper is
separate from frozen simulation code. [Plot provenance](analysis/plot_provenance.json)
binds both analysis and display source hashes to the returned tables.

Follow-up: the [post-70-second audit](../../audits/2026-10-02_v57_after70/REPORT.md)
confirms the fixed-search-pool trigger, repeated unsuccessful goal searches and
an inherited sample-time/publication-time mismatch. Late tracking lead reaches
about one meter while position feedback reduces commanded speed. The earlier
39–55 s corner result does not establish this later tracking condition. This
follow-up changes no frozen source or acceptance outcome.
